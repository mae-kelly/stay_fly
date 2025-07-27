# Insert this into okx_focused_trading.py to replace simulation

async def execute_okx_trade_live(self, trade_params: OKXTradeParams) -> bool:
    """Execute LIVE trade through OKX DEX - REAL MONEY"""
    print(f"🚀 EXECUTING LIVE OKX TRADE")
    print(f"   From: {trade_params.from_token[:10]}...")
    print(f"   To: {trade_params.to_token[:10]}...")
    print(f"   Amount: {trade_params.amount}")
    
    # First get quote
    quote = await self.get_okx_token_quote(
        trade_params.from_token,
        trade_params.to_token,
        trade_params.amount
    )
    
    if not quote:
        print("❌ Failed to get OKX quote")
        return False
    
    # Validate quote
    gas_estimate = int(quote.get('estimatedGas', '0'))
    price_impact = float(quote.get('priceImpact', '0'))
    
    print(f"📊 Quote Analysis:")
    print(f"   Gas Estimate: {gas_estimate:,}")
    print(f"   Price Impact: {price_impact:.2f}%")
    print(f"   Output Amount: {quote.get('toTokenAmount', '0')}")
    
    # Safety checks
    if price_impact > 5.0:
        print(f"⚠️ High price impact ({price_impact:.2f}%), skipping trade")
        return False
        
    if gas_estimate > 500000:
        print(f"⚠️ High gas estimate ({gas_estimate:,}), skipping trade")
        return False
    
    # Execute swap
    path = '/api/v5/dex/aggregator/swap'
    swap_data = {
        'chainId': '1',
        'fromTokenAddress': trade_params.from_token,
        'toTokenAddress': trade_params.to_token,
        'amount': trade_params.amount,
        'slippage': trade_params.slippage,
        'userWalletAddress': CONFIG.get('WALLET_ADDRESS', ''),
        'referrer': 'elite_mirror_bot',
        'gasPrice': '',
        'gasPriceLevel': 'high'
    }
    
    body = json.dumps(swap_data)
    headers = self._get_okx_headers('POST', path, body)
    
    try:
        url = f"{self.base_url}{path}"
        print(f"🔄 Sending LIVE trade to OKX...")
        
        async with self.session.post(url, data=body, headers=headers) as response:
            data = await response.json()
            
            if data.get('code') == '0':
                result = data.get('data', [{}])[0]
                tx_hash = result.get('txHash', 'N/A')
                
                print(f"✅ OKX LIVE Trade Executed Successfully!")
                print(f"   TX Hash: {tx_hash}")
                print(f"   Status: {result.get('status', 'submitted')}")
                
                # Monitor transaction status
                await self.monitor_transaction_status(tx_hash)
                
                return True
            else:
                print(f"❌ OKX Trade Failed: {data.get('msg', 'Unknown error')}")
                print(f"   Error Code: {data.get('code')}")
                
    except Exception as e:
        print(f"❌ OKX Trade Exception: {e}")
    
    return False
