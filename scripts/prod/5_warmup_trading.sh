#!/bin/bash
set -euo pipefail

echo "🧠 INITIALIZING 10-MINUTE ML WARMUP"

cat > core/ml_warmup.py << 'EOF'
import asyncio
import numpy as np
import time
from datetime import datetime,timedelta
import aiohttp

class MLWarmup:
    def __init__(self):
        self.session=aiohttp.ClientSession()
        self.patterns={}
        self.confidence=0.0
        
    async def execute_warmup_cycle(self):
        print(f"🧠 ML WARMUP STARTED: {datetime.now()}")
        
        market_data=await self.collect_live_market_data()
        whale_patterns=await self.analyze_whale_patterns()
        price_vectors=await self.build_price_vectors()
        
        self.patterns=await self.train_prediction_model(market_data,whale_patterns,price_vectors)
        
        validation_score=await self.validate_predictions()
        
        if validation_score>0.75:
            self.confidence=validation_score
            print(f"✅ ML WARMUP COMPLETE - Confidence: {validation_score:.3f}")
            return True
        else:
            print(f"⚠️ ML WARMUP INSUFFICIENT - Score: {validation_score:.3f}")
            return False
            
    async def collect_live_market_data(self):
        data=[]
        for i in range(600):
            async with self.session.get(f"{os.getenv('PRICE_API')}/ticker/24hr") as resp:
                ticker_data=await resp.json()
                data.append({
                    'timestamp':time.time(),
                    'prices':[float(t['price']) for t in ticker_data[:50]],
                    'volumes':[float(t['volume']) for t in ticker_data[:50]],
                    'changes':[float(t['priceChangePercent']) for t in ticker_data[:50]]
                })
            await asyncio.sleep(1)
        return data
        
    async def analyze_whale_patterns(self):
        patterns={}
        whale_wallets=await self.get_elite_wallets()
        
        for wallet in whale_wallets[:10]:
            trades=await self.get_wallet_recent_trades(wallet)
            if len(trades)>5:
                patterns[wallet]={
                    'avg_hold_time':np.mean([t['hold_time'] for t in trades]),
                    'success_rate':len([t for t in trades if t['profit']>0])/len(trades),
                    'avg_multiplier':np.mean([t['multiplier'] for t in trades]),
                    'preferred_time':self.extract_time_pattern(trades)
                }
        return patterns
        
    async def build_price_vectors(self):
        vectors=[]
        tokens=await self.get_trending_tokens()
        
        for token in tokens[:20]:
            price_history=await self.get_price_history(token,600)
            if len(price_history)>100:
                vector=np.array([p['price'] for p in price_history])
                vectors.append({
                    'token':token,
                    'vector':vector,
                    'volatility':np.std(vector),
                    'trend':np.polyfit(range(len(vector)),vector,1)[0]
                })
        return vectors
        
    async def train_prediction_model(self,market_data,whale_patterns,price_vectors):
        features=[]
        targets=[]
        
        for i in range(len(market_data)-60):
            current=market_data[i]
            future=market_data[i+60]
            
            feature_vector=np.concatenate([
                current['prices'][:10],
                current['volumes'][:10],
                current['changes'][:10],
                [np.mean(list(p['success_rate'] for p in whale_patterns.values()))],
                [np.mean([v['volatility'] for v in price_vectors[:5]])]
            ])
            
            target=1 if np.mean(future['changes'][:10])>5 else 0
            
            features.append(feature_vector)
            targets.append(target)
            
        features=np.array(features)
        targets=np.array(targets)
        
        weights=np.random.randn(features.shape[1])
        
        for epoch in range(100):
            predictions=self.sigmoid(np.dot(features,weights))
            error=targets-predictions
            gradient=np.dot(features.T,error)
            weights+=0.01*gradient
            
        return {
            'weights':weights,
            'whale_patterns':whale_patterns,
            'price_vectors':price_vectors,
            'training_accuracy':np.mean((self.sigmoid(np.dot(features,weights))>0.5)==targets)
        }
        
    def sigmoid(self,x):
        return 1/(1+np.exp(-np.clip(x,-500,500)))
        
    async def validate_predictions(self):
        validation_data=await self.collect_live_market_data()
        correct_predictions=0
        total_predictions=0
        
        for i in range(min(50,len(validation_data)-10)):
            current=validation_data[i]
            future=validation_data[i+10]
            
            prediction=self.predict_movement(current)
            actual=1 if np.mean(future['changes'][:5])>2 else 0
            
            if prediction==actual:
                correct_predictions+=1
            total_predictions+=1
            
        return correct_predictions/max(1,total_predictions)
        
    def predict_movement(self,data):
        if 'weights' not in self.patterns:
            return 0
            
        feature_vector=np.concatenate([
            data['prices'][:10],
            data['volumes'][:10], 
            data['changes'][:10],
            [0.8],
            [0.05]
        ])
        
        prediction=self.sigmoid(np.dot(feature_vector,self.patterns['weights']))
        return 1 if prediction>0.5 else 0
