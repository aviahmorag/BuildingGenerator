#!/bin/bash
# Building Generator - Mac Launcher
# Double-click this file to launch the tool

# Change to script directory
cd "$(dirname "$0")"

# Clear terminal and show header
clear
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              BUILDING GENERATOR TOOL                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed"
    echo "Please install Python 3 from: https://www.python.org/downloads/"
    echo ""
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Check/Install Flask
echo "Checking dependencies..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Flask (one-time setup)..."
    pip3 install --user flask flask-cors
    if [ $? -ne 0 ]; then
        echo "Failed to install Flask"
        echo "Try running: pip3 install flask flask-cors"
        echo ""
        echo "Press any key to exit..."
        read -n 1
        exit 1
    fi
fi

echo ""
echo "Starting Building Generator..."
echo "------------------------------------------------------------"
echo "The tool will open in your browser automatically."
echo "If Blender is not detected, use Settings to configure it."
echo "To stop: Close this terminal window or press Ctrl+C"
echo "------------------------------------------------------------"
echo ""

# Run the server
python3 building_generator_server.py

# Keep terminal open if script exits
echo ""
echo "Server stopped. Press any key to close..."
read -n 1
