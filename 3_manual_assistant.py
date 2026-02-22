#!/usr/bin/env python3
import ccxt, pandas as pd, time
from datetime import datetime
from colorama import Fore, init
from tabulate import tabulate
import getpass
init(autoreset=True)

class Assistant:
    def __init__(self, api_key=None, api_secret=None):
        if api_key:
            self.exchange = ccxt.gate({'apiKey':api_key, 'secret':api_secret, 'enableRateLimit':True})
            self.trading = True
            print(f"{Fore.GREEN}✓ Gate.io API Connected")
        else:
            self.exchange = ccxt.gate({'enableRateLimit':True})
            self.trading = False
            print(f"{Fore.YELLOW}ℹ Read-Only Mode - No API")
        self.symbols = ['BTC/USDT', 'ETH/USDT']
        self.stop_loss_pct = 0.001  # 0.1%
        self.take_profit_pct = 0.0015  # 0.15%
    
    def analyze(self, symbol):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1m', limit=50)
            df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
            price = df['c'].iloc[-1]
            
            deltas = [df['c'].iloc[i]-df['c'].iloc[i-1] for i in range(1,len(df))]
            gains, losses = [d if d>0 else 0 for d in deltas], [-d if d<0 else 0 for d in deltas]
            rsi = 100 - (100/(1+sum(gains[-7:])/sum(losses[-7:]))) if sum(losses[-7:])>0 else 100
            
            ob = self.exchange.fetch_order_book(symbol, limit=10)
            bid = sum([b[1] for b in ob['bids'][:5]])
            ask = sum([a[1] for a in ob['asks'][:5]])
            imb = (bid-ask)/(bid+ask) if (bid+ask)>0 else 0
            
            score = 0
            signals = []
            
            if rsi < 30:
                score += 3
                signals.append(("RSI Oversold", f"{rsi:.1f}", "Strong Buy"))
            elif rsi > 70:
                score -= 3
                signals.append(("RSI Overbought", f"{rsi:.1f}", "Strong Sell"))
            elif rsi < 40:
                score += 1
                signals.append(("RSI Low", f"{rsi:.1f}", "Buy"))
            elif rsi > 60:
                score -= 1
                signals.append(("RSI High", f"{rsi:.1f}", "Sell"))
            
            if imb > 0.4:
                score += 2
                signals.append(("Strong Bid Pressure", f"{imb:+.2f}", "Buy"))
            elif imb < -0.4:
                score -= 2
                signals.append(("Strong Ask Pressure", f"{imb:+.2f}", "Sell"))
            
            action = 'STRONG BUY' if score>=5 else 'BUY' if score>=3 else 'STRONG SELL' if score<=-5 else 'SELL' if score<=-3 else 'HOLD'
            color = Fore.GREEN if 'BUY' in action else Fore.RED if 'SELL' in action else Fore.YELLOW
            
            print(f"\n{Fore.CYAN}{'='*110}")
            print(f"{Fore.YELLOW}📊 {symbol} ANALYSIS")
            print(f"{Fore.CYAN}{'='*110}")
            print(f"{Fore.WHITE}Current Price: ${price:,.2f}")
            print(f"\n{tabulate([['RSI',f'{rsi:.2f}'],['Order Book Imbalance',f'{imb:+.3f}']], headers=['Indicator','Value'], tablefmt='grid')}")
            
            if signals:
                print(f"\n{Fore.CYAN}Detected Signals:")
                print(tabulate(signals, headers=['Signal','Value','Direction'], tablefmt='grid'))
            
            print(f"\n{color}{'='*110}")
            print(f"{color}RECOMMENDATION: {action} (Strength Score: {score})")
            print(f"{color}{'='*110}{Fore.RESET}")
            
            if 'BUY' in action:
                stop_price = price * (1 - self.stop_loss_pct)
                target_price = price * (1 + self.take_profit_pct)
                stop_pct = -self.stop_loss_pct * 100
                tp_pct = self.take_profit_pct * 100
                risk_amount = price - stop_price
                reward_amount = target_price - price
                
                print(f"\n{Fore.YELLOW}{'='*110}")
                print(f"{Fore.YELLOW}📈 SUGGESTED LONG TRADE SETUP:")
                print(f"{Fore.YELLOW}{'='*110}")
                print(f"{Fore.WHITE}Entry Price:     ${price:,.2f}")
                print(f"{Fore.RED}Stop Loss:       ${stop_price:,.2f}  ({stop_pct:.2f}%)  [Risk: ${risk_amount:.2f}]")
                print(f"{Fore.GREEN}Take Profit:     ${target_price:,.2f}  (+{tp_pct:.2f}%)  [Reward: ${reward_amount:.2f}]")
                print(f"{Fore.CYAN}Risk/Reward:     1:{reward_amount/risk_amount:.2f}")
                print(f"{Fore.MAGENTA}Position Size:   Calculate based on your risk tolerance")
                print(f"{Fore.YELLOW}{'='*110}")
                
            elif 'SELL' in action:
                stop_price = price * (1 + self.stop_loss_pct)
                target_price = price * (1 - self.take_profit_pct)
                stop_pct = self.stop_loss_pct * 100
                tp_pct = -self.take_profit_pct * 100
                risk_amount = stop_price - price
                reward_amount = price - target_price
                
                print(f"\n{Fore.YELLOW}{'='*110}")
                print(f"{Fore.YELLOW}📉 SUGGESTED SHORT TRADE SETUP:")
                print(f"{Fore.YELLOW}{'='*110}")
                print(f"{Fore.WHITE}Entry Price:     ${price:,.2f}")
                print(f"{Fore.RED}Stop Loss:       ${stop_price:,.2f}  (+{stop_pct:.2f}%)  [Risk: ${risk_amount:.2f}]")
                print(f"{Fore.GREEN}Take Profit:     ${target_price:,.2f}  ({tp_pct:.2f}%)  [Reward: ${reward_amount:.2f}]")
                print(f"{Fore.CYAN}Risk/Reward:     1:{reward_amount/risk_amount:.2f}")
                print(f"{Fore.MAGENTA}Position Size:   Calculate based on your risk tolerance")
                print(f"{Fore.YELLOW}{'='*110}")
                
        except Exception as e:
            print(f"{Fore.RED}Error analyzing {symbol}: {e}")
    
    def run(self):
        print(f"{Fore.CYAN}{'='*110}\n{Fore.YELLOW}MANUAL TRADING ASSISTANT - Gate.io\n{Fore.CYAN}{'='*110}\n")
        try:
            while True:
                print(f"\n{Fore.MAGENTA}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Analyzing markets...")
                for sym in self.symbols:
                    self.analyze(sym)
                    time.sleep(2)
                input(f"\n{Fore.YELLOW}Press ENTER to refresh signals (or Ctrl+C to quit)... {Fore.WHITE}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Assistant stopped.")

if __name__ == "__main__":
    use_api = input("Connect Gate.io API for live trading? (yes/no): ").lower()
    key = getpass.getpass("API Key: ") if use_api=='yes' else None
    secret = getpass.getpass("API Secret: ") if use_api=='yes' else None
    
    if use_api == 'yes':
        print(f"{Fore.RED}⚠️  WARNING: Only use API keys with SPOT trading permissions!")
        print(f"{Fore.RED}⚠️  NEVER enable withdrawal permissions!{Fore.RESET}\n")
    
    Assistant(key, secret).run()
