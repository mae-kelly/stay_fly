use std::sync::Arc;
use std::collections::HashSet;
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures_util::{SinkExt, StreamExt};
use serde_json::Value;
use dashmap::DashMap;
use web3::types::{H256, Transaction};
use anyhow::{Result, anyhow};
use crossbeam::channel::{bounded, Receiver, Sender};
use rayon::prelude::*;

use crate::{AlphaWallet, TokenTrade, TradeType};
use crate::token_validator::TokenValidator;
use crate::execution_engine::ExecutionEngine;

pub struct MempoolScanner {
    alpha_wallets: Arc<DashMap<String, AlphaWallet>>,
    validator: Arc<TokenValidator>,
    execution: Arc<ExecutionEngine>,
    pending_hashes: Arc<DashMap<String, u64>>,
    dex_routers: HashSet<String>,
}

impl MempoolScanner {
    pub fn new(
        alpha_wallets: Arc<DashMap<String, AlphaWallet>>,
        validator: Arc<TokenValidator>,
        execution: Arc<ExecutionEngine>,
    ) -> Self {
        let mut dex_routers = HashSet::new();
        dex_routers.insert("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D".to_lowercase()); // Uniswap V2
        dex_routers.insert("0xE592427A0AEce92De3Edee1F18E0157C05861564".to_lowercase()); // Uniswap V3
        dex_routers.insert("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F".to_lowercase()); // SushiSwap
        dex_routers.insert("0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506".to_lowercase()); // SushiSwap Router

        Self {
            alpha_wallets,
            validator,
            execution,
            pending_hashes: Arc::new(DashMap::new()),
            dex_routers,
        }
    }

    pub async fn start(&self) -> Result<()> {
        let ws_url = std::env::var("ETHEREUM_WS_URL")
            .map_err(|_| anyhow!("ETHEREUM_WS_URL not set"))?;

        let (tx_sender, mut tx_receiver) = mpsc::channel::<Transaction>(10000);
        let (trade_sender, trade_receiver) = bounded::<TokenTrade>(1000);

        let scanner_task = self.start_websocket_scanner(ws_url, tx_sender);
        let processor_task = self.start_transaction_processor(tx_receiver, trade_sender);
        let executor_task = self.start_trade_executor(trade_receiver);

        tokio::try_join!(scanner_task, processor_task, executor_task)?;
        Ok(())
    }

    async fn start_websocket_scanner(
        &self,
        ws_url: String,
        tx_sender: mpsc::Sender<Transaction>,
    ) -> Result<()> {
        let (ws_stream, _) = connect_async(&ws_url).await?;
        let (mut write, mut read) = ws_stream.split();

        let subscribe_msg = serde_json::json!({
            "id": 1,
            "method": "eth_subscribe",
            "params": ["pendingTransactions"]
        });

        write.send(Message::Text(subscribe_msg.to_string())).await?;

        let web3_client = web3::Web3::new(web3::transports::Http::new(&std::env::var("ETHEREUM_RPC_URL")?)?);
        let mut batch_hashes = Vec::with_capacity(100);
        let mut last_batch_time = std::time::Instant::now();

        while let Some(msg) = read.next().await {
            match msg? {
                Message::Text(text) => {
                    if let Ok(data) = serde_json::from_str::<Value>(&text) {
                        if let Some(result) = data["params"]["result"].as_str() {
                            if let Ok(hash) = result.parse::<H256>() {
                                batch_hashes.push(hash);

                                if batch_hashes.len() >= 50 || last_batch_time.elapsed().as_millis() >= 100 {
                                    self.process_transaction_batch(
                                        &web3_client,
                                        batch_hashes.clone(),
                                        &tx_sender,
                                    ).await?;
                                    
                                    batch_hashes.clear();
                                    last_batch_time = std::time::Instant::now();
                                }
                            }
                        }
                    }
                }
                Message::Close(_) => break,
                _ => {}
            }
        }
        Ok(())
    }

    async fn process_transaction_batch(
        &self,
        web3_client: &web3::Web3<web3::transports::Http>,
        hashes: Vec<H256>,
        tx_sender: &mpsc::Sender<Transaction>,
    ) -> Result<()> {
        let futures: Vec<_> = hashes.into_iter().map(|hash| {
            let client = web3_client.clone();
            async move {
                client.eth().transaction(web3::types::TransactionId::Hash(hash)).await
            }
        }).collect();

        let results = futures_util::future::join_all(futures).await;
        
        for result in results {
            if let Ok(Some(tx)) = result {
                if self.is_alpha_wallet_transaction(&tx) {
                    let _ = tx_sender.send(tx).await;
                }
            }
        }
        Ok(())
    }

