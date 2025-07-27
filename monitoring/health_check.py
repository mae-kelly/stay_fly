#!/usr/bin/env python3
"""
System Health Check and Monitoring
"""

import asyncio
import aiohttp
import json
import time
import psutil
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import os

@dataclass
class HealthMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    uptime_seconds: float
    active_connections: int
    trade_success_rate: float
    last_trade_time: Optional[datetime]
    portfolio_value: float

@dataclass
class AlertThreshold:
    metric: str
    threshold: float
    severity: str  # 'warning', 'critical'
    message: str

class HealthMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.metrics_history: List[HealthMetrics] = []
        self.alerts: List[str] = []
        
        # Alert thresholds
        self.thresholds = [
            AlertThreshold('cpu_percent', 80.0, 'warning', 'High CPU usage'),
            AlertThreshold('cpu_percent', 95.0, 'critical', 'Critical CPU usage'),
            AlertThreshold('memory_percent', 85.0, 'warning', 'High memory usage'),
            AlertThreshold('memory_percent', 95.0, 'critical', 'Critical memory usage'),
            AlertThreshold('disk_percent', 90.0, 'warning', 'High disk usage'),
            AlertThreshold('disk_percent', 98.0, 'critical', 'Critical disk usage'),
            AlertThreshold('trade_success_rate', 50.0, 'warning', 'Low trade success rate'),
            AlertThreshold('trade_success_rate', 30.0, 'critical', 'Critical trade success rate'),
        ]
        
        logging.info("🩺 Health monitor initialized")
    
    async def collect_metrics(self) -> HealthMetrics:
        """Collect system and application metrics"""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        # Application metrics
        uptime = time.time() - self.start_time
        
        # Mock trading metrics (replace with actual data)
        trade_success_rate = 75.0  # Replace with actual calculation
        portfolio_value = 1250.0   # Replace with actual portfolio value
        
        metrics = HealthMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent,
            network_sent=net_io.bytes_sent,
            network_recv=net_io.bytes_recv,
            uptime_seconds=uptime,
            active_connections=len(psutil.net_connections()),
            trade_success_rate=trade_success_rate,
            last_trade_time=datetime.now() - timedelta(minutes=5),
            portfolio_value=portfolio_value
        )
        
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        return metrics
    
    def check_alerts(self, metrics: HealthMetrics) -> List[str]:
        """Check metrics against thresholds and generate alerts"""
        new_alerts = []
        
        for threshold in self.thresholds:
            metric_value = getattr(metrics, threshold.metric, 0)
            
            if threshold.metric == 'trade_success_rate':
                # Reverse logic for success rate (alert if below threshold)
                if metric_value < threshold.threshold:
                    alert = f"🚨 {threshold.severity.upper()}: {threshold.message} ({metric_value:.1f}%)"
                    new_alerts.append(alert)
            else:
                # Normal logic (alert if above threshold)
                if metric_value > threshold.threshold:
                    alert = f"🚨 {threshold.severity.upper()}: {threshold.message} ({metric_value:.1f}%)"
                    new_alerts.append(alert)
        
        return new_alerts
    
    async def send_discord_alert(self, alert: str):
        """Send alert to Discord webhook"""
        webhook_url = os.getenv('DISCORD_WEBHOOK')
        if not webhook_url:
            return
        
        try:
            embed = {
                "title": "🚨 Elite Bot Alert",
                "description": alert,
                "color": 0xff0000,  # Red color
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "Elite Alpha Mirror Bot Monitoring"
                }
            }
            
            payload = {"embeds": [embed]}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 204:
                        logging.info("📱 Alert sent to Discord")
        except Exception as e:
            logging.error(f"❌ Failed to send Discord alert: {e}")
    
    async def generate_health_report(self) -> Dict:
        """Generate comprehensive health report"""
        if not self.metrics_history:
            return {"status": "no_data", "message": "No metrics available"}
        
        latest = self.metrics_history[-1]
        
        # Calculate averages over last hour
        hour_ago = datetime.now() - timedelta(hours=1)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > hour_ago]
        
        if recent_metrics:
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            avg_success_rate = sum(m.trade_success_rate for m in recent_metrics) / len(recent_metrics)
        else:
            avg_cpu = latest.cpu_percent
            avg_memory = latest.memory_percent
            avg_success_rate = latest.trade_success_rate
        
        # Determine overall health status
        if any(alert.startswith("🚨 CRITICAL") for alert in self.alerts[-10:]):
            status = "critical"
        elif any(alert.startswith("🚨 WARNING") for alert in self.alerts[-10:]):
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "timestamp": latest.timestamp.isoformat(),
            "uptime_hours": latest.uptime_seconds / 3600,
            "system": {
                "cpu_percent": latest.cpu_percent,
                "memory_percent": latest.memory_percent,
                "disk_percent": latest.disk_percent,
                "active_connections": latest.active_connections
            },
            "averages_1h": {
                "cpu_percent": avg_cpu,
                "memory_percent": avg_memory,
                "trade_success_rate": avg_success_rate
            },
            "trading": {
                "success_rate": latest.trade_success_rate,
                "portfolio_value": latest.portfolio_value,
                "last_trade": latest.last_trade_time.isoformat() if latest.last_trade_time else None
            },
            "recent_alerts": self.alerts[-5:],  # Last 5 alerts
            "metrics_count": len(self.metrics_history)
        }
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous health monitoring"""
        logging.info(f"🩺 Starting health monitoring (interval: {interval_seconds}s)")
        
        while True:
            try:
                metrics = await self.collect_metrics()
                new_alerts = self.check_alerts(metrics)
                
                for alert in new_alerts:
                    logging.warning(alert)
                    self.alerts.append(f"{datetime.now().isoformat()}: {alert}")
                    await self.send_discord_alert(alert)
                
                # Log periodic health status
                if len(self.metrics_history) % 10 == 0:  # Every 10 minutes
                    report = await self.generate_health_report()
                    logging.info(f"📊 Health Status: {report['status']} | CPU: {metrics.cpu_percent:.1f}% | Memory: {metrics.memory_percent:.1f}% | Portfolio: ${metrics.portfolio_value:.2f}")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logging.error(f"❌ Health monitoring error: {e}")
                await asyncio.sleep(interval_seconds)

# HTTP Health Check Endpoint
from aiohttp import web

async def health_endpoint(request):
    """HTTP health check endpoint for Docker/K8s"""
    monitor = request.app['health_monitor']
    report = await monitor.generate_health_report()
    
    status_code = 200
    if report.get('status') == 'critical':
        status_code = 503
    elif report.get('status') == 'warning':
        status_code = 200  # Still healthy enough
    
    return web.json_response(report, status=status_code)

async def metrics_endpoint(request):
    """Prometheus-style metrics endpoint"""
    monitor = request.app['health_monitor']
    
    if not monitor.metrics_history:
        return web.Response(text="# No metrics available\n", content_type='text/plain')
    
    latest = monitor.metrics_history[-1]
    
    metrics_text = f"""# HELP cpu_percent CPU usage percentage
