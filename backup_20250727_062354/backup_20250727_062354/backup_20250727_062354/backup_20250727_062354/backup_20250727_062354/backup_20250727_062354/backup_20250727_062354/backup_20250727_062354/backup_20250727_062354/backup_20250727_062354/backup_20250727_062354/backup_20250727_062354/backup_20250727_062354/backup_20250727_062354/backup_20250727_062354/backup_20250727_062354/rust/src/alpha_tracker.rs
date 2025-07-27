use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use anyhow::Result;
use reqwest::Client;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::AlphaWallet;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenPerformance {
    pub token_address: String,
    pub deployer: String,
    pub initial_price: f64,
    pub peak_price: f64,
    pub current_price: f64,
    pub max_multiplier: f64,
    pub liquidity_added: f64,
    pub volume_24h: f64,
    pub holders: u32,
    pub deploy_timestamp: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WalletAnalytics {
    pub address: String,
    pub total_deployed: u32,
    pub successful_deploys: u32,
    pub avg_multiplier: f64,
    pub total_volume: f64,
    pub avg_hold_time: f64,
    pub risk_score: f64,
    pub last_activity: u64,
}

pub struct AlphaTracker {
    client: Client,
    dexscreener_base: String,
    etherscan_base: String,
    tracked_tokens: HashMap<String, TokenPerformance>,
}

impl AlphaTracker {
    pub fn new() -> Self {
        Self {
            client: Client::new(),
            dexscreener_base: "https://api.dexscreener.com/latest".to_string(),
            etherscan_base: "https://api.etherscan.io/api".to_string(),
            tracked_tokens: HashMap::new(),
        }
    }

    pub async fn find_100x_tokens(&self, days_back: u32) -> Result<Vec<TokenPerformance>> {
        let mut hundred_x_tokens = Vec::new();
        
        let pairs_url = format!("{}/dex/pairs/ethereum", self.dexscreener_base);
        let response: serde_json::Value = self.client
            .get(&pairs_url)
            .send()
            .await?
            .json()
            .await?;

        if let Some(pairs) = response["pairs"].as_array() {
            for pair in pairs.iter().take(500) { // Check top 500 pairs
                if let (Some(token_addr), Some(price_change)) = (
                    pair["baseToken"]["address"].as_str(),
                    pair["priceChange"]["h24"].as_str(),
                ) {
                    if let Ok(change_pct) = price_change.parse::<f64>() {
                        if change_pct >= 10000.0 { // 100x = 10,000%
                            let token_perf = self.analyze_token_performance(token_addr).await?;
                            if token_perf.max_multiplier >= 100.0 {
                                hundred_x_tokens.push(token_perf);
                            }
                        }
                    }
                }
            }
        }

        hundred_x_tokens.sort_by(|a, b| b.max_multiplier.partial_cmp(&a.max_multiplier).unwrap());
        Ok(hundred_x_tokens.into_iter().take(50).collect()) // Top 50
    }

    pub async fn find_deployer_wallets(&self, tokens: &[TokenPerformance]) -> Result<Vec<AlphaWallet>> {
        let mut deployer_wallets = HashMap::new();

        for token in tokens {
            let deployer_addr = &token.deployer;
            
            let analytics = deployer_wallets
                .entry(deployer_addr.clone())
                .or_insert_with(|| WalletAnalytics {
                    address: deployer_addr.clone(),
                    total_deployed: 0,
                    successful_deploys: 0,
                    avg_multiplier: 0.0,
                    total_volume: 0.0,
                    avg_hold_time: 0.0,
                    risk_score: 0.0,
                    last_activity: 0,
                });

            analytics.total_deployed += 1;
            if token.max_multiplier >= 10.0 {
                analytics.successful_deploys += 1;
            }
            analytics.total_volume += token.volume_24h;
            analytics.avg_multiplier = (analytics.avg_multiplier + token.max_multiplier) / 2.0;
        }

        let mut alpha_wallets = Vec::new();
        for analytics in deployer_wallets.values() {
            let success_rate = analytics.successful_deploys as f64 / analytics.total_deployed as f64;
            
            if success_rate >= 0.6 && analytics.avg_multiplier >= 20.0 {
                alpha_wallets.push(AlphaWallet {
                    address: analytics.address.clone(),
                    avg_multiplier: analytics.avg_multiplier,
                    win_rate: success_rate,
                    last_activity: analytics.last_activity,
                    total_trades: analytics.total_deployed,
                    successful_trades: analytics.successful_deploys,
                    deployer_score: analytics.avg_multiplier * success_rate,
                    sniper_score: 0.0, // Will be calculated separately
                    risk_score: 1.0 - (analytics.avg_multiplier / 1000.0).min(0.5),
                });
            }
        }

        alpha_wallets.sort_by(|a, b| b.deployer_score.partial_cmp(&a.deployer_score).unwrap());
        Ok(alpha_wallets.into_iter().take(20).collect()) // Top 20 deployers
    }

    pub async fn find_sniper_wallets(&self, tokens: &[TokenPerformance]) -> Result<Vec<AlphaWallet>> {
        let mut sniper_candidates = Vec::new();

        for token in tokens {
            let early_buyers = self.get_early_token_buyers(&token.token_address).await?;
            
            for buyer in early_buyers {
                let wallet_performance = self.analyze_wallet_performance(&buyer).await?;
                
                if wallet_performance.avg_multiplier >= 15.0 && wallet_performance.avg_hold_time < 3600.0 {
                    sniper_candidates.push(AlphaWallet {
                        address: buyer,
                        avg_multiplier: wallet_performance.avg_multiplier,
                        win_rate: wallet_performance.successful_deploys as f64 / wallet_performance.total_deployed as f64,
                        last_activity: wallet_performance.last_activity,
                        total_trades: wallet_performance.total_deployed,
                        successful_trades: wallet_performance.successful_deploys,
                        deployer_score: 0.0,
                        sniper_score: wallet_performance.avg_multiplier * wallet_performance.avg_hold_time,
                        risk_score: wallet_performance.risk_score,
                    });
                }
            }
        }

        sniper_candidates.sort_by(|a, b| b.sniper_score.partial_cmp(&a.sniper_score).unwrap());
        sniper_candidates.dedup_by(|a, b| a.address == b.address);
        
        Ok(sniper_candidates.into_iter().take(30).collect()) // Top 30 snipers
    }

    async fn analyze_token_performance(&self, token_address: &str) -> Result<TokenPerformance> {
        let dex_url = format!("{}/dex/tokens/{}", self.dexscreener_base, token_address);
        let response: serde_json::Value = self.client
            .get(&dex_url)
            .send()
            .await?
            .json()
            .await?;

        let mut token_perf = TokenPerformance {
            token_address: token_address.to_string(),
            deployer: String::new(),
            initial_price: 0.0,
            peak_price: 0.0,
            current_price: 0.0,
            max_multiplier: 1.0,
            liquidity_added: 0.0,
            volume_24h: 0.0,
            holders: 0,
            deploy_timestamp: 0,
        };

        if let Some(pairs) = response["pairs"].as_array() {
            if let Some(pair) = pairs.first() {
                token_perf.current_price = pair["priceUsd"]
                    .as_str()
                    .unwrap_or("0")
                    .parse()
                    .unwrap_or(0.0);
                
                token_perf.volume_24h = pair["volume"]["h24"]
                    .as_f64()
                    .unwrap_or(0.0);

                if let Some(price_change) = pair["priceChange"]["h24"].as_str() {
                    if let Ok(change_pct) = price_change.parse::<f64>() {
                        token_perf.max_multiplier = (100.0 + change_pct) / 100.0;
                    }
                }
            }
        }

        token_perf.deployer = self.get_token_deployer(token_address).await?;
        
        Ok(token_perf)
    }

    async fn get_token_deployer(&self, token_address: &str) -> Result<String> {
        let etherscan_api_key = std::env::var("ETHERSCAN_API_KEY")
            .unwrap_or_else(|_| "YourApiKeyToken".to_string());

        let url = format!(
            "{}?module=contract&action=getcontractcreation&contractaddresses={}&apikey={}",
            self.etherscan_base, token_address, etherscan_api_key
        );

        let response: serde_json::Value = self.client
            .get(&url)
            .send()
            .await?
            .json()
            .await?;

        if let Some(result) = response["result"].as_array() {
            if let Some(creation) = result.first() {
                return Ok(creation["contractCreator"]
                    .as_str()
                    .unwrap_or("")
                    .to_string());
            }
        }

        Ok(String::new())
    }

    async fn get_early_token_buyers(&self, token_address: &str) -> Result<Vec<String>> {
        let etherscan_api_key = std::env::var("ETHERSCAN_API_KEY")
            .unwrap_or_else(|_| "YourApiKeyToken".to_string());

        let url = format!(
            "{}?module=account&action=tokentx&contractaddress={}&page=1&offset=100&sort=asc&apikey={}",
            self.etherscan_base, token_address, etherscan_api_key
        );

        let response: serde_json::Value = self.client
            .get(&url)
            .send()
            .await?
            .json()
            .await?;

        let mut early_buyers = Vec::new();
        if let Some(txs) = response["result"].as_array() {
            for tx in txs.iter().take(20) { // First 20 transactions
                if let Some(to_addr) = tx["to"].as_str() {
                    early_buyers.push(to_addr.to_string());
                }
            }
        }

        Ok(early_buyers)
    }

    async fn analyze_wallet_performance(&self, wallet_address: &str) -> Result<WalletAnalytics> {
        let etherscan_api_key = std::env::var("ETHERSCAN_API_KEY")
            .unwrap_or_else(|_| "YourApiKeyToken".to_string());

        let url = format!(
            "{}?module=account&action=txlist&address={}&startblock=0&endblock=99999999&page=1&offset=100&sort=desc&apikey={}",
            self.etherscan_base, wallet_address, etherscan_api_key
        );

        let response: serde_json::Value = self.client
            .get(&url)
            .send()
            .await?
            .json()
            .await?;

        let mut analytics = WalletAnalytics {
            address: wallet_address.to_string(),
            total_deployed: 0,
            successful_deploys: 0,
            avg_multiplier: 5.0, // Default assumption
            total_volume: 0.0,
            avg_hold_time: 1800.0, // 30 minutes default
            risk_score: 0.3,
            last_activity: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        };

        if let Some(txs) = response["result"].as_array() {
            analytics.total_deployed = txs.len() as u32;
            analytics.successful_deploys = (txs.len() as f64 * 0.7) as u32; // Estimate 70% success

            if let Some(latest_tx) = txs.first() {
                if let Some(timestamp_str) = latest_tx["timeStamp"].as_str() {
                    analytics.last_activity = timestamp_str.parse().unwrap_or(analytics.last_activity);
                }
            }

            for tx in txs.iter().take(10) {
                if let Some(value_str) = tx["value"].as_str() {
                    if let Ok(value) = value_str.parse::<f64>() {
                        analytics.total_volume += value / 1e18; // Convert wei to ETH
                    }
                }
            }
        }

        Ok(analytics)
    }

    pub async fn update_wallet_scores(&self, wallets: &mut [AlphaWallet]) -> Result<()> {
        for wallet in wallets.iter_mut() {
            let recent_performance = self.analyze_wallet_performance(&wallet.address).await?;
            
            wallet.avg_multiplier = (wallet.avg_multiplier + recent_performance.avg_multiplier) / 2.0;
            wallet.last_activity = recent_performance.last_activity;
            
            let time_decay = self.calculate_time_decay(wallet.last_activity);
            wallet.deployer_score *= time_decay;
            wallet.sniper_score *= time_decay;
            
            wallet.risk_score = self.calculate_risk_score(wallet).await?;
        }
        Ok(())
    }

    fn calculate_time_decay(&self, last_activity: u64) -> f64 {
        let current_time = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        let hours_since_activity = (current_time - last_activity) / 3600;
        
        if hours_since_activity <= 24 {
            1.0
        } else if hours_since_activity <= 168 { // 1 week
            0.9
        } else if hours_since_activity <= 720 { // 1 month
            0.7
        } else {
            0.3
        }
    }

    async fn calculate_risk_score(&self, wallet: &AlphaWallet) -> Result<f64> {
        let mut risk = 0.0;
        
        // Lower risk for higher win rates
        risk += (1.0 - wallet.win_rate) * 0.4;
        
        // Lower risk for more consistent performance
        if wallet.avg_multiplier > 50.0 {
            risk += 0.2; // Very high multipliers are risky
        } else if wallet.avg_multiplier > 20.0 {
            risk += 0.1;
        }
        
        // Recent activity reduces risk
        let time_since_activity = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs() - wallet.last_activity;
        
        if time_since_activity > 604800 { // 1 week
            risk += 0.3;
        }
        
        Ok(risk.min(1.0))
    }

    pub async fn export_alpha_wallets(&self, wallets: &[AlphaWallet]) -> Result<()> {
        let json_data = serde_json::to_string_pretty(&wallets)?;
        tokio::fs::write("alpha_wallets.json", json_data).await?;
        Ok(())
    }

    pub async fn load_alpha_wallets() -> Result<Vec<AlphaWallet>> {
        match tokio::fs::read_to_string("alpha_wallets.json").await {
            Ok(data) => {
                let wallets: Vec<AlphaWallet> = serde_json::from_str(&data)?;
                Ok(wallets)
            }
            Err(_) => Ok(Vec::new()),
        }
    }
}