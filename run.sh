#!/bin/bash

# Get the directory where this script is located
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

# Create venv if missing
[ ! -d "venv" ] && python3 -m venv venv

# Activate and install deps
source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

# Start server
python main.py
