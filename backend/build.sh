#!/bin/bash
# Install Python 3.11 if not available
if ! command -v python3.11 &> /dev/null; then
    apt-get update && apt-get install -y python3.11 python3.11-venv python3.11-dev
fi

# Create virtual environment with Python 3.11
python3.11 -m venv /opt/render/project/src/.venv
source /opt/render/project/src/.venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