    async fn start_transaction_processor(
        &self,
        mut tx_receiver: mpsc::Receiver<Transaction>,
        trade_sender: Sender<TokenTrade>,
    ) -> Result<()> {
        while let Some(tx) = tx_receiver.recv().await {
            if let Some(trade) = self.decode_transaction(&tx).await? {
                let _ = trade_sender.send(trade);
            }
        }
        Ok(())
    }

    async fn start_trade_executor(&self, trade_receiver: Receiver<TokenTrade>) -> Result<()> {
        let validator = self.validator.clone();
        let execution = self.execution.clone();
        let alpha_wallets = self.alpha_wallets.clone();

        tokio::task::spawn_blocking(move || {
            trade_receiver.iter().par_bridge().for_each(|trade| {
                let validator = validator.clone();
                let execution = execution.clone();
                let alpha_wallets = alpha_wallets.clone();

                tokio::runtime::Handle::current().block_on(async move {
                    if let Some(wallet) = alpha_wallets.get(&trade.wallet_address) {
                        if wallet.win_rate > 0.7 && wallet.avg_multiplier > 5.0 {
                            if let Ok(true) = validator.validate_token(&trade.token_address).await {
                                let position_size = 1000.0 * 0.3; // 30% of capital
                                let _ = execution.execute_buy(
                                    &trade.token_address,
                                    position_size,
                                    trade.gas_price + 2_000_000_000,
                                ).await;
                            }
                        }
                    }
                });
            });
        }).await?;

        Ok(())
    }

    fn is_alpha_wallet_transaction(&self, tx: &Transaction) -> bool {
        if let Some(from) = tx.from {
            let from_addr = format!("{:?}", from).to_lowercase();
            return self.alpha_wallets.contains_key(&from_addr);
        }
        false
    }

    async fn decode_transaction(&self, tx: &Transaction) -> Result<Option<TokenTrade>> {
        if let (Some(to), Some(from)) = (tx.to, tx.from) {
            let to_addr = format!("{:?}", to).to_lowercase();
            let from_addr = format!("{:?}", from).to_lowercase();

            if !self.dex_routers.contains(&to_addr) {
                return Ok(None);
            }

            if let Some(input) = &tx.input {
                let method_id = if input.0.len() >= 4 {
                    hex::encode(&input.0[0..4])
                } else {
                    return Ok(None);
                };

                let trade_type = match method_id.as_str() {
                    "7ff36ab5" => TradeType::Buy, // swapExactETHForTokens
                    "18cbafe5" => TradeType::Buy, // swapExactETHForTokensSupportingFeeOnTransferTokens
                    "38ed1739" => TradeType::Buy, // swapExactTokensForTokens
                    "b6f9de95" => TradeType::Buy, // swapExactETHForTokensOut
                    _ => return Ok(None),
                };

                let token_address = self.extract_token_from_calldata(&input.0)?;

                return Ok(Some(TokenTrade {
                    wallet_address: from_addr,
                    token_address,
                    tx_hash: format!("{:?}", tx.hash),
                    amount_eth: tx.value.as_u128() as f64 / 1e18,
                    gas_price: tx.gas_price.unwrap_or_default().as_u64(),
                    timestamp: std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)?
                        .as_secs(),
                    trade_type,
                }));
            }
        }
        Ok(None)
    }

    fn extract_token_from_calldata(&self, calldata: &[u8]) -> Result<String> {
        if calldata.len() < 4 {
            return Err(anyhow!("Invalid calldata"));
        }

        let method_id = &calldata[0..4];
        
        match hex::encode(method_id).as_str() {
            "7ff36ab5" | "18cbafe5" => {
                if calldata.len() >= 68 {
                    let path_offset = u32::from_be_bytes([
                        calldata[4], calldata[5], calldata[6], calldata[7]
                    ]) as usize;
                    
                    if calldata.len() >= path_offset + 32 {
                        let token_bytes = &calldata[path_offset + 32..path_offset + 52];
                        return Ok(format!("0x{}", hex::encode(token_bytes)));
                    }
                }
            }
            _ => {}
        }
        
        Err(anyhow!("Could not extract token address"))
    }
}