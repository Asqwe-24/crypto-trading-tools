#!/usr/bin/env python3
import ccxt, pandas as pd, time
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from tabulate import tabulate
init(autoreset=True)

class MarketAnalyzer:
    def __init__(self, symbols=['BTC/USDT', 'ETH/USDT']):
        self.exchange = ccxt.gate({'enableRateLimit': True})
        self.symbols = symbols
        self.signal_history = []
        
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
        """Calculate nearby support and resistance levels"""
        highs = df['high'].tail(50).values
        lows = df['low'].tail(50).values
        
        # Find resistance (price struggling to break above)
        resistance_levels = []
        for i in range(len(highs)-5):
            if highs[i] == max(highs[i:i+5]):
                resistance_levels.append(highs[i])
        
        # Find support (price bouncing from)
        support_levels = []
        for i in range(len(lows)-5):
            if lows[i] == min(lows[i:i+5]):
                support_levels.append(lows[i])
        
        # Get closest levels
        resistance_above = [r for r in resistance_levels if r > current_price]
        support_below = [s for s in support_levels if s < current_price]
        
        nearest_resistance = min(resistance_above) if resistance_above else current_price * 1.002
        nearest_support = max(support_below) if support_below else current_price * 0.998
        
        return nearest_support, nearest_resistance
    
    def calculate_volatility(self, df):
        """Calculate recent volatility for duration estimation"""
        returns = df['close'].pct_change().tail(20)
        volatility = returns.std()
        return volatility
    
    def analyze_symbol(self, symbol):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
            
            current_price = df['close'].iloc[-1]
            prices = df['close'].tolist()
            rsi = self.calculate_rsi(prices)
            
            # Volume analysis
            vol_ratio = df['volume'].iloc[-1] / df['volume'].tail(10).mean()
            
            # VWAP
            df['vwap'] = (df['volume']*(df['high']+df['low']+df['close'])/3).cumsum()/df['volume'].cumsum()
            vwap = df['vwap'].iloc[-1]
            dist_vwap = ((current_price - vwap)/vwap)*100
            
            # Order book
            ob_imb = self.get_orderbook_imbalance(symbol)
            
            # Support/Resistance
            support, resistance = self.get_support_resistance(df, current_price)
            
            # Volatility for duration
            volatility = self.calculate_volatility(df)
            
            # Price momentum
            price_change_1m = ((current_price - df['close'].iloc[-2])/df['close'].iloc[-2])*100
            price_change_5m = ((current_price - df['close'].iloc[-6])/df['close'].iloc[-6])*100
            
            # Generate detailed signal
            signal_data = self.generate_detailed_signal(
                symbol, current_price, rsi, ob_imb, vol_ratio, 
                dist_vwap, price_change_1m, price_change_5m,
                support, resistance, volatility
            )
            
            return signal_data
            
        except Exception as e:
            print(f"{Fore.RED}Error analyzing {symbol}: {e}")
            return None
    
    def generate_detailed_signal(self, symbol, price, rsi, ob_imb, vol_ratio, 
                                 dist_vwap, price_1m, price_5m, support, resistance, volatility):
        """Generate comprehensive trading signal with entry/exit details"""
        
        score = 0
        reasons = []
        
        # RSI signals
        if rsi < 30:
            score += 3
            reasons.append("🔥 RSI Oversold (Strong)")
        elif rsi < 35:
            score += 2
            reasons.append("📉 RSI Oversold")
        elif rsi > 70:
            score -= 3
            reasons.append("🔥 RSI Overbought (Strong)")
        elif rsi > 65:
            score -= 2
            reasons.append("📈 RSI Overbought")
        
        # Order book signals
        if ob_imb > 0.4:
            score += 3
            reasons.append("💪 Strong Bid Pressure")
        elif ob_imb > 0.3:
            score += 2
            reasons.append("👍 Bid Pressure")
        elif ob_imb < -0.4:
            score -= 3
            reasons.append("💪 Strong Sell Pressure")
        elif ob_imb < -0.3:
            score -= 2
            reasons.append("👎 Sell Pressure")
        
        # Volume
        if vol_ratio > 2.0:
            score += 2
            reasons.append("🔊 Very High Volume")
        elif vol_ratio > 1.5:
            score += 1
            reasons.append("📊 High Volume")
        
        # VWAP
        if -0.1 < dist_vwap < 0.1:
            score += 1
            reasons.append("🎯 Near VWAP (Fair Value)")
        
        # Momentum
        if price_1m > 0.1 and score > 0:
            score += 1
            reasons.append("🚀 Positive Momentum")
        elif price_1m < -0.1 and score < 0:
            score -= 1
            reasons.append("📉 Negative Momentum")
        
        # Support/Resistance proximity
        dist_to_support = ((price - support) / support) * 100
        dist_to_resistance = ((resistance - price) / price) * 100
        
        if dist_to_support < 0.5:
            score += 1
            reasons.append("🛡️ Near Support")
        if dist_to_resistance < 0.5:
            score -= 1
            reasons.append("🚧 Near Resistance")
        
        # Determine signal type
        if score >= 6:
            signal_type = "STRONG BUY"
            color = Fore.GREEN
            confidence = "VERY HIGH"
        elif score >= 4:
            signal_type = "BUY"
            color = Fore.GREEN
            confidence = "HIGH"
        elif score >= 2:
            signal_type = "WEAK BUY"
            color = Fore.YELLOW
            confidence = "MODERATE"
        elif score <= -6:
            signal_type = "STRONG SELL"
            color = Fore.RED
            confidence = "VERY HIGH"
        elif score <= -4:
            signal_type = "SELL"
            color = Fore.RED
            confidence = "HIGH"
        elif score <= -2:
            signal_type = "WEAK SELL"
            color = Fore.YELLOW
            confidence = "MODERATE"
        else:
            signal_type = "WAIT"
            color = Fore.YELLOW
            confidence = "LOW"
        
        # Calculate optimal entry/exit prices
        if "BUY" in signal_type:
            # For buys, enter slightly below current price (limit order)
            best_entry = price * 0.9995  # 0.05% below
            stop_loss = price * 0.999    # 0.1% stop
            take_profit = price * 1.0015  # 0.15% target
            
            # Estimated duration based on volatility
            if volatility > 0.01:  # High volatility
                duration = "2-5 minutes"
            else:
                duration = "5-10 minutes"
                
        elif "SELL" in signal_type:
            best_entry = price * 1.0005  # 0.05% above
            stop_loss = price * 1.001    # 0.1% stop
            take_profit = price * 0.9985  # 0.15% target
            
            if volatility > 0.01:
                duration = "2-5 minutes"
            else:
                duration = "5-10 minutes"
        else:
            best_entry = price
            stop_loss = None
            take_profit = None
            duration = "Wait for signal"
        
        return {
            'symbol': symbol,
            'signal': signal_type,
            'confidence': confidence,
            'color': color,
            'score': score,
            'reasons': reasons,
            'current_price': price,
            'best_entry': best_entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'duration': duration,
            'rsi': rsi,
            'ob_imbalance': ob_imb,
            'volume_ratio': vol_ratio,
            'dist_vwap': dist_vwap,
            'support': support,
            'resistance': resistance,
            'volatility': volatility
        }
    
    def display_signal(self, signal):
        if not signal:
            return
        
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.YELLOW}📊 {signal['symbol']} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{Fore.CYAN}{'='*120}")
        
        # Market overview
        print(f"\n{Fore.WHITE}💹 MARKET OVERVIEW:")
        market_data = [
            ['Current Price', f"${signal['current_price']:,.2f}"],
            ['Support Level', f"${signal['support']:,.2f}  ({((signal['current_price']-signal['support'])/signal['support']*100):+.2f}%)"],
            ['Resistance Level', f"${signal['resistance']:,.2f}  ({((signal['resistance']-signal['current_price'])/signal['current_price']*100):+.2f}%)"],
            ['Volatility', f"{signal['volatility']*100:.2f}%"]
        ]
        print(tabulate(market_data, tablefmt='simple'))
        
        # Indicators
        print(f"\n{Fore.WHITE}📈 TECHNICAL INDICATORS:")
        indicators = [
            ['RSI (7)', f"{signal['rsi']:.2f}"],
            ['Volume Ratio', f"{signal['volume_ratio']:.2f}x"],
            ['VWAP Distance', f"{signal['dist_vwap']:.2f}%"],
            ['Order Book', f"{signal['ob_imbalance']:+.3f}"]
        ]
        print(tabulate(indicators, tablefmt='simple'))
        
        # Signal reasons
        if signal['reasons']:
            print(f"\n{Fore.CYAN}🔍 SIGNAL FACTORS:")
            for reason in signal['reasons']:
                print(f"  • {reason}")
        
        # Main signal
        print(f"\n{signal['color']}{'='*120}")
        print(f"{signal['color']}🎯 SIGNAL: {signal['signal']} | Confidence: {signal['confidence']} | Strength: {signal['score']}")
        print(f"{signal['color']}{'='*120}{Fore.RESET}")
        
        # Trading setup (only for actionable signals)
        if signal['signal'] != 'WAIT':
            print(f"\n{Fore.YELLOW}{'='*120}")
            print(f"{Fore.YELLOW}💼 TRADING SETUP:")
            print(f"{Fore.YELLOW}{'='*120}")
            
            setup_data = [
                ['', ''],
                [f'{Fore.CYAN}📍 BEST ENTRY PRICE', f'{Fore.WHITE}${signal["best_entry"]:,.2f}  (Set limit order here)'],
                [f'{Fore.WHITE}💰 CURRENT PRICE', f'{Fore.WHITE}${signal["current_price"]:,.2f}'],
                [f'{Fore.RED}🛑 STOP LOSS', f'{Fore.RED}${signal["stop_loss"]:,.2f}  (-{((signal["current_price"]-signal["stop_loss"])/signal["current_price"]*100):.2f}%)'],
                [f'{Fore.GREEN}🎯 TAKE PROFIT', f'{Fore.GREEN}${signal["take_profit"]:,.2f}  (+{((signal["take_profit"]-signal["current_price"])/signal["current_price"]*100):.2f}%)'],
                ['', ''],
                [f'{Fore.MAGENTA}⏱️  EXPECTED DURATION', f'{Fore.MAGENTA}{signal["duration"]}'],
                [f'{Fore.CYAN}💎 RISK/REWARD', f'{Fore.CYAN}1:1.5']
            ]
            
            print(tabulate(setup_data, tablefmt='plain'))
            print(f"{Fore.YELLOW}{'='*120}")
            
            # Action recommendation
            if "STRONG" in signal['signal']:
                print(f"\n{signal['color']}⚡ ACTION: {signal['signal']} - High probability setup!")
            else:
                print(f"\n{signal['color']}📌 ACTION: Consider {signal['signal']} if conditions align")
        
        else:
            print(f"\n{Fore.YELLOW}⏸️  No actionable signal at this time. Wait for better setup.")
        
        # Save to history if strong signal
        if abs(signal['score']) >= 4:
            self.signal_history.append({
                'time': datetime.now(),
                'symbol': signal['symbol'],
                'signal': signal['signal'],
                'price': signal['current_price'],
                'score': signal['score']
            })
    
    def show_signal_history(self):
        """Display recent strong signals"""
        if self.signal_history:
            recent = self.signal_history[-5:]  # Last 5 signals
            print(f"\n{Fore.CYAN}{'='*120}")
            print(f"{Fore.YELLOW}📋 RECENT STRONG SIGNALS (Last 5):")
            print(f"{Fore.CYAN}{'='*120}")
            
            history_table = []
            for s in recent:
                color = Fore.GREEN if 'BUY' in s['signal'] else Fore.RED
                history_table.append([
                    s['time'].strftime('%H:%M:%S'),
                    s['symbol'],
                    f"{color}{s['signal']}{Fore.RESET}",
                    f"${s['price']:,.2f}",
                    s['score']
                ])
            
            print(tabulate(history_table, 
                          headers=['Time', 'Symbol', 'Signal', 'Price', 'Score'],
                          tablefmt='grid'))
    
    def run(self, interval=60):
        print(f"{Fore.CYAN}{'='*120}")
        print(f"{Fore.YELLOW}🤖 ADVANCED MARKET ANALYZER - Gate.io")
        print(f"{Fore.YELLOW}📡 Real-time BUY/SELL Signals with Entry/Exit Prices")
        print(f"{Fore.CYAN}{'='*120}")
        print(f"{Fore.WHITE}Monitoring: {', '.join(self.symbols)}")
        print(f"{Fore.WHITE}Update Interval: {interval} seconds")
        print(f"{Fore.WHITE}Press Ctrl+C to stop\n")
        
        try:
            iteration = 0
            while True:
                iteration += 1
                print(f"\n{Fore.MAGENTA}{'▼'*120}")
                print(f"{Fore.MAGENTA}🔄 UPDATE #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{Fore.MAGENTA}{'▼'*120}")
                
                for symbol in self.symbols:
                    signal = self.analyze_symbol(symbol)
                    if signal:
                        self.display_signal(signal)
                    time.sleep(2)
                
                # Show history
                self.show_signal_history()
                
                print(f"\n{Fore.YELLOW}{'─'*120}")
                print(f"{Fore.YELLOW}⏰ Next analysis in {interval} seconds...")
                print(f"{Fore.YELLOW}{'─'*120}")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}{'='*120}")
            print(f"{Fore.YELLOW}🛑 Analyzer stopped")
            print(f"{Fore.YELLOW}{'='*120}")
            self.show_signal_history()
            print(f"\n{Fore.GREEN}Total strong signals captured: {len(self.signal_history)}")

if __name__ == "__main__":
    MarketAnalyzer().run(interval=60)
