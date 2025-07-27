use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use tokio::time::{sleep, Duration};
use reqwest::Client;
use anyhow::Result;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MLPrediction {
    pub success_probability: f64,
    pub confidence_score: f64,
    pub risk_assessment: String,
    pub recommended_position_size: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WhaleBehaviorPattern {
    pub wallet_address: String,
    pub pattern_type: String,
    pub success_rate: f64,
    pub avg_hold_time: f64,
    pub preferred_tokens: Vec<String>,
    pub trading_hours: Vec<u8>,
}

pub struct RustMLProcessor {
    client: Client,
    patterns: HashMap<String, WhaleBehaviorPattern>,
}

impl RustMLProcessor {
    pub fn new() -> Self {
        Self {
            client: Client::new(),
            patterns: HashMap::new(),
        }
    }
    
    pub async fn analyze_whale_patterns(&mut self, whale_addresses: Vec<String>) -> Result<()> {
        for address in whale_addresses {
            let pattern = self.extract_behavior_pattern(&address).await?;
            self.patterns.insert(address.clone(), pattern);
            sleep(Duration::from_millis(100)).await;
        }
        Ok(())
    }
    
    async fn extract_behavior_pattern(&self, wallet_address: &str) -> Result<WhaleBehaviorPattern> {
        let etherscan_key = std::env::var("ETHERSCAN_API_KEY").unwrap_or_default();
        let url = format!(
            "https://api.etherscan.io/api?module=account&action=txlist&address={}&startblock=0&endblock=99999999&sort=desc&apikey={}",
            wallet_address, etherscan_key
        );
        
        let response: serde_json::Value = self.client
            .get(&url)
            .send()
            .await?
            .json()
            .await?;
            
        let mut trading_hours = vec![0; 24];
        let mut total_trades = 0;
        let mut successful_trades = 0;
        
        if let Some(txs) = response["result"].as_array() {
            for tx in txs.iter().take(1000) {
                if let Some(timestamp) = tx["timeStamp"].as_str() {
                    if let Ok(ts) = timestamp.parse::<i64>() {
                        let hour = ((ts % 86400) / 3600) as usize;
                        if hour < 24 {
                            trading_hours[hour] += 1;
                        }
                        total_trades += 1;
                        
                        if let Some(value) = tx["value"].as_str() {
                            if let Ok(val) = value.parse::<u64>() {
                                if val > 100000000000000000 {
                                    successful_trades += 1;
                                }
                            }
                        }
                    }
                }
            }
        }
        
        let success_rate = if total_trades > 0 {
            successful_trades as f64 / total_trades as f64
        } else {
            0.0
        };
        
        Ok(WhaleBehaviorPattern {
            wallet_address: wallet_address.to_string(),
            pattern_type: if success_rate > 0.7 { "aggressive".to_string() } else { "conservative".to_string() },
            success_rate,
            avg_hold_time: 3600.0,
            preferred_tokens: vec![],
            trading_hours: trading_hours.iter().map(|&x| x as u8).collect(),
        })
    }
    
    pub fn predict_trade_outcome(&self, whale_address: &str, token_data: &HashMap<String, f64>) -> MLPrediction {
        if let Some(pattern) = self.patterns.get(whale_address) {
            let base_probability = pattern.success_rate;
            let confidence = if pattern.success_rate > 0.8 { 0.9 } else { 0.6 };
            
            let liquidity_factor = token_data.get("liquidity").unwrap_or(&0.0) / 100000.0;
            let volume_factor = token_data.get("volume_24h").unwrap_or(&0.0) / 1000000.0;
            
            let adjusted_probability = (base_probability + liquidity_factor.min(0.2) + volume_factor.min(0.1)).min(0.95);
            
            let risk_level = if adjusted_probability > 0.8 {
                "low"
            } else if adjusted_probability > 0.6 {
                "medium"
            } else {
                "high"
            };
            
            let position_size = match risk_level {
                "low" => 0.3,
                "medium" => 0.2,
                _ => 0.1,
            };
            
            MLPrediction {
                success_probability: adjusted_probability,
                confidence_score: confidence,
                risk_assessment: risk_level.to_string(),
                recommended_position_size: position_size,
            }
        } else {
            MLPrediction {
                success_probability: 0.5,
                confidence_score: 0.3,
                risk_assessment: "unknown".to_string(),
                recommended_position_size: 0.1,
            }
        }
    }
    
    pub fn get_optimal_entry_time(&self, whale_address: &str) -> Option<u8> {
        if let Some(pattern) = self.patterns.get(whale_address) {
            let max_activity_hour = pattern.trading_hours
                .iter()
                .enumerate()
                .max_by_key(|(_, &count)| count)
                .map(|(hour, _)| hour as u8);
            return max_activity_hour;
        }
        None
    }
}
