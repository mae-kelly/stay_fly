use std::sync::Arc;
use std::collections::HashMap;
use serde_json::Value;
use anyhow::{Result, anyhow};
use lru::LruCache;
use parking_lot::Mutex;
use reqwest::Client;
use std::num::NonZeroUsize;

use crate::okx_dex_api::OkxClient;

pub struct TokenValidator {
    okx_client: Arc<OkxClient>,
    etherscan_client: Client,
    cache: Arc<Mutex<LruCache<String, bool>>>,
    blacklist: Arc<Mutex<Vec<String>>>,
}

impl TokenValidator {
    pub fn new(okx_client: Arc<OkxClient>) -> Self {
        let cache_size = NonZeroUsize::new(1000).unwrap();
        Self {
            okx_client,
            etherscan_client: Client::new(),
            cache: Arc::new(Mutex::new(LruCache::new(cache_size))),
            blacklist: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub async fn validate_token(&self, token_address: &str) -> Result<bool> {
        let addr_lower = token_address.to_lowercase();
        
        if let Some(&cached) = self.cache.lock().get(&addr_lower) {
            return Ok(cached);
        }

        if self.is_blacklisted(&addr_lower) {
            self.cache.lock().put(addr_lower, false);
            return Ok(false);
        }

        let validation_result = self.perform_comprehensive_validation(&addr_lower).await?;
        self.cache.lock().put(addr_lower, validation_result);
        
        Ok(validation_result)
    }

    async fn perform_comprehensive_validation(&self, token_address: &str) -> Result<bool> {
        let validation_tasks = vec![
            self.check_contract_verification(token_address),
            self.check_liquidity_requirements(token_address),
            self.check_ownership_renounced(token_address),
            self.check_no_malicious_functions(token_address),
            self.check_transfer_test(token_address),
            self.check_not_honeypot(token_address),
        ];

        let results = futures_util::future::join_all(validation_tasks).await;
        
        for result in results {
            if !result? {
                return Ok(false);
            }
        }

        Ok(true)
    }

    async fn check_contract_verification(&self, token_address: &str) -> Result<bool> {
        let etherscan_api_key = std::env::var("ETHERSCAN_API_KEY")
            .map_err(|_| anyhow!("ETHERSCAN_API_KEY not set"))?;

        let url = format!(
            "https://api.etherscan.io/api?module=contract&action=getsourcecode&address={}&apikey={}",
            token_address, etherscan_api_key
        );

        let response: Value = self.etherscan_client
            .get(&url)
            .send()
            .await?
            .json()
            .await?;

        if let Some(result) = response["result"].as_array() {
            if let Some(contract) = result.first() {
                let source_code = contract["SourceCode"].as_str().unwrap_or("");
                return Ok(!source_code.is_empty());
            }
        }

        Ok(false)
    }

    async fn check_liquidity_requirements(&self, token_address: &str) -> Result<bool> {
        let liquidity = self.okx_client.get_token_liquidity(token_address).await?;
        Ok(liquidity >= 50000.0) // Minimum $50K liquidity
    }

    async fn check_ownership_renounced(&self, token_address: &str) -> Result<bool> {
        let web3_url = std::env::var("ETHEREUM_RPC_URL")
            .map_err(|_| anyhow!("ETHEREUM_RPC_URL not set"))?;
        
        let client = web3::Web3::new(web3::transports::Http::new(&web3_url)?);
        
        let owner_call = web3::contract::Contract::new(
            client.eth(),
            token_address.parse()?,
            include_bytes!("../contracts/erc20_abi.json"),
        );

        match owner_call.query("owner", (), None, web3::contract::Options::default(), None).await {
            Ok(owner_address) => {
                let owner: web3::types::Address = owner_address;
                let zero_address = "0x0000000000000000000000000000000000000000".parse::<web3::types::Address>()?;
                let dead_address = "0x000000000000000000000000000000000000dead".parse::<web3::types::Address>()?;
                
                Ok(owner == zero_address || owner == dead_address)
            }
            Err(_) => Ok(true), // If no owner function, assume renounced
        }
    }

    async fn check_no_malicious_functions(&self, token_address: &str) -> Result<bool> {
        let etherscan_api_key = std::env::var("ETHERSCAN_API_KEY")
            .map_err(|_| anyhow!("ETHERSCAN_API_KEY not set"))?;

        let url = format!(
            "https://api.etherscan.io/api?module=contract&action=getsourcecode&address={}&apikey={}",
            token_address, etherscan_api_key
        );

        let response: Value = self.etherscan_client
            .get(&url)
            .send()
            .await?
            .json()
            .await?;

        if let Some(result) = response["result"].as_array() {
            if let Some(contract) = result.first() {
                let source_code = contract["SourceCode"].as_str().unwrap_or("").to_lowercase();
                
                let dangerous_patterns = vec![
                    "blacklist", "pause", "setfees", "cooldown", "antisell",
                    "rebase", "mint(", "burn(", "onlyowner", "_transfer",
                    "addliquidity", "removeliquidity", "settaxes", "setfee",
                ];

                for pattern in dangerous_patterns {
                    if source_code.contains(pattern) {
                        return Ok(false);
                    }
                }
            }
        }

        Ok(true)
    }

    async fn check_transfer_test(&self, token_address: &str) -> Result<bool> {
        let simulation_result = self.okx_client.simulate_token_transfer(token_address).await?;
        Ok(simulation_result.success)
    }

    async fn check_not_honeypot(&self, token_address: &str) -> Result<bool> {
        let honeypot_check_url = format!(
            "https://api.honeypot.is/v2/IsHoneypot?address={}",
            token_address
        );

        match self.etherscan_client.get(&honeypot_check_url).send().await {
            Ok(response) => {
                if let Ok(data) = response.json::<Value>().await {
                    return Ok(!data["isHoneypot"].as_bool().unwrap_or(true));
                }
            }
            Err(_) => {}
        }

        Ok(true) // If check fails, assume safe
    }

    fn is_blacklisted(&self, token_address: &str) -> bool {
        self.blacklist.lock().contains(&token_address.to_string())
    }

    pub fn add_to_blacklist(&self, token_address: String) {
        self.blacklist.lock().push(token_address);
    }

    pub async fn load_rugdoc_blacklist(&self) -> Result<()> {
        let url = "https://raw.githubusercontent.com/rugdoc/honeypot-list/main/addresses.json";
        
        match self.etherscan_client.get(url).send().await {
            Ok(response) => {
                if let Ok(addresses) = response.json::<Vec<String>>().await {
                    let mut blacklist = self.blacklist.lock();
                    for addr in addresses {
                        blacklist.push(addr.to_lowercase());
                    }
                }
            }
            Err(_) => {}
        }

        Ok(())
    }
}