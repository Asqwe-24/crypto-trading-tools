#!/bin/bash
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         CRYPTO TRADING TOOLS - QUICK LAUNCHER                 ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${YELLOW}Installing packages (this may take a minute)...${NC}"
    pip install --upgrade pip -q
    pip install ccxt pandas colorama tabulate -q
    echo -e "${GREEN}✓ Setup complete!${NC}"
else
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated!${NC}"
fi

echo ""
if [ ! -f "launch.py" ]; then
    echo -e "${RED}Error: Python files not found.${NC}"
    echo "Please download the files from Claude and extract them here."
    exit 1
fi

chmod +x *.py 2>/dev/null
python3 launch.py
