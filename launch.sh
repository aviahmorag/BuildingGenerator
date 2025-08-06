#!/bin/bash
# Building Generator Launcher

echo "🏢 Launching Building Generator..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if Flask is installed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing Flask..."
    pip3 install flask flask-cors
fi

# Check if Blender is installed
if ! command -v blender &> /dev/null; then
    echo "⚠️  Warning: Blender not found in PATH"
    echo "   The tool will open but won't be able to generate .blend files"
    echo "   Install Blender from: https://www.blender.org/download/"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Launch the server
cd "$(dirname "$0")"
python3 building_generator_server.py