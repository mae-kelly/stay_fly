use std::sync::Arc;
use tokio::signal;
use tracing::{info, error};
use tracing_subscriber;
use anyhow::Result;

use mimic_engine::{MimicEngine, alpha_tracker::AlphaTracker};

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    
    info!("Starting Elite Wallet Mimic Engine");
    info!("Target: $1K -> $1M via 100x token deployment mirroring");
    
    let mut engine = MimicEngine::new().await?;
    
    let alpha_tracker = AlphaTracker::new();
    
    info!("Scanning for 100x tokens from last 30 days...");
    let hundred_x_tokens = alpha_tracker.find_100x_tokens(30).await?;
    info!("Found {} tokens with 100x+ performance", hundred_x_tokens.len());
    
    info!("Identifying deployer wallets...");
    let mut deployer_wallets = alpha_tracker.find_deployer_wallets(&hundred_x_tokens).await?;
    info!("Found {} elite deployer wallets", deployer_wallets.len());
    
    info!("Identifying sniper wallets...");
    let mut sniper_wallets = alpha_tracker.find_sniper_wallets(&hundred_x_tokens).await?;
    info!("Found {} elite sniper wallets", sniper_wallets.len());
    
    deployer_wallets.append(&mut sniper_wallets);
    
    info!("Updating wallet performance scores...");
    alpha_tracker.update_wallet_scores(&mut deployer_wallets).await?;
    
    info!("Loading {} alpha wallets into engine", deployer_wallets.len());
    engine.load_alpha_wallets(deployer_wallets.clone()).await?;
    
    alpha_tracker.export_alpha_wallets(&deployer_wallets).await?;
    info!("Alpha wallets exported to alpha_wallets.json");
    
    info!("Starting mempool monitoring...");
    info!("Watching for transactions from {} elite wallets", deployer_wallets.len());
    info!("Initial capital: ${:.2}", engine.get_portfolio_value());
    
    let engine_clone = Arc::new(engine);
    let monitoring_engine = engine_clone.clone();
    
    let monitoring_task = tokio::spawn(async move {
        if let Err(e) = monitoring_engine.start_monitoring().await {
            error!("Monitoring error: {}", e);
        }
    });
    
    let portfolio_engine = engine_clone.clone();
    let portfolio_task = tokio::spawn(async move {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(30));
        
        loop {
            interval.tick().await;
            
            if let Ok(summary) = portfolio_engine.execution.get_portfolio_summary().await {
                info!("Portfolio Update: {}", summary);
            }
            
            if let Err(e) = portfolio_engine.execution.update_positions().await {
                error!("Position update error: {}", e);
            }
        }
    });
    
    info!("Elite Wallet Mimic Engine is now running...");
    info!("Press Ctrl+C to stop");
    
    tokio::select! {
        _ = signal::ctrl_c() => {
            info!("Shutdown signal received");
        }
        _ = monitoring_task => {
            error!("Monitoring task ended unexpectedly");
        }
        _ = portfolio_task => {
            error!("Portfolio task ended unexpectedly");
        }
    }
    
    info!("Performing emergency close of all positions...");
    engine_clone.execution.emergency_close_all().await?;
    
    let final_value = engine_clone.get_portfolio_value();
    let initial_value = 1000.0;
    let total_return = ((final_value - initial_value) / initial_value) * 100.0;
    
    info!("Final Portfolio Value: ${:.2}", final_value);
    info!("Total Return: {:.2}%", total_return);
    
    if total_return >= 100000.0 {
        info!("🎉 TARGET ACHIEVED: $1K -> $1M+ via elite wallet mirroring!");
    } else if total_return >= 1000.0 {
        info!("💎 EXCELLENT: 10x+ return achieved!");
    } else if total_return >= 100.0 {
        info!("📈 GOOD: Doubled money via smart money following");
    }
    
    info!("Elite Wallet Mimic Engine shutdown complete");
    Ok(())
}