# TYPE cpu_percent gauge
cpu_percent {latest.cpu_percent}

# HELP memory_percent Memory usage percentage
# TYPE memory_percent gauge
memory_percent {latest.memory_percent}

# HELP disk_percent Disk usage percentage
# TYPE disk_percent gauge
disk_percent {latest.disk_percent}

# HELP trade_success_rate Trading success rate percentage
# TYPE trade_success_rate gauge
trade_success_rate {latest.trade_success_rate}

# HELP portfolio_value Current portfolio value in USD
# TYPE portfolio_value gauge
portfolio_value {latest.portfolio_value}

# HELP uptime_seconds Bot uptime in seconds
# TYPE uptime_seconds counter
uptime_seconds {latest.uptime_seconds}
"""
    
    return web.Response(text=metrics_text, content_type='text/plain')

async def create_health_server():
    """Create HTTP server for health checks"""
    app = web.Application()
    monitor = HealthMonitor()
    app['health_monitor'] = monitor
    
    app.router.add_get('/health', health_endpoint)
    app.router.add_get('/metrics', metrics_endpoint)
    
    # Start monitoring in background
    asyncio.create_task(monitor.start_monitoring())
    
    return app

async def main():
    """Run health monitoring server"""
    app = await create_health_server()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logging.info("🩺 Health monitoring server started on port 8080")
    logging.info("🔗 Health check: http://localhost:8080/health")
    logging.info("📊 Metrics: http://localhost:8080/metrics")
    
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logging.info("🛑 Health monitoring server stopping")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
