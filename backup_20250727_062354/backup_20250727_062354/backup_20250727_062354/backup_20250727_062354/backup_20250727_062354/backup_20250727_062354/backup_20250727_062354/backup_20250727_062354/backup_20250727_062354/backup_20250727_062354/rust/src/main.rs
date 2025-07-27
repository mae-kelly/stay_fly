use std::sync::Arc;
use tokio::signal;
use tracing::{info, error};
use tracing_subscriber;
use anyhow::Result;

use alpha_mirror::{MimicEngine, alpha_tracker::AlphaTracker};

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    
    info!("🚀 Elite Alpha Mirror Bot - Production Version");
    info!("💰 Target: $1K → $1M via real-time mempool mirroring");
    info!("⚡ Using OKX DEX for live execution");
    
    let mut engine = MimicEngine::new().await?;
    
    let alpha_tracker = AlphaTracker::new();
    
    info!("🔍 Discovering elite wallets from recent 100x tokens...");
    let hundred_x_tokens = alpha_tracker.find_100x_tokens(30).await?;
    info!("Found {} tokens with 100x+ performance", hundred_x_tokens.len());
    
    info!("🧠 Identifying elite deployers and snipers...");
    let mut deployer_wallets = alpha_tracker.find_deployer_wallets(&hundred_x_tokens).await?;
    let mut sniper_wallets = alpha_tracker.find_sniper_wallets(&hundred_x_tokens).await?;
    deployer_wallets.append(&mut sniper_wallets);
    
    info!("📊 Updating wallet performance scores...");
    alpha_tracker.update_wallet_scores(&mut deployer_wallets).await?;
    
    info!("Loading {} elite wallets into engine", deployer_wallets.len());
    engine.load_alpha_wallets(deployer_wallets.clone()).await?;
    
    alpha_tracker.export_alpha_wallets(&deployer_wallets).await?;
    info!("Elite wallets exported to alpha_wallets.json");
    
    info!("🚀 Starting real-time mempool monitoring...");
    info!("👀 Watching {} elite wallets", deployer_wallets.len());
    info!("💰 Initial capital: ${:.2}", engine.get_portfolio_value());
    
    let engine_arc = Arc::new(engine);
    let monitoring_engine = engine_arc.clone();
    
    // Start real-time monitoring with completed mempool scanner
    let monitoring_task = tokio::spawn(async move {
        if let Err(e) = monitoring_engine.start_monitoring().await {
            error!("Monitoring error: {}", e);
        }
    });
    
    // Portfolio management with OKX integration
    let portfolio_engine = engine_arc.clone();
    let portfolio_task = tokio::spawn(async move {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(30));
        
        loop {
            interval.tick().await;
            
            if let Ok(summary) = portfolio_engine.execution.get_portfolio_summary().await {
                info!("📊 Portfolio: {}", summary);
            }
            
            if let Err(e) = portfolio_engine.execution.update_positions().await {
                error!("Position update error: {}", e);
            }
            
            // Check if target achieved
            let current_value = portfolio_engine.get_portfolio_value();
            if current_value >= 1000000.0 {
                info!("🎉 TARGET ACHIEVED: $1K → $1M!");
                break;
            }
        }
    });
    
    info!("✅ Elite Alpha Mirror Bot is now LIVE!");
    info!("🎯 Target: Transform $1,000 into $1,000,000");
    info!("⚡ Method: Real-time elite wallet mirroring via OKX DEX");
    info!("Press Ctrl+C to stop");
    
    tokio::select! {
        _ = signal::ctrl_c() => {
            info!("Shutdown signal received");
        }
        _ = monitoring_task => {
            error!("Monitoring task ended unexpectedly");
        }
        _ = portfolio_task => {
            info!("Portfolio task completed");
        }
    }
    
    info!("Performing emergency close of all positions...");
    engine_arc.execution.emergency_close_all().await?;
    
    let final_value = engine_arc.get_portfolio_value();
    let initial_value = 1000.0;
    let total_return = ((final_value - initial_value) / initial_value) * 100.0;
    
    info!("📊 FINAL RESULTS:");
    info!("💰 Final Portfolio Value: ${:.2}", final_value);
    info!("📈 Total Return: {:.2}%", total_return);
    
    if total_return >= 100000.0 {
        info!("🎉 LEGENDARY: $1K → $1M+ achieved via elite wallet mirroring!");
    } else if total_return >= 900.0 {
        info!("💎 EXCELLENT: 10x+ return achieved!");
    } else if total_return > 0.0 {
        info!("📈 PROFIT: Positive return via smart money following");
    }
    
    info!("Elite Alpha Mirror Bot shutdown complete");
    Ok(())
}
