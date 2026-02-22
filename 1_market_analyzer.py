#!/usr/bin/env python3
"""
TOOL 1: MARKET ANALYZER - SPOT TRADING SIGNALS ONLY
Analyzes markets and provides SPOT buy/sell signals (no leverage/futures)
"""
import ccxt, pandas as pd, time, json, os
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from tabulate import tabulate
init(autoreset=True)

class MarketAnalyzer:
    def __init__(self, symbols=['BTC/USDT', 'ETH/USDT']):
        self.exchange = ccxt.gate({'enableRateLimit': True})
        self.symbols = symbols
        self.signal_history = []
        self.state_file = 'analyzer_state.json'
        self.load_state()
        
    def save_state(self):
        """Save signal history to resume later"""
        state = {
            'signal_history': [
                {
                    'time': s['time'].isoformat(),
                    'symbol': s['symbol'],
                    'signal': s['signal'],
                    'price': s['price'],
                    'score': s['score']
                } for s in self.signal_history
            ],
            'last_save': datetime.now().isoformat()
        }
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except:
            pass
    
    def load_state(self):
        """Load previous session"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.signal_history = [
                        {
                            'time': datetime.fromisoformat(s['time']),
                            'symbol': s['symbol'],
                            'signal': s['signal'],
                            'price': s['price'],
                            'score': s['score']
                        } for s in state.get('signal_history', [])
                    ]
                    print(f"{Fore.GREEN}✓ Loaded {len(self.signal_history)} previous signals")
        except:
            pass
        
    def calculate_rsi(self, prices, period=7):
        if len(prices) < period + 1: return 50
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_gain, avg_loss = sum(gains[-period:])/period, sum(losses[-period:])/period
        if avg_loss == 0: return 100
        return 100 - (100 / (1 + avg_gain/avg_loss))
    
    def get_orderbook_imbalance(self, symbol):
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=10)
            bid_vol = sum([b[1] for b in orderbook['bids'][:5]])
            ask_vol = sum([a[1] for a in orderbook['asks'][:5]])
            total = bid_vol + ask_vol
            return (bid_vol - ask_vol) / total if total > 0 else 0
        except: return 0
    
    def get_support_resistance(self, df, current_price):
        """Calculate support/resistance levels"""
        highs = df['high'].tail(50).values
        lows = df['low'].tail(50).values
        
        resistance_levels = []
        for i in range(len(highs)-5):
            if highs[i] == max(highs[i:i+5]):
                resistance_levels.append(highs[i])
        
        support_levels = []
        for i in range(len(lows)-5):
            if lows[i] == min(lows[i:i+5]):
                support_levels.append(lows[i])
        
        resistance_above = [r for r in resistance_levels if r > current_price]
        support_below = [s for s in support_levels if s < current_price]
        
        nearest_resistance = min(resistance_above) if resistance_above else current_price * 1.002
        nearest_support = max(support_below) if support_below else current_price * 0.998
        
        return nearest_support, nearest_resistance
    
    def calculate_volatility(self, df):
        """Calculate volatility for timing"""
        returns = df['close'].pct_change().tail(20)
        return returns.std()
    
    def analyze_symbol(self, symbol):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
            
            current_price = df['close'].iloc[-1]
            prices = df['close'].tolist()
            rsi = self.calculate_rsi(prices)
            
            vol_ratio = df['volume'].iloc[-1] / df['volume'].tail(10).mean()
            
            df['vwap'] = (df['volume']*(df['high']+df['low']+df['close'])/3).cumsum()/df['volume'].cumsum()
            vwap = df['vwap'].iloc[-1]
            dist_vwap = ((current_price - vwap)/vwap)*100
            
            ob_imb = self.get_orderbook_imbalance(symbol)
            support, resistance = self.get_support_resistance(df, current_price)
            volatility = self.calculate_volatility(df)
            
            price_change_1m = ((current_price - df['close'].iloc[-2])/df['close'].iloc[-2])*100
            
            signal_data = self.generate_spot_signal(
                symbol, current_price, rsi, ob_imb, vol_ratio, 
                dist_vwap, price_change_1m, support, resistance, volatility
            )
            
            return signal_data
            
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
            return None
    
    def generate_spot_signal(self, symbol, price, rsi, ob_imb, vol_ratio, 
                            dist_vwap, price_1m, support, resistance, volatility):
        """Generate SPOT trading signal (no leverage)"""
        
        score = 0
        reasons = []
        
        # RSI
        if rsi < 30:
            score += 3
            reasons.append("🔥 RSI Oversold")
        elif rsi < 35:
            score += 2
            reasons.append("📉 RSI Low")
        elif rsi > 70:
            score -= 3
            reasons.append("🔥 RSI Overbought")
        elif rsi > 65:
            score -= 2
            reasons.append("📈 RSI High")
        
        # Order book
        if ob_imb > 0.4:
            score += 3
            reasons.append("💪 Strong Buying")
        elif ob_imb > 0.3:
            score += 2
            reasons.append("👍 Buying Pressure")
        elif ob_imb < -0.4:
            score -= 3
            reasons.append("💪 Strong Selling")
        elif ob_imb < -0.3:
            score -= 2
            reasons.append("👎 Selling Pressure")
        
        # Volume
        if vol_ratio > 2.0:
            score += 2
            reasons.append("🔊 High Volume")
        elif vol_ratio > 1.5:
            score += 1
            reasons.append("📊 Good Volume")
        
        # VWAP
        if -0.1 < dist_vwap < 0.1:
            score += 1
            reasons.append("🎯 Fair Price (VWAP)")
        
        # Momentum
        if price_1m > 0.1 and score > 0:
            score += 1
            reasons.append("🚀 Momentum")
        
        # Support/Resistance
        dist_to_support = ((price - support) / support) * 100
        dist_to_resistance = ((resistance - price) / price) * 100
        
        if dist_to_support < 0.5:
            score += 1
            reasons.append("🛡️ At Support")
        if dist_to_resistance < 0.5:
            score -= 1
            reasons.append("🚧 At Resistance")
        
        # Signal type
        if score >= 6:
            signal_type = "STRONG BUY SPOT"
            color = Fore.GREEN
            confidence = "VERY HIGH"
        elif score >= 4:
            signal_type = "BUY SPOT"
            color = Fore.GREEN
            confidence = "HIGH"
        elif score >= 2:
            signal_type = "WEAK BUY SPOT"
            color = Fore.YELLOW
            confidence = "MODERATE"
        elif score <= -6:
            signal_type = "STRONG SELL SPOT"
            color = Fore.RED
            confidence = "VERY HIGH"
        elif score <= -4:
            signal_type = "SELL SPOT"
            color = Fore.RED
            confidence = "HIGH"
        elif score <= -2:
            signal_type = "WEAK SELL SPOT"
            color = Fore.YELLOW
            confidence = "MODERATE"
        else:
            signal_type = "WAIT / HOLD"
            color = Fore.YELLOW
            confidence = "LOW"
        
        # SPOT trade setup (no leverage)
        if "BUY" in signal_type:
            entry_price = price * 0.9995
            stop_loss = price * 0.999
            take_profit = price * 1.0015
            duration = "2-5 min" if volatility > 0.01 else "5-10 min"
            position_type = "SPOT BUY"
            
        elif "SELL" in signal_type:
            entry_price = price * 1.0005
            stop_loss = price * 1.001
            take_profit = price * 0.9985
            duration = "2-5 min" if volatility > 0.01 else "5-10 min"
            position_type = "SPOT SELL"
        else:
            entry_price = price
            stop_loss = None
            take_profit = None
            duration = "Wait"
            position_type = "NO POSITION"
        
        return {
            'symbol': symbol,
            'signal': signal_type,
            'position_type': position_type,
            'confidence': confidence,
            'color': color,
            'score': score,
            'reasons': reasons,
            'current_price': price,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'duration': duration,
            'rsi': rsi,
            'ob_imbalance': ob_imb,
            'volume_ratio': vol_ratio,
            'support': support,
            'resistance': resistance
        }
    
    def display_signal(self, signal):
        if not signal:
            return
        
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.YELLOW}📊 {signal['symbol']} - SPOT TRADING SIGNAL - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{Fore.CYAN}{'='*120}")
        
        # Market info
        print(f"\n{Fore.WHITE}💹 MARKET INFO:")
        market_data = [
            ['Current Price', f"${signal['current_price']:,.2f}"],
            ['Support', f"${signal['support']:,.2f}"],
            ['Resistance', f"${signal['resistance']:,.2f}"],
            ['RSI', f"{signal['rsi']:.2f}"],
            ['Volume', f"{signal['volume_ratio']:.2f}x"],
            ['Order Book', f"{signal['ob_imbalance']:+.3f}"]
        ]
        print(tabulate(market_data, tablefmt='simple'))
        
        # Signal
        print(f"\n{signal['color']}{'='*120}")
        print(f"{signal['color']}🎯 {signal['signal']} | Confidence: {signal['confidence']} | Score: {signal['score']}")
        print(f"{signal['color']}{'='*120}{Fore.RESET}")
        
        if signal['reasons']:
            print(f"\n{Fore.CYAN}Reasons:")
            for r in signal['reasons']:
                print(f"  • {r}")
        
        # Trade setup for SPOT only
        if signal['signal'] != 'WAIT / HOLD':
            print(f"\n{Fore.YELLOW}{'='*120}")
            print(f"{Fore.YELLOW}💼 SPOT TRADE SETUP (NO LEVERAGE):")
            print(f"{Fore.YELLOW}{'='*120}")
            
            setup = [
                ['', ''],
                [f'{Fore.MAGENTA}📍 POSITION TYPE', f'{Fore.MAGENTA}{signal["position_type"]} (SPOT ONLY - NO FUTURES)'],
                [f'{Fore.CYAN}📍 ENTRY PRICE', f'{Fore.WHITE}${signal["entry_price"]:,.2f}'],
                [f'{Fore.WHITE}💰 CURRENT PRICE', f'{Fore.WHITE}${signal["current_price"]:,.2f}'],
                [f'{Fore.RED}🛑 STOP LOSS', f'{Fore.RED}${signal["stop_loss"]:,.2f} ({((signal["stop_loss"]-signal["current_price"])/signal["current_price"]*100):+.2f}%)'],
                [f'{Fore.GREEN}🎯 TAKE PROFIT', f'{Fore.GREEN}${signal["take_profit"]:,.2f} ({((signal["take_profit"]-signal["current_price"])/signal["current_price"]*100):+.2f}%)'],
                ['', ''],
                [f'{Fore.CYAN}⏱️  DURATION', f'{Fore.CYAN}{signal["duration"]}'],
                [f'{Fore.CYAN}💎 RISK/REWARD', f'{Fore.CYAN}1:1.5']
            ]
            
            print(tabulate(setup, tablefmt='plain'))
            print(f"{Fore.YELLOW}{'='*120}")
        
        # Save signal if strong
        if abs(signal['score']) >= 4:
            self.signal_history.append({
                'time': datetime.now(),
                'symbol': signal['symbol'],
                'signal': signal['signal'],
                'price': signal['current_price'],
                'score': signal['score']
            })
            self.save_state()
    
    def show_history(self):
        if self.signal_history:
            recent = self.signal_history[-10:]
            print(f"\n{Fore.CYAN}{'='*120}")
            print(f"{Fore.YELLOW}📋 RECENT STRONG SIGNALS:")
            print(f"{Fore.CYAN}{'='*120}")
            
            history = []
            for s in recent:
                color = Fore.GREEN if 'BUY' in s['signal'] else Fore.RED
                history.append([
                    s['time'].strftime('%H:%M:%S'),
                    s['symbol'],
                    f"{color}{s['signal']}{Fore.RESET}",
                    f"${s['price']:,.2f}",
                    s['score']
                ])
            
            print(tabulate(history, headers=['Time', 'Symbol', 'Signal', 'Price', 'Score'], tablefmt='grid'))
    
    def run(self, interval=60):
        print(f"{Fore.CYAN}{'='*120}")
        print(f"{Fore.YELLOW}🤖 SPOT TRADING ANALYZER - Gate.io (NO LEVERAGE/FUTURES)")
        print(f"{Fore.CYAN}{'='*120}")
        print(f"Symbols: {', '.join(self.symbols)} | Interval: {interval}s")
        print(f"Press Ctrl+C to stop (progress auto-saved)\n")
        
        try:
            iteration = 0
            while True:
                iteration += 1
                print(f"\n{Fore.MAGENTA}{'▼'*120}")
                print(f"{Fore.MAGENTA}UPDATE #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{Fore.MAGENTA}{'▼'*120}")
                
                for symbol in self.symbols:
                    signal = self.analyze_symbol(symbol)
                    if signal:
                        self.display_signal(signal)
                    time.sleep(2)
                
                self.show_history()
                self.save_state()
                
                print(f"\n{Fore.YELLOW}⏰ Next in {interval}s...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.save_state()
            print(f"\n{Fore.GREEN}✓ Progress saved. Total signals: {len(self.signal_history)}")

if __name__ == "__main__":
    MarketAnalyzer().run()
