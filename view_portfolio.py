import json
from datetime import datetime

def view_paper_portfolio():
    try:
        with open('data/paper_trading_session.json', 'r') as f:
            data = json.load(f)
        
        print("📊 PAPER TRADING PORTFOLIO")
        print("=" * 50)
        
        starting = data['starting_capital']
        current_cash = data['current_capital']
        
        print(f"💰 Starting Capital: ${starting:.2f}")
        print(f"💵 Current Cash: ${current_cash:.2f}")
        
        if data['positions']:
            print(f"\n🎯 Current Positions ({len(data['positions'])}):")
            for pos in data['positions']:
                entry_time = datetime.fromisoformat(pos['entry_time']).strftime('%m/%d %H:%M')
                print(f"  📈 {pos['token_symbol']}")
                print(f"     Entry: ${pos['entry_price']:.6f} on {entry_time}")
                print(f"     Quantity: {pos['quantity']:,.2f}")
                print(f"     Invested: ${pos['usd_invested']:.2f}")
                print(f"     Whale: {pos['whale_wallet'][:10]}...")
                print(f"     Reason: {pos['entry_reason']}")
                print()
        
        if data['trades']:
            print(f"📈 Recent Trades ({len(data['trades'])}):")
            for trade in data['trades'][-5:]:  # Last 5 trades
                time_str = datetime.fromisoformat(trade['timestamp']).strftime('%m/%d %H:%M')
                action_emoji = "🛒" if trade['action'] == 'BUY' else "💰"
                
                print(f"  {action_emoji} {trade['action']} {trade['token_symbol']}")
                print(f"     Price: ${trade['price']:.6f}")
                print(f"     Amount: ${trade['usd_amount']:.2f}")
                print(f"     Time: {time_str}")
                if trade['pnl'] != 0:
                    pnl_emoji = "📈" if trade['pnl'] > 0 else "📉"
                    print(f"     P&L: {pnl_emoji} ${trade['pnl']:.2f}")
                print()
        
        # Calculate total return
        total_positions_value = sum(pos['usd_invested'] for pos in data['positions'])
        total_portfolio = current_cash + total_positions_value
        total_return = ((total_portfolio - starting) / starting) * 100
        
        print(f"🏆 PERFORMANCE SUMMARY:")
        print(f"   Portfolio Value: ${total_portfolio:.2f}")
        print(f"   Total Return: {total_return:+.1f}%")
        
        if total_return >= 100:
            print("🎉 CONGRATULATIONS! You've doubled your money!")
        elif total_return >= 900:
            print("🚀 INCREDIBLE! You're approaching the $1K → $10K milestone!")
        
    except FileNotFoundError:
        print("❌ No paper trading session found. Start trading first!")

if __name__ == "__main__":
    view_paper_portfolio()
