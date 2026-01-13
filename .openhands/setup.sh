#!/usr/bin/env bash
set -e

echo "🔧 OpenHands bootstrap initializing The Lathe..."

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

mkdir -p data

echo "✅ Bootstrap environment ready"