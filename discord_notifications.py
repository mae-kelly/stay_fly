import aiohttp
import json
from datetime import datetime

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        
    async def send_trade_alert(self, trade_data):
        """Send trade alert to Discord"""
        embed = {
            "title": "🐋 Elite Wallet Activity Detected!",
            "color": 0x00ff00 if trade_data['action'] == 'BUY' else 0xff0000,
            "fields": [
                {
                    "name": "Action",
                    "value": f"📊 {trade_data['action']}",
                    "inline": True
                },
                {
                    "name": "Token",
                    "value": f"💎 {trade_data.get('token_symbol', 'Unknown')}",
                    "inline": True
                },
                {
                    "name": "Whale Wallet",
                    "value": f"🐋 {trade_data['whale_wallet'][:10]}...",
                    "inline": True
                },
                {
                    "name": "Amount",
                    "value": f"💰 ${trade_data['usd_amount']:.2f}",
                    "inline": True
                },
                {
                    "name": "Price",
                    "value": f"💵 ${trade_data['price']:.6f}",
                    "inline": True
                },
                {
                    "name": "Time",
                    "value": f"⏰ {datetime.now().strftime('%H:%M:%S')}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Elite Alpha Mirror Bot • Paper Trading Mode"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if trade_data.get('pnl', 0) != 0:
            pnl_color = "📈" if trade_data['pnl'] > 0 else "📉"
            embed["fields"].append({
                "name": "P&L",
                "value": f"{pnl_color} ${trade_data['pnl']:.2f}",
                "inline": True
            })
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        print("📱 Discord notification sent!")
                    else:
                        print(f"❌ Discord notification failed: {response.status}")
        except Exception as e:
            print(f"❌ Discord error: {e}")
    
    async def send_portfolio_update(self, portfolio_data):
        """Send portfolio update to Discord"""
        total_return = portfolio_data.get('total_return', 0)
        color = 0x00ff00 if total_return > 0 else 0xff0000 if total_return < 0 else 0xffff00
        
        embed = {
            "title": "📊 Portfolio Update",
            "color": color,
            "fields": [
                {
                    "name": "Starting Capital",
                    "value": f"💰 ${portfolio_data['starting_capital']:.2f}",
                    "inline": True
                },
                {
                    "name": "Current Value",
                    "value": f"💵 ${portfolio_data['current_value']:.2f}",
                    "inline": True
                },
                {
                    "name": "Total Return",
                    "value": f"📈 {total_return:+.1f}%",
                    "inline": True
                },
                {
                    "name": "Active Positions",
                    "value": f"🎯 {portfolio_data['position_count']}",
                    "inline": True
                },
                {
                    "name": "Total Trades",
                    "value": f"📊 {portfolio_data['trade_count']}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Elite Alpha Mirror Bot • Live Update"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        print("📱 Portfolio update sent to Discord!")
        except Exception as e:
            print(f"❌ Discord error: {e}")

# Example usage
async def test_discord():
    notifier = DiscordNotifier("https://discord.com/api/webhooks/1398448251933298740/lSnT3iPsfvb87RWdN0XCd3AjdFsCZiTpF-_I1ciV3rB2BqTpIszS6U6tFxAVk5QmM2q3")
    
    # Test trade alert
    await notifier.send_trade_alert({
        'action': 'BUY',
        'token_symbol': 'PEPE',
        'whale_wallet': '0xae2fc483527b8ef99eb5d9b44875f005ba1fae13',
        'usd_amount': 300.0,
        'price': 0.000012
    })

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_discord())
