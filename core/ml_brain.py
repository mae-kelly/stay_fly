import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import asyncio
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
import sqlite3
import aiohttp

@dataclass
class TradeSignal:
    confidence: float
    action: str
    token_address: str
    price_target: float
    risk_score: float
    ml_score: float

class CryptoPredictor(nn.Module):
    def __init__(self, input_size=50, hidden_size=128, num_layers=3):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.attention = nn.MultiheadAttention(hidden_size, 8, batch_first=True)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        return self.fc(attn_out[:, -1, :])

class MLBrain:
    def __init__(self):
        self.device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
        self.model = CryptoPredictor().to(self.device)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=0.001)
        self.criterion = nn.BCELoss()
        self.scaler = None
        self.session = None
        self.training_data = []
        self.real_time_features = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.load_historical_data()
        await self.train_initial_model()
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def load_historical_data(self):
        conn = sqlite3.connect('data/crypto_history.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS price_data 
                       (timestamp INTEGER, token TEXT, price REAL, volume REAL, 
                        market_cap REAL, volatility REAL, rsi REAL, macd REAL)''')
        
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 100}
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for coin in data:
                        features = self.extract_features(coin)
                        if features:
                            self.training_data.append(features)
        except:
            pass
        conn.close()
    
    def extract_features(self, coin_data):
        try:
            return [
                float(coin_data.get('current_price', 0)),
                float(coin_data.get('market_cap', 0)),
                float(coin_data.get('total_volume', 0)),
                float(coin_data.get('price_change_percentage_24h', 0)),
                float(coin_data.get('price_change_percentage_7d', 0)),
                float(coin_data.get('market_cap_rank', 999)),
                float(coin_data.get('circulating_supply', 0)),
                time.time()
            ]
        except:
            return None
    
    async def train_initial_model(self):
        if len(self.training_data) < 50:
            return
            
        data = np.array(self.training_data)
        X = torch.FloatTensor(data[:, :-2]).to(self.device)
        y = torch.FloatTensor((data[:, -2] > 5).astype(float)).to(self.device)
        
        X = X.unsqueeze(1).repeat(1, 10, 1)
        
        self.model.train()
        for epoch in range(100):
            self.optimizer.zero_grad()
            outputs = self.model(X).squeeze()
            loss = self.criterion(outputs, y)
            loss.backward()
            self.optimizer.step()
    
    async def predict_token_movement(self, token_data):
        if not token_data:
            return 0.5
        
        features = torch.FloatTensor(token_data).unsqueeze(0).unsqueeze(1).to(self.device)
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(features).item()
        return prediction
    
    async def generate_trade_signal(self, token_address, current_price, volume, market_data):
        features = [current_price, volume] + list(market_data.values())
        ml_score = await self.predict_token_movement(features)
        
        confidence = min(ml_score * 1.2, 0.95)
        action = "BUY" if ml_score > 0.7 else "HOLD"
        
        return TradeSignal(
            confidence=confidence,
            action=action,
            token_address=token_address,
            price_target=current_price * (1 + ml_score),
            risk_score=1 - ml_score,
            ml_score=ml_score
        )
    
    async def update_model(self, trade_result, actual_outcome):
        pass
