#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
mkdir -p logs orders backup temp
echo "🚀 Starting WEB NST Server..."
python run.py
