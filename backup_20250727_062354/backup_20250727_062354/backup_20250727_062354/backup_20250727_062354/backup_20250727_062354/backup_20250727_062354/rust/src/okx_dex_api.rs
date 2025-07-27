use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use serde_json::{Value, json};
use reqwest::Client;
use anyhow::{Result, anyhow};
use ring::hmac;
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use serde::{Deserialize, Serialize};
use tokio::time::{sleep, Duration};

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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderStatus {
    pub tx_hash: String,
    pub status: String,
    pub confirmations: u32,
    pub gas_used: Option<u64>,
    pub block_number: Option<u64>,
}

pub struct OkxClient {
    client: Client,
    api_key: String,
    secret_key: String,
    passphrase: String,
    base_url: String,
    retry_count: u32,
    rate_limit_delay: Duration,
}

impl OkxClient {
    pub async fn new() -> Result<Self> {
        let api_key = std::env::var("OKX_API_KEY")
            .map_err(|_| anyhow!("OKX_API_KEY not set"))?;
        let secret_key = std::env::var("OKX_SECRET_KEY")
            .map_err(|_| anyhow!("OKX_SECRET_KEY not set"))?;
        let passphrase = std::env::var("OKX_PASSPHRASE")
            .map_err(|_| anyhow!("OKX_PASSPHRASE not set"))?;

        let client = Client::builder()
            .timeout(Duration::from_secs(10))
            .user_agent("elite-mirror-bot/1.0")
            .build()?;

        Ok(Self {
            client,
            api_key,
            secret_key,
            passphrase,
            base_url: "https://www.okx.com".to_string(),
            retry_count: 3,
            rate_limit_delay: Duration::from_millis(100),
        })
    }

    pub async fn get_token_liquidity(&self, token_address: &str) -> Result<f64> {
        let path = "/api/v5/dex/liquidity";
        let params = format!("tokenAddress={}&chainId=1", token_address);
        
        let result = self.make_authenticated_request("GET", path, Some(&params), None).await?;
        
        if let Some(liquidity_data) = result["data"].as_array().and_then(|arr| arr.first()) {
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

        let result = self.make_authenticated_request("POST", path, None, Some(&body.to_string())).await?;

        if let Some(quote_data) = result["data"].as_array().and_then(|arr| arr.first()) {
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
            "referrer": "elite_mirror_bot",
            "gasPrice": params.gas_tip.to_string(),
            "gasPriceLevel": "high"
        });

        let result = self.make_authenticated_request("POST", path, None, Some(&body.to_string())).await?;

        if let Some(swap_data) = result["data"].as_array().and_then(|arr| arr.first()) {
            let tx_hash = swap_data["txHash"].as_str().unwrap_or("").to_string();
            let amount_out: f64 = swap_data["toTokenAmount"]
                .as_str()
                .unwrap_or("0")
                .parse()
                .unwrap_or(0.0);

            // Monitor the transaction
            if !tx_hash.is_empty() {
                self.monitor_transaction(&tx_hash).await?;
            }

            return Ok(ExecutionResult {
                tx_hash,
                status: "submitted".to_string(),
                gas_used: swap_data["gasUsed"]
                    .as_str()
                    .unwrap_or("0")
                    .parse()
                    .unwrap_or(0),
                effective_price: if amount_out > 0.0 { params.amount_in / amount_out } else { 0.0 },
                amount_out,
            });
        }

        Err(anyhow!("Trade execution failed: {}", result))
    }

    pub async fn get_token_price(&self, token_address: &str) -> Result<f64> {
        let path = "/api/v5/dex/quote";
        let body = json!({
            "chainId": "1",
            "fromTokenAddress": token_address,
            "toTokenAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "amount": "1000000000000000000"
        });

        let result = self.make_authenticated_request("POST", path, None, Some(&body.to_string())).await?;

        if let Some(quote_data) = result["data"].as_array().and_then(|arr| arr.first()) {
            let eth_amount: f64 = quote_data["toTokenAmount"]
                .as_str()
                .unwrap_or("0")
                .parse()
                .unwrap_or(0.0) / 1e18;
            return Ok(eth_amount);
        }

        Ok(0.0)
    }

