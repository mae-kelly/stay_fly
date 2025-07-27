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
use std::time::{Duration, Instant};
use parking_lot::RwLock;

use crate::{AlphaWallet, TokenTrade, TradeType};
use crate::token_validator::TokenValidator;
use crate::execution_engine::ExecutionEngine;

pub struct MempoolScanner {
    alpha_wallets: Arc<DashMap<String, AlphaWallet>>,
    validator: Arc<TokenValidator>,
    execution: Arc<ExecutionEngine>,
    pending_hashes: Arc<DashMap<String, u64>>,
    dex_routers: HashSet<String>,
    performance_stats: Arc<RwLock<PerformanceStats>>,
}

#[derive(Debug, Default)]
struct PerformanceStats {
    transactions_processed: u64,
    alpha_trades_detected: u64,
    successful_executions: u64,
    failed_executions: u64,
    avg_detection_latency: f64,
    uptime_start: Instant,
}

impl MempoolScanner {
    pub fn new(
        alpha_wallets: Arc<DashMap<String, AlphaWallet>>,
        validator: Arc<TokenValidator>,
        execution: Arc<ExecutionEngine>,
    ) -> Self {
        let mut dex_routers = HashSet::new();
        
        // Major DEX routers for comprehensive coverage
        dex_routers.insert("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D".to_lowercase()); // Uniswap V2
        dex_routers.insert("0xE592427A0AEce92De3Edee1F18E0157C05861564".to_lowercase()); // Uniswap V3
        dex_routers.insert("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F".to_lowercase()); // SushiSwap
        dex_routers.insert("0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506".to_lowercase()); // SushiSwap Router
        dex_routers.insert("0x881D40237659C251811CEC9c364ef91dC08D300C".to_lowercase()); // Metamask Swap
        dex_routers.insert("0x1111111254EEB25477B68fb85Ed929f73A960582".to_lowercase()); // 1inch
        dex_routers.insert("0xDef1C0ded9bec7F1a1670819833240f027b25EfF".to_lowercase()); // 0x Protocol

        Self {
            alpha_wallets,
            validator,
            execution,
            pending_hashes: Arc::new(DashMap::new()),
            dex_routers,
            performance_stats: Arc::new(RwLock::new(PerformanceStats {
                uptime_start: Instant::now(),
                ..Default::default()
            })),
        }
    }

    pub async fn start_realtime_monitoring(&self) -> Result<()> {
        let ws_url = std::env::var("ETHEREUM_WS_URL")
            .map_err(|_| anyhow!("ETHEREUM_WS_URL not set"))?;

        tracing::info!("🚀 Starting real-time mempool monitoring");
        tracing::info!("📡 WebSocket URL: {}", ws_url);
        tracing::info!("🐋 Monitoring {} alpha wallets", self.alpha_wallets.len());

        let (tx_sender, tx_receiver) = mpsc::channel::<Transaction>(10000);
        let (trade_sender, trade_receiver) = bounded::<TokenTrade>(1000);

        // Start concurrent tasks
        let websocket_task = self.start_websocket_scanner(ws_url.clone(), tx_sender.clone());
        let processor_task = self.start_transaction_processor(tx_receiver, trade_sender.clone());
        let executor_task = self.start_trade_executor(trade_receiver);
        let health_monitor = self.start_health_monitoring();
        let reconnect_monitor = self.start_reconnection_monitor(ws_url, tx_sender);

        // Run all tasks concurrently
        tokio::try_join!(
            websocket_task,
            processor_task,
            executor_task,
            health_monitor,
            reconnect_monitor
        )?;

        Ok(())
    }

