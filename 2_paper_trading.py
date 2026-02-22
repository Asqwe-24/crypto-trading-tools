#!/usr/bin/env python3
"""
TOOL 2: PAPER TRADING - SPOT ONLY (NO LEVERAGE)
Simulates SPOT trading with virtual money. Saves progress automatically.
"""
import ccxt, pandas as pd, time, json, os
from datetime import datetime
from colorama import Fore, init
from tabulate import tabulate
init(autoreset=True)

class PaperBot:
    def __init__(self, balance):
        self.exchange = ccxt.gate({'enableRateLimit': True})
        self.initial = balance
        self.balance = balance
        self.positions = []
        self.trades = []
        self.symbols = ['BTC/USDT', 'ETH/USDT']
        self.stop_loss_pct = 0.001
        self.take_profit_pct = 0.0015
        self.state_file = 'paper_trading_state.json'
        self.load_state()
        
    def save_state(self):
        """Save trading state to resume later"""
        state = {
            'balance': self.balance,
            'initial': self.initial,
            'positions': [
                {
                    'symbol': p['symbol'],
                    'entry_price': p['entry_price'],
                    'qty': p['qty'],
                    'stop': p['stop'],
                    'target': p['target'],
                    'entry_time': p['entry_time'].isoformat(),
                    'position_value': p['position_value']
                } for p in self.positions
            ],
            'trades': self.trades,
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
                    
                    # Ask if user wants to resume
                    print(f"{Fore.YELLOW}Previous session found!")
                    print(f"Balance: ${state.get('balance', 0):,.2f}")
                    print(f"Trades: {len(state.get('trades', []))}")
                    resume = input(f"{Fore.CYAN}Resume? (yes/no): {Fore.RESET}").lower()
                    
                    if resume == 'yes':
                        self.balance = state.get('balance', self.initial)
                        self.initial = state.get('initial', self.initial)
                        self.trades = state.get('trades', [])
                        self.positions = [
                            {
                                'symbol': p['symbol'],
                                'entry_price': p['entry_price'],
                                'qty': p['qty'],
                                'stop': p['stop'],
                                'target': p['target'],
                                'entry_time': datetime.fromisoformat(p['entry_time']),
                                'position_value': p['position_value']
                            } for p in state.get('positions', [])
                        ]
                        print(f"{Fore.GREEN}✓ Resumed with ${self.balance:,.2f}")
                    else:
                        # Start fresh
                        os.remove(self.state_file)
                        print(f"{Fore.YELLOW}Starting fresh session")
        except:
            pass
    
    def analyze(self, symbol):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1m', limit=50)
            df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
            price = df['c'].iloc[-1]
            
            deltas = [df['c'].iloc[i] - df['c'].iloc[i-1] for i in range(1,len(df))]
            gains = [d if d>0 else 0 for d in deltas]
            losses = [-d if d<0 else 0 for d in deltas]
            rsi = 100 - (100/(1 + sum(gains[-7:])/sum(losses[-7:]))) if sum(losses[-7:])>0 else 100
            
            ob = self.exchange.fetch_order_book(symbol, limit=10)
            bid_vol = sum([b[1] for b in ob['bids'][:5]])
            ask_vol = sum([a[1] for a in ob['asks'][:5]])
            imb = (bid_vol-ask_vol)/(bid_vol+ask_vol) if (bid_vol+ask_vol)>0 else 0
            
            score = 0
            if rsi < 35: score += 2
            if imb > 0.3: score += 2
            
            return {'symbol':symbol, 'price':price, 'buy':score>=4}
        except:
            return None
    
    def open_position(self, symbol, price):
        qty = (self.balance * 0.01) / (price * self.stop_loss_pct)
        stop_price = price * (1 - self.stop_loss_pct)
        target_price = price * (1 + self.take_profit_pct)
        
        pos = {
            'symbol': symbol,
            'entry_price': price,
            'qty': qty,
            'stop': stop_price,
            'target': target_price,
            'entry_time': datetime.now(),
            'position_value': price * qty
        }
        self.positions.append(pos)
        self.balance -= price * qty
        
        print(f"\n{Fore.GREEN}{'='*100}")
        print(f"{Fore.GREEN}🟢 SPOT POSITION OPENED (NO LEVERAGE)")
        print(f"{Fore.GREEN}{'='*100}")
        print(f"Symbol: {symbol} | Type: SPOT BUY")
        print(f"Entry: ${price:,.2f} | Qty: {qty:.6f}")
        print(f"Stop: ${stop_price:,.2f} | Target: ${target_price:,.2f}")
        print(f"{Fore.GREEN}{'='*100}")
        
        self.save_state()
        
    def check_positions(self):
        for pos in self.positions[:]:
            try:
                price = self.exchange.fetch_ticker(pos['symbol'])['last']
                fees = pos['entry_price'] * pos['qty'] * 0.002
                
                if price <= pos['stop']:
                    pnl = (price - pos['entry_price']) * pos['qty'] - fees
                    self.balance += price * pos['qty'] + pnl
                    self.trades.append({'pnl':pnl, 'type':'STOP'})
                    print(f"\n{Fore.RED}🔴 STOP LOSS | {pos['symbol']} | P&L: ${pnl:.2f}")
                    self.positions.remove(pos)
                    self.save_state()
                    
                elif price >= pos['target']:
                    pnl = (price - pos['entry_price']) * pos['qty'] - fees
                    self.balance += price * pos['qty'] + pnl
                    self.trades.append({'pnl':pnl, 'type':'TP'})
                    print(f"\n{Fore.GREEN}🟢 TAKE PROFIT | {pos['symbol']} | P&L: ${pnl:.2f}")
                    self.positions.remove(pos)
                    self.save_state()
                    
                elif (datetime.now()-pos['entry_time']).seconds > 300:
                    pnl = (price - pos['entry_price']) * pos['qty'] - fees
                    self.balance += price * pos['qty'] + pnl
                    self.trades.append({'pnl':pnl, 'type':'TIMEOUT'})
                    color = Fore.GREEN if pnl>0 else Fore.RED
                    print(f"\n{color}⏱  TIMEOUT | {pos['symbol']} | P&L: ${pnl:.2f}")
                    self.positions.remove(pos)
                    self.save_state()
            except:
                pass
    
    def get_pnl(self):
        unrealized = 0
        for pos in self.positions:
            try:
                curr = self.exchange.fetch_ticker(pos['symbol'])['last']
                unrealized += (curr - pos['entry_price']) * pos['qty'] - (pos['entry_price']*pos['qty']*0.002)
            except:
                pass
        
        realized = sum(t['pnl'] for t in self.trades)
        total_pnl = realized + unrealized
        total_value = self.balance + sum(self.exchange.fetch_ticker(p['symbol'])['last']*p['qty'] for p in self.positions)
        
        return {
            'unrealized': unrealized,
            'realized': realized,
            'total': total_pnl,
            'value': total_value,
            'roi': ((total_value-self.initial)/self.initial)*100
        }
    
    def display_dashboard(self):
        pnl = self.get_pnl()
        
        print(f"\n{Fore.CYAN}{'='*100}")
        print(f"{Fore.YELLOW}💰 SPOT PAPER TRADING (NO LEVERAGE)")
        print(f"{Fore.CYAN}{'='*100}")
        
        color = Fore.GREEN if pnl['total']>=0 else Fore.RED
        
        data = [
            ['Starting', f"${self.initial:,.2f}"],
            ['Balance', f"${self.balance:,.2f}"],
            ['Total Value', f"${pnl['value']:,.2f}"],
            [f"{color}Total P&L{Fore.RESET}", f"{color}${pnl['total']:,.2f}{Fore.RESET}"],
            [f"{color}ROI{Fore.RESET}", f"{color}{pnl['roi']:+.2f}%{Fore.RESET}"],
            ['Trades', len(self.trades)],
            ['Wins', len([t for t in self.trades if t['pnl']>0])],
            ['Win Rate', f"{len([t for t in self.trades if t['pnl']>0])/len(self.trades)*100:.1f}%" if self.trades else "0%"]
        ]
        
        print(tabulate(data, tablefmt='simple'))
        
        if self.positions:
            print(f"\n{Fore.YELLOW}Active SPOT Positions:")
            for p in self.positions:
                try:
                    curr = self.exchange.fetch_ticker(p['symbol'])['last']
                    upnl = (curr-p['entry_price'])*p['qty']
                    color = Fore.GREEN if upnl>0 else Fore.RED
                    print(f"{color}{p['symbol']}: ${p['entry_price']:,.2f}→${curr:,.2f} ({upnl:+.2f})")
                except:
                    pass
        
        print(f"{Fore.CYAN}{'='*100}")
    
    def run(self):
        print(f"{Fore.CYAN}{'='*100}")
        print(f"{Fore.YELLOW}🤖 SPOT PAPER TRADING - Gate.io")
        print(f"{Fore.WHITE}Balance: ${self.initial:,.2f} (VIRTUAL)")
        print(f"{Fore.MAGENTA}Trading: SPOT ONLY (NO LEVERAGE/FUTURES)")
        print(f"{Fore.CYAN}{'='*100}\n")
        
        try:
            while True:
                print(f"{Fore.MAGENTA}[{datetime.now().strftime('%H:%M:%S')}]")
                self.check_positions()
                
                if len(self.positions)<3 and len(self.trades)<10:
                    for sym in self.symbols:
                        a = self.analyze(sym)
                        if a and a['buy']:
                            self.open_position(sym, a['price'])
                        time.sleep(1)
                
                self.display_dashboard()
                time.sleep(30)
                
        except KeyboardInterrupt:
            self.save_state()
            print(f"\n{Fore.GREEN}✓ Progress saved")
            self.display_dashboard()

if __name__ == "__main__":
    print(f"{Fore.CYAN}SPOT PAPER TRADING (NO LEVERAGE)\n")
    print("Starting balance options:")
    print("[1] $10   [2] $100   [3] $1,000   [4] $10,000")
    
    choice = input(f"{Fore.CYAN}Select (1-4): {Fore.RESET}").strip()
    balances = {'1':10, '2':100, '3':1000, '4':10000}
    balance = balances.get(choice, 10000)
    
    PaperBot(balance).run()