    pub async fn get_order_status(&self, tx_hash: &str) -> Result<OrderStatus> {
        // In a real implementation, you'd query the transaction status
        // via OKX transaction status API or Ethereum RPC
        
        let path = "/api/v5/dex/transaction";
        let params = format!("txHash={}", tx_hash);
        
        match self.make_authenticated_request("GET", path, Some(&params), None).await {
            Ok(result) => {
                if let Some(tx_data) = result["data"].as_array().and_then(|arr| arr.first()) {
                    return Ok(OrderStatus {
                        tx_hash: tx_hash.to_string(),
                        status: tx_data["status"].as_str().unwrap_or("pending").to_string(),
                        confirmations: tx_data["confirmations"].as_u64().unwrap_or(0) as u32,
                        gas_used: tx_data["gasUsed"].as_str().and_then(|s| s.parse().ok()),
                        block_number: tx_data["blockNumber"].as_u64(),
                    });
                }
            }
            Err(_) => {
                // Fallback to basic status
                return Ok(OrderStatus {
                    tx_hash: tx_hash.to_string(),
                    status: "unknown".to_string(),
                    confirmations: 0,
                    gas_used: None,
                    block_number: None,
                });
            }
        }

        Ok(OrderStatus {
            tx_hash: tx_hash.to_string(),
            status: "pending".to_string(),
            confirmations: 0,
            gas_used: None,
            block_number: None,
        })
    }

    async fn monitor_transaction(&self, tx_hash: &str) -> Result<()> {
        let max_wait_time = Duration::from_secs(300); // 5 minutes
        let check_interval = Duration::from_secs(10);
        let start_time = std::time::Instant::now();

        tracing::info!("🔍 Monitoring transaction: {}", &tx_hash[..10]);

        while start_time.elapsed() < max_wait_time {
            match self.get_order_status(tx_hash).await {
                Ok(status) => {
                    tracing::info!("📊 Transaction status: {} (confirmations: {})", status.status, status.confirmations);
                    
                    match status.status.as_str() {
                        "confirmed" | "success" => {
                            tracing::info!("✅ Transaction confirmed!");
                            return Ok(());
                        }
                        "failed" | "reverted" => {
                            return Err(anyhow!("Transaction failed or reverted"));
                        }
                        _ => {
                            // Continue monitoring
                        }
                    }
                }
                Err(e) => {
                    tracing::warn!("⚠️ Error checking transaction status: {}", e);
                }
            }

            sleep(check_interval).await;
        }

        tracing::warn!("⏰ Transaction monitoring timeout");
        Ok(())
    }

    async fn make_authenticated_request(
        &self,
        method: &str,
        path: &str,
        params: Option<&str>,
        body: Option<&str>,
    ) -> Result<Value> {
        let mut attempts = 0;
        
        while attempts < self.retry_count {
            attempts += 1;
            
            let headers = self.create_headers(method, path, body.unwrap_or(""))?;
            let url = if let Some(p) = params {
                format!("{}{}?{}", self.base_url, path, p)
            } else {
                format!("{}{}", self.base_url, path)
            };

            let request = match method {
                "GET" => self.client.get(&url),
                "POST" => {
                    let mut req = self.client.post(&url);
                    if let Some(b) = body {
                        req = req.body(b.to_string());
                    }
                    req
                }
                _ => return Err(anyhow!("Unsupported HTTP method: {}", method)),
            };

            let response = request.headers(headers).send().await?;
            
            if response.status().is_success() {
                let data: Value = response.json().await?;
                
                if data["code"].as_str() == Some("0") {
                    return Ok(data);
                } else {
                    let error_msg = data["msg"].as_str().unwrap_or("Unknown error");
                    
                    // Check for rate limiting
                    if data["code"].as_str() == Some("50011") {
                        tracing::warn!("Rate limited, retrying in {:?}", self.rate_limit_delay);
                        sleep(self.rate_limit_delay).await;
                        continue;
                    }
                    
                    return Err(anyhow!("OKX API error: {}", error_msg));
                }
            } else if response.status().as_u16() == 429 {
                // Rate limited
                tracing::warn!("HTTP 429 rate limit, retrying in {:?}", self.rate_limit_delay);
                sleep(self.rate_limit_delay).await;
                continue;
            } else {
                return Err(anyhow!("HTTP error: {}", response.status()));
            }
        }
        
        Err(anyhow!("Max retries exceeded"))
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

    pub async fn test_connection(&self) -> Result<bool> {
        let path = "/api/v5/public/time";
        
        match self.make_authenticated_request("GET", path, None, None).await {
            Ok(_) => {
                tracing::info!("✅ OKX connection test successful");
                Ok(true)
            }
            Err(e) => {
                tracing::error!("❌ OKX connection test failed: {}", e);
                Ok(false)
            }
        }
    }
}