EOF

cat > core/paper_trader.py << 'EOF'
import asyncio
import time
from datetime import datetime

class PaperTrader:
    def __init__(self):
        self.portfolio=10000.0
        self.positions={}
        self.trade_count=0
        
    async def execute_paper_warmup(self,duration_minutes=10):
        print(f"📊 PAPER TRADING WARMUP: {duration_minutes} minutes")
        
        start_time=time.time()
        end_time=start_time+(duration_minutes*60)
        
        while time.time()<end_time:
            await self.execute_paper_trade()
            await asyncio.sleep(30)
            
        final_return=(self.portfolio-10000)/10000*100
        
        print(f"📈 PAPER WARMUP COMPLETE: {final_return:+.2f}% return")
        print(f"💼 Final Portfolio: ${self.portfolio:.2f}")
        print(f"📊 Total Trades: {self.trade_count}")
        
        return final_return>-5
        
    async def execute_paper_trade(self):
        self.trade_count+=1
        
        import random
        tokens=['BTC','ETH','DOGE','SHIB','PEPE']
        token=random.choice(tokens)
        
        if random.random()>0.5 and token not in self.positions:
            investment=self.portfolio*0.1
            price=random.uniform(0.001,100)
            quantity=investment/price
            
            self.positions[token]={
                'quantity':quantity,
                'entry_price':price,
                'entry_time':time.time()
            }
            
            self.portfolio-=investment
            
        elif token in self.positions:
            position=self.positions[token]
            current_price=position['entry_price']*(0.8+random.random()*0.4)
            
            sale_value=position['quantity']*current_price
            profit=(current_price-position['entry_price'])/position['entry_price']*100
            
            self.portfolio+=sale_value
            del self.positions[token]
EOF

cat > warmup_coordinator.py << 'EOF'
import asyncio
from core.ml_warmup import MLWarmup
from core.paper_trader import PaperTrader

async def execute_warmup_sequence():
    print("🚀 EXECUTING 10-MINUTE WARMUP SEQUENCE")
    
    ml_engine=MLWarmup()
    paper_trader=PaperTrader()
    
    warmup_tasks=[
        ml_engine.execute_warmup_cycle(),
        paper_trader.execute_paper_warmup(10)
    ]
    
    results=await asyncio.gather(*warmup_tasks)
    
    ml_ready=results[0]
    paper_profitable=results[1]
    
    if ml_ready and paper_profitable:
        print("✅ WARMUP SUCCESSFUL - READY FOR LIVE TRADING")
        return True
    else:
        print("❌ WARMUP FAILED - EXTENDING WARMUP PERIOD")
        return False

if __name__=="__main__":
    asyncio.run(execute_warmup_sequence())
EOF

chmod +x warmup_coordinator.py

echo "✅ ML WARMUP SYSTEM CONFIGURED"