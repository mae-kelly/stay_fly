import torch
import torch.nn as nn
import numpy as np
import aiohttp
import asyncio
import json
import time
from datetime import datetime, timedelta
import os
import pandas as pd
from typing import Dict, List, Tuple

class WhalePredictor(nn.Module):
    def __init__(self, input_size=128, hidden_size=256, num_layers=4):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.3)
        self.attention = nn.MultiheadAttention(hidden_size, 8, batch_first=True)
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(hidden_size, 8, 512, dropout=0.2), 
            num_layers=3
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        trans_out = self.transformer(attn_out)
        return self.fc(trans_out[:, -1, :])

class WhaleMLEngine:
    def __init__(self):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.model = WhalePredictor().to(self.device)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=0.01)
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=100)
        self.criterion = nn.BCELoss()
        self.session = None
        self.training_data = []
        self.feature_scaler = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
            
    async def fetch_historical_whale_data(self):
        urls = [
            "https://api.etherscan.io/api?module=account&action=txlist&address={}&startblock=0&endblock=99999999&sort=desc&apikey={}",
            "https://api.dexscreener.com/latest/dex/pairs/ethereum",
            "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250",
            "https://api.whale-alert.io/v1/transactions?api_key={}&blockchain=ethereum&limit=100"
        ]
        
        all_data = []
        etherscan_key = os.getenv("ETHERSCAN_API_KEY", "")
        whale_alert_key = os.getenv("WHALE_ALERT_API_KEY", "")
        
        for url_template in urls:
            try:
                if "etherscan" in url_template:
                    for whale_addr in ["0xae2fc483527b8ef99eb5d9b44875f005ba1fae13", "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b"]:
                        url = url_template.format(whale_addr, etherscan_key)
                        async with self.session.get(url) as resp:
                            data = await resp.json()
                            if data.get("result"):
                                all_data.extend(data["result"][:50])
                elif "whale-alert" in url_template:
                    url = url_template.format(whale_alert_key)
                    async with self.session.get(url) as resp:
                        data = await resp.json()
                        if data.get("result"):
                            all_data.extend(data["result"])
                else:
                    async with self.session.get(url_template) as resp:
                        data = await resp.json()
                        if isinstance(data, list):
                            all_data.extend(data[:100])
                        elif "pairs" in data:
                            all_data.extend(data["pairs"][:100])
                            
                await asyncio.sleep(0.2)
            except Exception as e:
                continue
                
        return all_data
        
    def extract_features(self, raw_data):
        features = []
        labels = []
        
        for item in raw_data:
            try:
                feature_vector = []
                
                if "value" in item:
                    feature_vector.append(float(item.get("value", 0)) / 1e18)
                if "gasPrice" in item:
                    feature_vector.append(float(item.get("gasPrice", 0)) / 1e9)
                if "timeStamp" in item:
                    feature_vector.append(float(item.get("timeStamp", 0)))
                if "priceUsd" in item:
                    feature_vector.append(float(item.get("priceUsd", 0)))
                if "volume" in item and isinstance(item["volume"], dict):
                    feature_vector.append(float(item["volume"].get("h24", 0)))
                if "priceChange" in item and isinstance(item["priceChange"], dict):
                    change = float(item["priceChange"].get("h24", 0))
                    feature_vector.append(change)
                    labels.append(1.0 if change > 50 else 0.0)
                    
                while len(feature_vector) < 128:
                    feature_vector.append(0.0)
                    
                if len(feature_vector) == 128 and len(labels) == len(features) + 1:
                    features.append(feature_vector)
                    
            except:
                continue
                
        return np.array(features), np.array(labels)
        
    async def train_model(self, training_minutes=10):
        print(f"🧠 Training ML model for {training_minutes} minutes on M1 GPU...")
        
        raw_data = await self.fetch_historical_whale_data()
        print(f"📊 Fetched {len(raw_data)} data points")
        
        features, labels = self.extract_features(raw_data)
        if len(features) == 0:
            print("⚠️ No training data available")
            return
            
        X = torch.FloatTensor(features).unsqueeze(1).to(self.device)
        y = torch.FloatTensor(labels).to(self.device)
        
        self.model.train()
        start_time = time.time()
        epoch = 0
        best_loss = float('inf')
        
        while time.time() - start_time < training_minutes * 60:
            self.optimizer.zero_grad()
            outputs = self.model(X).squeeze()
            loss = self.criterion(outputs, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            self.scheduler.step()
            
            if loss.item() < best_loss:
                best_loss = loss.item()
                torch.save(self.model.state_dict(), 'whale_model_best.pth')
                
            if epoch % 100 == 0:
                print(f"Epoch {epoch}, Loss: {loss.item():.4f}")
                
            epoch += 1
            
        print(f"✅ Training complete! Best loss: {best_loss:.4f}")
        
    def predict_trade_success(self, whale_data, token_data):
        self.model.eval()
        
        features = []
        features.extend([
            float(whale_data.get("avg_multiplier", 0)),
            float(whale_data.get("success_rate", 0)),
            float(whale_data.get("total_trades", 0)),
            float(token_data.get("liquidity", 0)),
            float(token_data.get("volume_24h", 0)),
            float(token_data.get("price_change", 0))
        ])
        
        while len(features) < 128:
            features.append(0.0)
            
        x = torch.FloatTensor(features).unsqueeze(0).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            prediction = self.model(x).item()
            
        return prediction