    async fn start_websocket_scanner(
        &self,
        ws_url: String,
        tx_sender: mpsc::Sender<Transaction>,
    ) -> Result<()> {
        let mut retry_count = 0;
        let max_retries = 5;

        loop {
            match self.connect_and_monitor(&ws_url, &tx_sender).await {
                Ok(_) => {
                    tracing::info!("WebSocket connection completed normally");
                    break;
                }
                Err(e) => {
                    retry_count += 1;
                    if retry_count > max_retries {
                        return Err(anyhow!("Max WebSocket retries exceeded: {}", e));
                    }
                    
                    tracing::warn!("WebSocket error (attempt {}/{}): {}", retry_count, max_retries, e);
                    
                    // Exponential backoff
                    let delay = Duration::from_secs(2_u64.pow(retry_count));
                    tokio::time::sleep(delay).await;
                }
            }
        }

        Ok(())
    }

    async fn connect_and_monitor(
        &self,
        ws_url: &str,
        tx_sender: &mpsc::Sender<Transaction>,
    ) -> Result<()> {
        tracing::info!("🔗 Connecting to Ethereum WebSocket...");
        
        let (ws_stream, _) = connect_async(ws_url).await
            .map_err(|e| anyhow!("WebSocket connection failed: {}", e))?;
        
        let (mut write, mut read) = ws_stream.split();

        // Subscribe to pending transactions
        let subscribe_msg = serde_json::json!({
            "id": 1,
            "method": "eth_subscribe",
            "params": ["pendingTransactions"]
        });

        write.send(Message::Text(subscribe_msg.to_string())).await?;
        tracing::info!("✅ Subscribed to pending transactions");

        // Initialize Web3 client for batch processing
        let rpc_url = std::env::var("ETHEREUM_RPC_URL")?;
        let web3_client = web3::Web3::new(web3::transports::Http::new(&rpc_url)?);
        
        let mut batch_hashes = Vec::with_capacity(50);
        let mut last_batch_time = Instant::now();
        let batch_timeout = Duration::from_millis(100);

        // Main processing loop
        while let Some(msg) = read.next().await {
            match msg? {
                Message::Text(text) => {
                    if let Ok(data) = serde_json::from_str::<Value>(&text) {
                        if let Some(result) = data["params"]["result"].as_str() {
                            if let Ok(hash) = result.parse::<H256>() {
                                batch_hashes.push(hash);
                                
                                // Process batches for efficiency
                                if batch_hashes.len() >= 50 || last_batch_time.elapsed() >= batch_timeout {
                                    self.process_transaction_batch(
                                        &web3_client,
                                        batch_hashes.clone(),
                                        tx_sender,
                                    ).await?;
                                    
                                    batch_hashes.clear();
                                    last_batch_time = Instant::now();
                                }
                            }
                        }
                    }
                }
                Message::Close(_) => {
                    tracing::warn!("WebSocket connection closed");
                    break;
                }
                Message::Ping(payload) => {
                    write.send(Message::Pong(payload)).await?;
                }
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
        let start_time = Instant::now();
        
        // Parallel transaction fetching
        let futures: Vec<_> = hashes.into_iter().map(|hash| {
            let client = web3_client.clone();
            async move {
                client.eth().transaction(web3::types::TransactionId::Hash(hash)).await
            }
        }).collect();

        let results = futures_util::future::join_all(futures).await;
        let mut alpha_transactions = 0;
        
        for result in results {
            if let Ok(Some(tx)) = result {
                if self.is_alpha_wallet_transaction(&tx) {
                    alpha_transactions += 1;
                    if tx_sender.send(tx).await.is_err() {
                        tracing::warn!("Failed to send transaction to processor");
                    }
                }
            }
        }

        // Update performance stats
        {
            let mut stats = self.performance_stats.write();
            stats.transactions_processed += results.len() as u64;
            stats.avg_detection_latency = start_time.elapsed().as_micros() as f64 / 1000.0;
        }

        if alpha_transactions > 0 {
            tracing::info!("🎯 Found {} alpha wallet transactions in batch", alpha_transactions);
        }

        Ok(())
    }

    async fn start_transaction_processor(
        &self,
        mut tx_receiver: mpsc::Receiver<Transaction>,
        trade_sender: Sender<TokenTrade>,
    ) -> Result<()> {
        tracing::info!("🔄 Starting transaction processor");

        while let Some(tx) = tx_receiver.recv().await {
            if let Ok(Some(trade)) = self.decode_transaction(&tx).await {
                {
                    let mut stats = self.performance_stats.write();
                    stats.alpha_trades_detected += 1;
                }
                
                tracing::info!(
                    "🐋 Alpha trade detected: {} -> {} ({})",
                    trade.wallet_address[..10].to_string(),
                    trade.token_address[..10].to_string(),
                    trade.amount_eth
                );
                
                if trade_sender.send(trade).is_err() {
                    tracing::warn!("Failed to send trade to executor");
                }
            }
        }
        
        Ok(())
    }

    async fn start_trade_executor(&self, trade_receiver: Receiver<TokenTrade>) -> Result<()> {
        let validator = self.validator.clone();
        let execution = self.execution.clone();
        let alpha_wallets = self.alpha_wallets.clone();
        let performance_stats = self.performance_stats.clone();

        tracing::info!("⚡ Starting trade executor");

        tokio::task::spawn_blocking(move || {
            trade_receiver.iter().par_bridge().for_each(|trade| {
                let validator = validator.clone();
                let execution = execution.clone();
                let alpha_wallets = alpha_wallets.clone();
                let performance_stats = performance_stats.clone();

                tokio::runtime::Handle::current().block_on(async move {
                    let start_time = Instant::now();
                    
                    if let Some(wallet) = alpha_wallets.get(&trade.wallet_address) {
                        // Check wallet quality thresholds
                        if wallet.win_rate > 0.7 && wallet.avg_multiplier > 5.0 {
                            
                            // Fast-track validation for high-confidence wallets
                            let validation_result = if wallet.avg_multiplier > 50.0 {
                                // Skip some validations for ultra-elite wallets
                                Ok(true)
                            } else {
                                validator.validate_token(&trade.token_address).await
                            };

                            match validation_result {
                                Ok(true) => {
                                    // Calculate position size based on wallet confidence
                                    let base_position = 300.0; // $300 base
                                    let multiplier = (wallet.avg_multiplier / 10.0).min(3.0); // Max 3x
                                    let position_size = base_position * multiplier;
                                    
                                    // Execute with priority gas
                                    let gas_boost = 3_000_000_000; // +3 gwei boost
                                    
                                    match execution.execute_buy(
                                        &trade.token_address,
                                        position_size,
                                        trade.gas_price + gas_boost,
                                    ).await {
                                        Ok(true) => {
                                            let mut stats = performance_stats.write();
                                            stats.successful_executions += 1;
                                            
                                            let execution_time = start_time.elapsed().as_millis();
                                            tracing::info!(
                                                "✅ Mirror trade executed in {}ms: ${:.0} -> {}",
                                                execution_time,
                                                position_size,
                                                trade.token_address[..10].to_string()
                                            );
                                        }
                                        Ok(false) => {
                                            tracing::warn!("⚠️ Trade execution declined");
                                        }
                                        Err(e) => {
                                            let mut stats = performance_stats.write();
                                            stats.failed_executions += 1;
                                            tracing::error!("❌ Trade execution failed: {}", e);
                                        }
                                    }
                                }
                                Ok(false) => {
                                    tracing::warn!("⚠️ Token validation failed: {}", trade.token_address[..10].to_string());
                                }
                                Err(e) => {
                                    tracing::error!("❌ Validation error: {}", e);
                                }
                            }
                        }
                    }
                });
            });
        }).await?;

        Ok(())
    }

    async fn start_health_monitoring(&self) -> Result<()> {
        let performance_stats = self.performance_stats.clone();
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(Duration::from_secs(60));
            
            loop {
                interval.tick().await;
                
                let stats = performance_stats.read();
                let uptime = stats.uptime_start.elapsed().as_secs();
                let success_rate = if stats.alpha_trades_detected > 0 {
                    (stats.successful_executions as f64 / stats.alpha_trades_detected as f64) * 100.0
                } else {
                    0.0
                };
                
                tracing::info!(
                    "📊 Health Check | Uptime: {}s | Processed: {} | Detected: {} | Success Rate: {:.1}%",
                    uptime,
                    stats.transactions_processed,
                    stats.alpha_trades_detected,
                    success_rate
                );
            }
        });
        
        Ok(())
    }

