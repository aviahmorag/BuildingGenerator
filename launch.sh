#!/bin/bash
# Building Generator Launcher

echo "Launching Building Generator..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed"
    exit 1
fi

# Check if Flask is installed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Flask..."
    pip3 install flask flask-cors
fi

# Launch the server
cd "$(dirname "$0")"
python3 building_generator_server.py
