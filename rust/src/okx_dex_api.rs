use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use serde_json::{Value, json};
use reqwest::Client;
use anyhow::{Result, anyhow};
use ring::hmac;
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationResult {
    pub success: bool,
    pub gas_used: u64,
    pub slippage: f64,
    pub output_amount: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeParams {
    pub token_address: String,
    pub amount_in: f64,
    pub slippage_tolerance: f64,
    pub gas_tip: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub tx_hash: String,
    pub status: String,
    pub gas_used: u64,
    pub effective_price: f64,
    pub amount_out: f64,
}

pub struct OkxClient {
    client: Client,
    api_key: String,
    secret_key: String,
    passphrase: String,
    base_url: String,
}

impl OkxClient {
    pub async fn new() -> Result<Self> {
        let api_key = std::env::var("OKX_API_KEY")
            .map_err(|_| anyhow!("OKX_API_KEY not set"))?;
        let secret_key = std::env::var("OKX_SECRET_KEY")
            .map_err(|_| anyhow!("OKX_SECRET_KEY not set"))?;
        let passphrase = std::env::var("OKX_PASSPHRASE")
            .map_err(|_| anyhow!("OKX_PASSPHRASE not set"))?;

        Ok(Self {
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(5))
                .build()?,
            api_key,
            secret_key,
            passphrase,
            base_url: "https://www.okx.com".to_string(),
        })
    }

    pub async fn get_token_liquidity(&self, token_address: &str) -> Result<f64> {
        let path = "/api/v5/dex/liquidity";
        let params = format!("tokenAddress={}", token_address);
        let url = format!("{}{}?{}", self.base_url, path, params);

        let headers = self.create_headers("GET", path, "")?;
        let response = self.client
            .get(&url)
            .headers(headers)
            .send()
            .await?;

        let data: Value = response.json().await?;
        
        if data["code"].as_str() == Some("0") {
            if let Some(liquidity_data) = data["data"].as_array().and_then(|arr| arr.first()) {
                let base_liquidity = liquidity_data["baseLiquidity"]
                    .as_str()
                    .unwrap_or("0")
                    .parse::<f64>()
                    .unwrap_or(0.0);
                let quote_liquidity = liquidity_data["quoteLiquidity"]
                    .as_str()
                    .unwrap_or("0")
                    .parse::<f64>()
                    .unwrap_or(0.0);
                
                return Ok(base_liquidity + quote_liquidity);
            }
        }

        Ok(0.0)
    }

    pub async fn simulate_token_transfer(&self, token_address: &str) -> Result<SimulationResult> {
        let path = "/api/v5/dex/quote";
        let body = json!({
            "chainId": "1",
            "fromTokenAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "toTokenAddress": token_address,
            "amount": "1000000000000000000",
            "slippage": "1"
        });

        let headers = self.create_headers("POST", path, &body.to_string())?;
        let response = self.client
            .post(&format!("{}{}", self.base_url, path))
            .headers(headers)
            .json(&body)
            .send()
            .await?;

        let data: Value = response.json().await?;

        if data["code"].as_str() == Some("0") {
            if let Some(quote_data) = data["data"].as_array().and_then(|arr| arr.first()) {
                return Ok(SimulationResult {
                    success: true,
                    gas_used: quote_data["estimatedGas"]
                        .as_str()
                        .unwrap_or("0")
                        .parse()
                        .unwrap_or(0),
                    slippage: quote_data["priceImpact"]
                        .as_str()
                        .unwrap_or("0")
                        .parse()
                        .unwrap_or(0.0),
                    output_amount: quote_data["toTokenAmount"]
                        .as_str()
                        .unwrap_or("0")
                        .parse()
                        .unwrap_or(0.0),
                });
            }
        }

        Ok(SimulationResult {
            success: false,
            gas_used: 0,
            slippage: 0.0,
            output_amount: 0.0,
        })
    }

    pub async fn execute_buy_order(&self, params: TradeParams) -> Result<ExecutionResult> {
        let path = "/api/v5/dex/swap";
        
        let wallet_address = std::env::var("WALLET_ADDRESS")
            .map_err(|_| anyhow!("WALLET_ADDRESS not set"))?;

        let body = json!({
            "chainId": "1",
            "fromTokenAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "toTokenAddress": params.token_address,
            "amount": (params.amount_in * 1e18).to_string(),
            "slippage": params.slippage_tolerance.to_string(),
            "userWalletAddress": wallet_address,
            "referrer": "mimic_bot",
            "gasPrice": params.gas_tip.to_string()
        });

        let headers = self.create_headers("POST", path, &body.to_string())?;
        let response = self.client
            .post(&format!("{}{}", self.base_url, path))
            .headers(headers)
            .json(&body)
            .send()
            .await?;

        let data: Value = response.json().await?;

        if data["code"].as_str() == Some("0") {
            if let Some(swap_data) = data["data"].as_array().and_then(|arr| arr.first()) {
                return Ok(ExecutionResult {
                    tx_hash: swap_data["txHash"].as_str().unwrap_or("").to_string(),
                    status: "submitted".to_string(),
                    gas_used: swap_data["gasUsed"]
                        .as_str()
                        .unwrap_or("0")
                        .parse()
                        .unwrap_or(0),
                    effective_price: params.amount_in / swap_data["toTokenAmount"]
                        .as_str()
                        .unwrap_or("1")
                        .parse::<f64>()
                        .unwrap_or(1.0),
                    amount_out: swap_data["toTokenAmount"]
                        .as_str()
                        .unwrap_or("0")
                        .parse()
                        .unwrap_or(0.0),
                });
            }
        }

        Err(anyhow!("Trade execution failed: {}", data))
    }

    pub async fn get_token_price(&self, token_address: &str) -> Result<f64> {
        let path = "/api/v5/dex/quote";
        let body = json!({
            "chainId": "1",
            "fromTokenAddress": token_address,
            "toTokenAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "amount": "1000000000000000000"
        });

        let headers = self.create_headers("POST", path, &body.to_string())?;
        let response = self.client
            .post(&format!("{}{}", self.base_url, path))
            .headers(headers)
            .json(&body)
            .send()
            .await?;

        let data: Value = response.json().await?;

        if data["code"].as_str() == Some("0") {
            if let Some(quote_data) = data["data"].as_array().and_then(|arr| arr.first()) {
                let eth_amount: f64 = quote_data["toTokenAmount"]
                    .as_str()
                    .unwrap_or("0")
                    .parse()
                    .unwrap_or(0.0) / 1e18;
                return Ok(eth_amount);
            }
        }

        Ok(0.0)
    }

    fn create_headers(&self, method: &str, path: &str, body: &str) -> Result<reqwest::header::HeaderMap> {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)?
            .as_millis()
            .to_string();

        let message = format!("{}{}{}{}", timestamp, method, path, body);
        let key = hmac::Key::new(hmac::HMAC_SHA256, self.secret_key.as_bytes());
        let signature = hmac::sign(&key, message.as_bytes());
        let signature_b64 = BASE64.encode(signature.as_ref());

        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert("OK-ACCESS-KEY", self.api_key.parse()?);
        headers.insert("OK-ACCESS-SIGN", signature_b64.parse()?);
        headers.insert("OK-ACCESS-TIMESTAMP", timestamp.parse()?);
        headers.insert("OK-ACCESS-PASSPHRASE", self.passphrase.parse()?);
        headers.insert("Content-Type", "application/json".parse()?);

        Ok(headers)
    }
}