    async fn start_reconnection_monitor(
        &self,
        ws_url: String,
        tx_sender: mpsc::Sender<Transaction>,
    ) -> Result<()> {
        let performance_stats = self.performance_stats.clone();
        
        tokio::spawn(async move {
            let mut last_activity = Instant::now();
            let mut check_interval = tokio::time::interval(Duration::from_secs(30));
            
            loop {
                check_interval.tick().await;
                
                let stats = performance_stats.read();
                if stats.uptime_start.elapsed() - last_activity.elapsed() > Duration::from_secs(120) {
                    tracing::warn!("🔄 No activity for 2 minutes, connection may be stale");
                    // Trigger reconnection logic here if needed
                }
                
                last_activity = Instant::now();
            }
        });
        
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

            // Check if transaction is to a known DEX router
            if !self.dex_routers.contains(&to_addr) {
                return Ok(None);
            }

            if let Some(input) = &tx.input {
                let method_id = if input.0.len() >= 4 {
                    hex::encode(&input.0[0..4])
                } else {
                    return Ok(None);
                };

                // Decode common DEX methods
                let trade_type = match method_id.as_str() {
                    "7ff36ab5" => TradeType::Buy, // swapExactETHForTokens
                    "18cbafe5" => TradeType::Buy, // swapExactETHForTokensSupportingFeeOnTransferTokens
                    "38ed1739" => TradeType::Buy, // swapExactTokensForTokens
                    "b6f9de95" => TradeType::Buy, // swapExactETHForTokensOut
                    "791ac947" => TradeType::Buy, // swapExactTokensForETH
                    "fb3bdb41" => TradeType::Buy, // swapETHForExactTokens
                    _ => return Ok(None),
                };

                // Extract token address from calldata
                if let Ok(token_address) = self.extract_token_from_calldata(&input.0) {
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
        }
        Ok(None)
    }

    fn extract_token_from_calldata(&self, calldata: &[u8]) -> Result<String> {
        if calldata.len() < 4 {
            return Err(anyhow!("Invalid calldata length"));
        }

        let method_id = &calldata[0..4];
        
        match hex::encode(method_id).as_str() {
            "7ff36ab5" | "18cbafe5" => {
                // swapExactETHForTokens methods
                if calldata.len() >= 68 {
                    // Path is typically at offset 0x80 (128 bytes)
                    if calldata.len() >= 160 {
                        let path_start = 128 + 32; // Skip length field
                        if calldata.len() >= path_start + 40 {
                            // Second token in path (first is WETH)
                            let token_bytes = &calldata[path_start + 12..path_start + 32];
                            return Ok(format!("0x{}", hex::encode(token_bytes)));
                        }
                    }
                }
            }
            "38ed1739" => {
                // swapExactTokensForTokens
                if calldata.len() >= 68 {
                    // Extract destination token from path
                    if calldata.len() >= 200 {
                        let path_offset = u32::from_be_bytes([
                            calldata[68], calldata[69], calldata[70], calldata[71]
                        ]) as usize + 4;
                        
                        if calldata.len() >= path_offset + 64 {
                            let token_bytes = &calldata[path_offset + 44..path_offset + 64];
                            return Ok(format!("0x{}", hex::encode(token_bytes)));
                        }
                    }
                }
            }
            _ => {}
        }
        
        Err(anyhow!("Could not extract token address from calldata"))
    }

    pub fn get_performance_stats(&self) -> String {
        let stats = self.performance_stats.read();
        format!(
            "Processed: {}, Detected: {}, Executed: {}, Failed: {}, Uptime: {}s",
            stats.transactions_processed,
            stats.alpha_trades_detected,
            stats.successful_executions,
            stats.failed_executions,
            stats.uptime_start.elapsed().as_secs()
        )
    }

    pub async fn start(&self) -> Result<()> {
        self.start_realtime_monitoring().await
    }
}
