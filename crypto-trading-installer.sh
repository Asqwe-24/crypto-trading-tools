#!/bin/bash
# Crypto Trading Tools - One-Click Installer
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         CRYPTO TRADING TOOLS - AUTO INSTALLER                 ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "This installer is for Linux/Ubuntu only"
    exit 1
fi

echo -e "${YELLOW}[1/5] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    sudo apt update && sudo apt install python3 python3-pip python3-venv -y
fi
echo -e "${GREEN}✓ Python ready${NC}"

echo -e "${YELLOW}[2/5] Creating directory...${NC}"
PROJECT_DIR="$HOME/crypto-trading-tools"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo -e "${YELLOW}[3/5] Downloading tools...${NC}"
wget -q https://raw.githubusercontent.com/Asqwe-24/crypto-trading-tools/main/1_market_analyzer.py
wget -q https://raw.githubusercontent.com/Asqwe-24/crypto-trading-tools/main/2_paper_trading.py
wget -q https://raw.githubusercontent.com/Asqwe-24/crypto-trading-tools/main/3_manual_assistant.py
wget -q https://raw.githubusercontent.com/Asqwe-24/crypto-trading-tools/main/launch.py
chmod +x *.py

echo -e "${YELLOW}[4/5] Setting up environment...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q ccxt pandas colorama tabulate
echo -e "${GREEN}✓ Environment ready${NC}"

echo -e "${YELLOW}[5/5] Creating shortcuts...${NC}"
cat > "$HOME/Desktop/Crypto-Trading.desktop" << ENDDESKTOP
[Desktop Entry]
Type=Application
Name=Crypto Trading Tools
Exec=gnome-terminal -- bash -c "cd $PROJECT_DIR && source venv/bin/activate && python3 launch.py; exec bash"
Icon=utilities-terminal
Terminal=false
Categories=Finance;
ENDDESKTOP

chmod +x "$HOME/Desktop/Crypto-Trading.desktop"
echo 'alias crypto="cd ~/crypto-trading-tools && source venv/bin/activate && python3 launch.py"' >> "$HOME/.bashrc"

echo ""
echo -e "${GREEN}✅ INSTALLATION COMPLETE!${NC}"
echo ""
echo "Launch: Desktop icon OR type 'crypto' in terminal"
echo ""
