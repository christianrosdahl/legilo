#!/bin/bash

# Define the virtual environment directory
VENV_DIR="venv"

# Check if the virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found, creating one..."
    python3 -m venv $VENV_DIR
fi

# Activate the virtual environment
source $VENV_DIR/bin/activate

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install --upgrade pip --quiet
    pip install wheel --quiet
    pip install -r requirements.txt --quiet
fi

# Run Legilo
python main.py

# Deactivate the virtual environment
deactivate