import asyncio
import aiohttp
import json
import sqlite3
import time
from datetime import datetime, timedelta

class DataCollector:
    def __init__(self):
        self.session = None
        self.db_path = 'data/crypto_history.db'
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.init_db()
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS historical_trades 
                       (timestamp INTEGER, token TEXT, price REAL, volume REAL, 
                        whale_wallet TEXT, trade_type TEXT, success INTEGER)''')
        conn.commit()
        conn.close()
    
    async def collect_realtime_data(self):
        while True:
            try:
                url = "https://api.coingecko.com/api/v3/coins/markets"
                params = {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 10}
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        await self.store_data(data)
            except:
                pass
            await asyncio.sleep(60)
    
    async def store_data(self, data):
        conn = sqlite3.connect(self.db_path)
        for coin in data:
            conn.execute('''INSERT INTO historical_trades VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (int(time.time()), coin['id'], coin['current_price'], 
                         coin['total_volume'], 'system', 'data_collection', 1))
        conn.commit()
        conn.close()
