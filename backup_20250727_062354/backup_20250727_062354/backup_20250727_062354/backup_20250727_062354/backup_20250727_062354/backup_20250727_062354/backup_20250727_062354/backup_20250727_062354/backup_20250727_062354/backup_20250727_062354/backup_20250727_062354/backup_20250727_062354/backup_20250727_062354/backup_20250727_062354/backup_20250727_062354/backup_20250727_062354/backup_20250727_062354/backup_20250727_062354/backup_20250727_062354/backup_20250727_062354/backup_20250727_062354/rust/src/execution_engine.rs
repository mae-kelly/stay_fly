use std::sync::Arc;
use std::collections::HashMap;
use tokio::sync::RwLock;
use anyhow::{Result, anyhow};
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};

use crate::okx_dex_api::{OkxClient, TradeParams, ExecutionResult};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub token_address: String,
    pub entry_price: f64,
    pub amount: f64,
    pub timestamp: u64,
    pub stop_loss: f64,
    pub take_profit: f64,
    pub current_value: f64,
    pub unrealized_pnl: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeMetrics {
    pub total_trades: u32,
    pub winning_trades: u32,
    pub total_pnl: f64,
    pub max_drawdown: f64,
    pub win_rate: f64,
    pub avg_trade_duration: f64,
}

pub struct ExecutionEngine {
    okx_client: Arc<OkxClient>,
    positions: Arc<RwLock<HashMap<String, Position>>>,
    capital: Arc<Mutex<f64>>,
    metrics: Arc<Mutex<TradeMetrics>>,
    max_position_size: f64,
    max_positions: usize,
}

impl ExecutionEngine {
    pub fn new(okx_client: Arc<OkxClient>) -> Self {
        Self {
            okx_client,
            positions: Arc::new(RwLock::new(HashMap::new())),
            capital: Arc::new(Mutex::new(1000.0)),
            metrics: Arc::new(Mutex::new(TradeMetrics {
                total_trades: 0,
                winning_trades: 0,
                total_pnl: 0.0,
                max_drawdown: 0.0,
                win_rate: 0.0,
                avg_trade_duration: 0.0,
            })),
            max_position_size: 0.3, // 30% max per position
            max_positions: 5,
        }
    }

    pub async fn execute_buy(
        &self,
        token_address: &str,
        amount_eth: f64,
        gas_price: u64,
    ) -> Result<bool> {
        let current_capital = *self.capital.lock();
        let max_amount = current_capital * self.max_position_size;
        let actual_amount = amount_eth.min(max_amount);

        if actual_amount < 0.01 {
            return Ok(false); // Too small
        }

        let positions = self.positions.read().await;
        if positions.len() >= self.max_positions {
            return Ok(false); // Too many positions
        }

        if positions.contains_key(token_address) {
            return Ok(false); // Already have position
        }
        drop(positions);

        let trade_params = TradeParams {
            token_address: token_address.to_string(),
            amount_in: actual_amount,
            slippage_tolerance: 0.05, // 5% slippage
            gas_tip: gas_price,
        };

        match self.okx_client.execute_buy_order(trade_params).await {
            Ok(result) => {
                let entry_price = result.effective_price;
                let position = Position {
                    token_address: token_address.to_string(),
                    entry_price,
                    amount: actual_amount,
                    timestamp: std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_secs(),
                    stop_loss: entry_price * 0.8, // 20% stop loss
                    take_profit: entry_price * 5.0, // 5x take profit
                    current_value: actual_amount,
                    unrealized_pnl: 0.0,
                };

                let mut positions = self.positions.write().await;
                positions.insert(token_address.to_string(), position);

                *self.capital.lock() -= actual_amount;

                self.metrics.lock().total_trades += 1;

                tracing::info!(
                    "Position opened: {} @ {:.8} ETH (Amount: {:.4})",
                    token_address,
                    entry_price,
                    actual_amount
                );

                Ok(true)
            }
            Err(e) => {
                tracing::error!("Trade execution failed: {}", e);
                Ok(false)
            }
        }
    }

    pub async fn update_positions(&self) -> Result<()> {
        let mut positions = self.positions.write().await;
        let mut positions_to_close = Vec::new();

        for (token_addr, position) in positions.iter_mut() {
            if let Ok(current_price) = self.okx_client.get_token_price(token_addr).await {
                let current_value = position.amount * current_price / position.entry_price;
                position.current_value = current_value;
                position.unrealized_pnl = current_value - position.amount;

                // Check exit conditions
                if current_price <= position.stop_loss || current_price >= position.take_profit {
                    positions_to_close.push(token_addr.clone());
                }

                // Time-based exit (24 hours)
                let elapsed = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs() - position.timestamp;

                if elapsed > 86400 { // 24 hours
                    positions_to_close.push(token_addr.clone());
                }
            }
        }

        for token_addr in positions_to_close {
            if let Some(position) = positions.remove(&token_addr) {
                self.close_position(position).await?;
            }
        }

        Ok(())
    }

    async fn close_position(&self, position: Position) -> Result<()> {
        let current_price = self.okx_client.get_token_price(&position.token_address).await?;
        let exit_value = position.amount * current_price / position.entry_price;
        let pnl = exit_value - position.amount;

        *self.capital.lock() += exit_value;

        let mut metrics = self.metrics.lock();
        metrics.total_pnl += pnl;
        if pnl > 0.0 {
            metrics.winning_trades += 1;
        }
        metrics.win_rate = metrics.winning_trades as f64 / metrics.total_trades as f64;

        tracing::info!(
            "Position closed: {} | PnL: {:.4} ETH ({:.1}%)",
            position.token_address,
            pnl,
            (pnl / position.amount) * 100.0
        );

        Ok(())
    }

    pub async fn get_portfolio_summary(&self) -> Result<serde_json::Value> {
        let positions = self.positions.read().await;
        let current_capital = *self.capital.lock();
        let metrics = self.metrics.lock();

        let mut total_value = current_capital;
        for position in positions.values() {
            total_value += position.current_value;
        }

        let total_return = ((total_value - 1000.0) / 1000.0) * 100.0;

        Ok(serde_json::json!({
            "current_capital": current_capital,
            "total_value": total_value,
            "total_return_pct": total_return,
            "active_positions": positions.len(),
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "win_rate": metrics.win_rate,
            "total_pnl": metrics.total_pnl,
            "positions": positions.values().collect::<Vec<_>>()
        }))
    }

    pub async fn emergency_close_all(&self) -> Result<()> {
        let mut positions = self.positions.write().await;
        let position_list: Vec<Position> = positions.drain().map(|(_, pos)| pos).collect();
        drop(positions);

        for position in position_list {
            self.close_position(position).await?;
        }

        tracing::warn!("Emergency close executed for all positions");
        Ok(())
    }

    pub fn get_current_capital(&self) -> f64 {
        *self.capital.lock()
    }

    pub async fn get_position_count(&self) -> usize {
        self.positions.read().await.len()
    }
}