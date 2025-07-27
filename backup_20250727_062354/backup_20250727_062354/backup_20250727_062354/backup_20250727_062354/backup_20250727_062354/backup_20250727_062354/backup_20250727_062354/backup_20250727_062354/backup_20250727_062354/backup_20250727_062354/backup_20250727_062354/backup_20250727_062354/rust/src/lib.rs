use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use dashmap::DashMap;
use parking_lot::Mutex;
use anyhow::Result;
use serde::{Deserialize, Serialize};

pub mod alpha_tracker;
pub mod token_validator;
pub mod execution_engine;
pub mod mempool_scanner;
pub mod okx_dex_api;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlphaWallet {
    pub address: String,
    pub avg_multiplier: f64,
    pub win_rate: f64,
    pub last_activity: u64,
    pub total_trades: u32,
    pub successful_trades: u32,
    pub deployer_score: f64,
    pub sniper_score: f64,
    pub risk_score: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenTrade {
    pub wallet_address: String,
    pub token_address: String,
    pub tx_hash: String,
    pub amount_eth: f64,
    pub gas_price: u64,
    pub timestamp: u64,
    pub trade_type: TradeType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TradeType {
    Deploy,
    Buy,
    Sell,
    AddLiquidity,
    RemoveLiquidity,
}

#[derive(Debug, Clone)]
pub struct MimicEngine {
    alpha_wallets: Arc<DashMap<String, AlphaWallet>>,
    active_trades: Arc<RwLock<HashMap<String, TokenTrade>>>,
    capital: Arc<Mutex<f64>>,
    okx_client: Arc<okx_dex_api::OkxClient>,
    validator: Arc<token_validator::TokenValidator>,
    execution: Arc<execution_engine::ExecutionEngine>,
}

impl MimicEngine {
    pub async fn new() -> Result<Self> {
        let alpha_wallets = Arc::new(DashMap::new());
        let active_trades = Arc::new(RwLock::new(HashMap::new()));
        let capital = Arc::new(Mutex::new(1000.0));
        
        let okx_client = Arc::new(okx_dex_api::OkxClient::new().await?);
        let validator = Arc::new(token_validator::TokenValidator::new(okx_client.clone()));
        let execution = Arc::new(execution_engine::ExecutionEngine::new(okx_client.clone()));
        
        Ok(Self {
            alpha_wallets,
            active_trades,
            capital,
            okx_client,
            validator,
            execution,
        })
    }

    pub async fn load_alpha_wallets(&self, wallets: Vec<AlphaWallet>) -> Result<()> {
        for wallet in wallets {
            self.alpha_wallets.insert(wallet.address.clone(), wallet);
        }
        Ok(())
    }

    pub async fn start_monitoring(&self) -> Result<()> {
        let scanner = mempool_scanner::MempoolScanner::new(
            self.alpha_wallets.clone(),
            self.validator.clone(),
            self.execution.clone(),
        );
        
        scanner.start().await
    }

    pub fn get_portfolio_value(&self) -> f64 {
        *self.capital.lock()
    }

    pub async fn execute_mimic_trade(&self, trade: TokenTrade) -> Result<bool> {
        if !self.should_mimic_trade(&trade).await? {
            return Ok(false);
        }

        let token_valid = self.validator.validate_token(&trade.token_address).await?;
        if !token_valid {
            return Ok(false);
        }

        let position_size = self.calculate_position_size(&trade).await?;
        
        self.execution.execute_buy(
            &trade.token_address,
            position_size,
            trade.gas_price + 1_000_000_000, // +1 gwei tip
        ).await
    }

    async fn should_mimic_trade(&self, trade: &TokenTrade) -> Result<bool> {
        if let Some(wallet) = self.alpha_wallets.get(&trade.wallet_address) {
            return Ok(wallet.win_rate > 0.7 && wallet.avg_multiplier > 5.0);
        }
        Ok(false)
    }

    async fn calculate_position_size(&self, _trade: &TokenTrade) -> Result<f64> {
        let current_capital = *self.capital.lock();
        Ok(current_capital * 0.3) // 30% position size
    }
}