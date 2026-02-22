#!/usr/bin/env python3
"""
CRYPTO TRADING TOOLS LAUNCHER
Easy menu to launch any of the three tools
"""

from colorama import Fore, Style, init
import subprocess
import sys
import os

init(autoreset=True)

def print_banner():
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════╗
║                    CRYPTO TRADING TOOLS SUITE                             ║
║                         Educational Edition                               ║
╚═══════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

def print_menu():
    menu = f"""
{Fore.YELLOW}Select a tool to launch:{Style.RESET_ALL}

{Fore.GREEN}[1] Market Data Analyzer{Style.RESET_ALL}
    └─ Read-only market analysis and signals
    └─ Best for: Learning and understanding indicators
    └─ Risk: None (no trading)
    └─ {Fore.CYAN}Perfect starting point for beginners{Style.RESET_ALL}

{Fore.YELLOW}[2] Paper Trading Simulator{Style.RESET_ALL}
    └─ Automated trading with virtual money
    └─ Best for: Testing strategies risk-free
    └─ Risk: None (virtual $10,000)
    └─ {Fore.CYAN}Test before you invest real money{Style.RESET_ALL}

{Fore.RED}[3] Manual Trading Assistant{Style.RESET_ALL}
    └─ Shows signals, you execute manually
    └─ Best for: Active trading with control
    └─ Risk: {Fore.RED}REAL MONEY if you connect API{Style.RESET_ALL}
    └─ {Fore.YELLOW}⚠️  Only use after extensive practice{Style.RESET_ALL}

{Fore.WHITE}[4] Exit{Style.RESET_ALL}

"""
    print(menu)

def launch_tool(tool_number):
    """Launch the selected tool"""
    tools = {
        '1': '1_market_analyzer.py',
        '2': '2_paper_trading.py',
        '3': '3_manual_assistant.py'
    }
    
    if tool_number in tools:
        script = tools[tool_number]
        
        if not os.path.exists(script):
            print(f"{Fore.RED}Error: {script} not found!")
            return
        
        print(f"\n{Fore.GREEN}Launching {script}...")
        print(f"{Fore.YELLOW}Press Ctrl+C to stop the tool and return to menu\n")
        
        try:
            subprocess.run([sys.executable, script])
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Tool stopped. Returning to menu...")
        except Exception as e:
            print(f"{Fore.RED}Error launching tool: {e}")

def show_warnings():
    """Show critical warnings before starting"""
    warnings = f"""
{Fore.RED}╔═══════════════════════════════════════════════════════════════════════════╗
║                          ⚠️  CRITICAL WARNINGS ⚠️                          ║
╚═══════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}1. These are EDUCATIONAL tools - not professional trading software
2. NO TOOL GUARANTEES PROFIT - most traders lose money
3. START WITH TOOL 1, then TOOL 2 - practice for weeks/months
4. ONLY use Tool 3 after consistent paper trading success
5. NEVER risk more than you can afford to lose completely{Style.RESET_ALL}

{Fore.GREEN}✓ Press ENTER to continue{Style.RESET_ALL}
"""
    print(warnings)
    try:
        input()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Goodbye!")
        sys.exit(0)

def main():
    os.system('clear')
    
    print_banner()
    show_warnings()
    
    while True:
        os.system('clear')
        print_banner()
        print_menu()
        
        try:
            choice = input(f"{Fore.CYAN}Enter your choice (1-4): {Style.RESET_ALL}").strip()
            
            if choice == '1':
                launch_tool('1')
            elif choice == '2':
                launch_tool('2')
            elif choice == '3':
                print(f"\n{Fore.YELLOW}{'='*80}")
                print(f"{Fore.RED}WARNING: Tool 3 can connect to real trading!")
                print(f"{'='*80}{Style.RESET_ALL}")
                confirm = input(f"\n{Fore.CYAN}Continue? (yes/no): {Style.RESET_ALL}").strip().lower()
                if confirm == 'yes':
                    launch_tool('3')
            elif choice == '4':
                print(f"\n{Fore.YELLOW}Thank you for using Crypto Trading Tools!{Style.RESET_ALL}")
                sys.exit(0)
            else:
                print(f"{Fore.RED}Invalid choice. Please enter 1-4.")
                input(f"{Fore.YELLOW}Press ENTER to continue...")
                
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()
