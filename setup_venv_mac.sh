#!/bin/bash
set -e
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo
echo "Environment ready. Activate it later with: source .venv/bin/activate"
