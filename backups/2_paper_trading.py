#!/usr/bin/env python3
import ccxt, pandas as pd, time, json
from datetime import datetime
from colorama import Fore, Style, init
from tabulate import tabulate
init(autoreset=True)

class PaperBot:
    def __init__(self, balance=10):
        self.exchange = ccxt.gate({'enableRateLimit': True})
        self.balance = balance
        self.initial = balance
        self.positions = []
        self.trades = []
        self.symbols = ['BTC/USDT', 'ETH/USDT']
        self.stop_loss_pct = 0.001  # 0.1%
        self.take_profit_pct = 0.0015  # 0.15%
        
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
            
            return {'symbol':symbol, 'price':price, 'rsi':rsi, 'imb':imb, 'buy':score>=4}
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
        print(f"{Fore.GREEN}🟢 POSITION OPENED #{len(self.trades) + len(self.positions)}")
        print(f"{Fore.GREEN}{'='*100}")
        print(f"{Fore.WHITE}Symbol:       {symbol}")
        print(f"Entry Price:  ${price:,.2f}")
        print(f"Quantity:     {qty:.6f}")
        print(f"Position Val: ${pos['position_value']:,.2f}")
        print(f"{Fore.RED}Stop Loss:    ${stop_price:,.2f}  (-{self.stop_loss_pct*100:.2f}%)")
        print(f"{Fore.GREEN}Take Profit:  ${target_price:,.2f}  (+{self.take_profit_pct*100:.2f}%)")
        print(f"{Fore.GREEN}{'='*100}")
        
    def get_current_pnl(self):
        """Calculate real-time P&L for all open positions"""
        total_unrealized_pnl = 0
        total_position_value = 0
        
        for pos in self.positions:
            try:
                current_price = self.exchange.fetch_ticker(pos['symbol'])['last']
                unrealized_pnl = (current_price - pos['entry_price']) * pos['qty']
                unrealized_pnl -= (pos['entry_price'] * pos['qty'] * 0.001)  # Entry fee
                unrealized_pnl -= (current_price * pos['qty'] * 0.001)  # Exit fee estimate
                
                total_unrealized_pnl += unrealized_pnl
                total_position_value += current_price * pos['qty']
            except:
                pass
        
        # Realized P&L from closed trades
        realized_pnl = sum(t['pnl'] for t in self.trades)
        
        # Total P&L
        total_pnl = realized_pnl + total_unrealized_pnl
        
        # Total account value
        total_account_value = self.balance + total_position_value
        
        return {
            'unrealized_pnl': total_unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': total_pnl,
            'total_value': total_account_value,
            'roi': ((total_account_value - self.initial) / self.initial) * 100
        }
    
    def check_positions(self):
        for pos in self.positions[:]:
            try:
                ticker = self.exchange.fetch_ticker(pos['symbol'])
                price = ticker['last']
                
                # Calculate current P&L
                current_pnl = (price - pos['entry_price']) * pos['qty']
                current_pnl_pct = ((price - pos['entry_price']) / pos['entry_price']) * 100
                fees = (pos['entry_price'] * pos['qty'] * 0.002)
                
                if price <= pos['stop']:
                    pnl = (price - pos['entry_price']) * pos['qty'] - fees
                    pnl_pct = ((price - pos['entry_price']) / pos['entry_price']) * 100
                    self.balance += price * pos['qty'] + pnl
                    self.trades.append({'pnl':pnl, 'pnl_pct': pnl_pct, 'type': 'STOP LOSS'})
                    
                    print(f"\n{Fore.RED}{'='*100}")
                    print(f"{Fore.RED}🔴 STOP LOSS HIT")
                    print(f"{Fore.RED}{'='*100}")
                    print(f"Symbol:      {pos['symbol']}")
                    print(f"Entry:       ${pos['entry_price']:,.2f} → Exit: ${price:,.2f}  ({pnl_pct:.2f}%)")
                    print(f"P&L:         ${pnl:.2f}")
                    print(f"Duration:    {(datetime.now()-pos['entry_time']).seconds}s")
                    print(f"{Fore.RED}{'='*100}")
                    self.positions.remove(pos)
                    
                elif price >= pos['target']:
                    pnl = (price - pos['entry_price']) * pos['qty'] - fees
                    pnl_pct = ((price - pos['entry_price']) / pos['entry_price']) * 100
                    self.balance += price * pos['qty'] + pnl
                    self.trades.append({'pnl':pnl, 'pnl_pct': pnl_pct, 'type': 'TAKE PROFIT'})
                    
                    print(f"\n{Fore.GREEN}{'='*100}")
                    print(f"{Fore.GREEN}🟢 TAKE PROFIT HIT")
                    print(f"{Fore.GREEN}{'='*100}")
                    print(f"Symbol:      {pos['symbol']}")
                    print(f"Entry:       ${pos['entry_price']:,.2f} → Exit: ${price:,.2f}  (+{pnl_pct:.2f}%)")
                    print(f"P&L:         ${pnl:.2f}")
                    print(f"Duration:    {(datetime.now()-pos['entry_time']).seconds}s")
                    print(f"{Fore.GREEN}{'='*100}")
                    self.positions.remove(pos)
                    
                elif (datetime.now()-pos['entry_time']).seconds > 300:
                    pnl = (price - pos['entry_price']) * pos['qty'] - fees
                    pnl_pct = ((price - pos['entry_price']) / pos['entry_price']) * 100
                    self.balance += price * pos['qty'] + pnl
                    self.trades.append({'pnl':pnl, 'pnl_pct': pnl_pct, 'type': 'TIMEOUT'})
                    
                    color = Fore.GREEN if pnl > 0 else Fore.RED
                    print(f"\n{color}{'='*100}")
                    print(f"{color}⏱  TIMEOUT - Position Closed After 5 Minutes")
                    print(f"{color}{'='*100}")
                    print(f"Symbol:      {pos['symbol']}")
                    print(f"Entry:       ${pos['entry_price']:,.2f} → Exit: ${price:,.2f}  ({pnl_pct:+.2f}%)")
                    print(f"P&L:         ${pnl:.2f}")
                    print(f"{color}{'='*100}")
                    self.positions.remove(pos)
                    
            except Exception as e:
                print(f"{Fore.RED}Error checking position: {e}")
    
    def display_dashboard(self):
        """Show comprehensive dashboard with live P&L"""
        pnl_data = self.get_current_pnl()
        
        # Main header
        print(f"\n{Fore.CYAN}{'='*100}")
        print(f"{Fore.YELLOW}💰 PAPER TRADING DASHBOARD - LIVE P&L")
        print(f"{Fore.CYAN}{'='*100}")
        
        # Account summary with color-coded P&L
        pnl_color = Fore.GREEN if pnl_data['total_pnl'] >= 0 else Fore.RED
        roi_color = Fore.GREEN if pnl_data['roi'] >= 0 else Fore.RED
        
        account_data = [
            ['💵 Starting Balance', f"${self.initial:,.2f}"],
            ['💰 Current Balance', f"${self.balance:,.2f}"],
            ['📊 Total Account Value', f"${pnl_data['total_value']:,.2f}"],
            ['', ''],
            [f'{pnl_color}✓ Realized P&L{Fore.RESET}', f"{pnl_color}${pnl_data['realized_pnl']:,.2f}{Fore.RESET}"],
            [f'{pnl_color}⏳ Unrealized P&L{Fore.RESET}', f"{pnl_color}${pnl_data['unrealized_pnl']:,.2f}{Fore.RESET}"],
            [f'{pnl_color}💎 TOTAL P&L{Fore.RESET}', f"{pnl_color}${pnl_data['total_pnl']:,.2f}{Fore.RESET}"],
            [f'{roi_color}📈 ROI{Fore.RESET}', f"{roi_color}{pnl_data['roi']:+.2f}%{Fore.RESET}"]
        ]
        
        print(tabulate(account_data, tablefmt='simple'))
        
        # Trading statistics
        if self.trades:
            wins = [t for t in self.trades if t['pnl']>0]
            losses = [t for t in self.trades if t['pnl']<=0]
            win_rate = (len(wins)/len(self.trades)*100) if self.trades else 0
            
            print(f"\n{Fore.CYAN}{'─'*100}")
            print(f"{Fore.YELLOW}📊 TRADING STATISTICS")
            print(f"{Fore.CYAN}{'─'*100}")
            
            stats_data = [
                ['Total Trades', len(self.trades)],
                [f'{Fore.GREEN}Wins{Fore.RESET}', len(wins)],
                [f'{Fore.RED}Losses{Fore.RESET}', len(losses)],
                ['Win Rate', f"{win_rate:.1f}%"],
                ['Avg Win', f"${sum(t['pnl'] for t in wins)/len(wins):.2f}" if wins else "$0.00"],
                ['Avg Loss', f"${sum(t['pnl'] for t in losses)/len(losses):.2f}" if losses else "$0.00"]
            ]
            
            print(tabulate(stats_data, tablefmt='simple'))
        
        # Active positions with live updates
        if self.positions:
            print(f"\n{Fore.CYAN}{'─'*100}")
            print(f"{Fore.YELLOW}🔥 ACTIVE POSITIONS (LIVE)")
            print(f"{Fore.CYAN}{'─'*100}")
            
            positions_display = []
            for pos in self.positions:
                try:
                    current_price = self.exchange.fetch_ticker(pos['symbol'])['last']
                    unrealized_pnl = (current_price - pos['entry_price']) * pos['qty']
                    unrealized_pnl -= (pos['entry_price'] * pos['qty'] * 0.002)  # Fees
                    pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                    
                    # Distance to TP/SL
                    dist_to_tp = ((pos['target'] - current_price) / current_price) * 100
                    dist_to_sl = ((current_price - pos['stop']) / current_price) * 100
                    
                    duration = (datetime.now() - pos['entry_time']).seconds
                    
                    pnl_color = Fore.GREEN if unrealized_pnl >= 0 else Fore.RED
                    
                    positions_display.append([
                        pos['symbol'],
                        f"${pos['entry_price']:,.2f}",
                        f"${current_price:,.2f}",
                        f"{pnl_color}{pnl_pct:+.2f}%{Fore.RESET}",
                        f"{pnl_color}${unrealized_pnl:,.2f}{Fore.RESET}",
                        f"{dist_to_tp:+.2f}% to TP",
                        f"{dist_to_sl:+.2f}% to SL",
                        f"{duration}s"
                    ])
                except:
                    positions_display.append([
                        pos['symbol'],
                        f"${pos['entry_price']:,.2f}",
                        "Loading...",
                        "...",
                        "...",
                        "...",
                        "...",
                        "..."
                    ])
            
            print(tabulate(positions_display, 
                          headers=['Symbol', 'Entry', 'Current', 'Change', 'Unreal. P&L', 'To TP', 'To SL', 'Time'],
                          tablefmt='grid'))
        else:
            print(f"\n{Fore.YELLOW}No active positions")
        
        print(f"{Fore.CYAN}{'='*100}")
    
    def run(self):
        print(f"{Fore.CYAN}{'='*100}")
        print(f"{Fore.YELLOW}🤖 PAPER TRADING BOT - Gate.io")
        print(f"{Fore.WHITE}Starting Balance: ${self.initial:,.2f} (VIRTUAL)")
        print(f"{Fore.CYAN}{'='*100}\n")
        
        try:
            iteration = 0
            while True:
                iteration += 1
                print(f"\n{Fore.MAGENTA}[{datetime.now().strftime('%H:%M:%S')}] Update #{iteration}")
                
                # Check and close positions
                self.check_positions()
                
                # Look for new opportunities
                if len(self.positions) < 3 and len(self.trades) < 10:
                    for sym in self.symbols:
                        analysis = self.analyze(sym)
                        if analysis and analysis['buy']:
                            self.open_position(sym, analysis['price'])
                        time.sleep(1)
                
                # ALWAYS show dashboard with live P&L
                self.display_dashboard()
                
                print(f"\n{Fore.YELLOW}⏰ Next check in 30 seconds...")
                time.sleep(30)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}{'='*100}")
            print(f"{Fore.YELLOW}🛑 Bot stopped by user")
            print(f"{Fore.YELLOW}{'='*100}")
            self.display_dashboard()
            
            # Final summary
            pnl_data = self.get_current_pnl()
            print(f"\n{Fore.CYAN}📋 FINAL SUMMARY:")
            print(f"Total P&L: {Fore.GREEN if pnl_data['total_pnl']>=0 else Fore.RED}${pnl_data['total_pnl']:,.2f}")
            print(f"ROI: {Fore.GREEN if pnl_data['roi']>=0 else Fore.RED}{pnl_data['roi']:+.2f}%{Fore.RESET}")

if __name__ == "__main__":
    PaperBot().run()
