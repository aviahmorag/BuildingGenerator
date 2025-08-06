#!/bin/bash
# Building Generator - Mac Launcher
# Double-click this file to launch the tool

# Change to script directory
cd "$(dirname "$0")"

# Clear terminal and show header
clear
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           🏢 BUILDING GENERATOR TOOL 🏢                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    echo "Please install Python 3 from: https://www.python.org/downloads/"
    echo ""
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Check/Install Flask
echo "🔍 Checking dependencies..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing Flask (one-time setup)..."
    pip3 install --user flask flask-cors
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Flask"
        echo "Try running: pip3 install flask flask-cors"
        echo ""
        echo "Press any key to exit..."
        read -n 1
        exit 1
    fi
fi

# Check Blender - look in common Mac locations
BLENDER_FOUND=false
if [ -f "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER_FOUND=true
    echo "✅ Blender found at /Applications/Blender.app"
elif [ -f "/Applications/Blender.app/Contents/MacOS/blender" ]; then
    BLENDER_FOUND=true
    echo "✅ Blender found at /Applications/Blender.app"
elif command -v blender &> /dev/null; then
    BLENDER_FOUND=true
    echo "✅ Blender found in PATH"
fi

if [ "$BLENDER_FOUND" = false ]; then
    echo ""
    echo "⚠️  WARNING: Blender not found"
    echo "   The tool will open but won't generate .blend files"
    echo "   "
    echo "   To fix this:"
    echo "   1. Download Blender from: https://www.blender.org/download/"
    echo "   2. Install it in the Applications folder"
    echo ""
    echo "Press Enter to continue anyway, or Ctrl+C to exit..."
    read
fi

echo ""
echo "✅ Starting Building Generator..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "The tool will open in your browser automatically"
echo "To stop: Close this terminal window or press Ctrl+C"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the server
python3 building_generator_server.py

# Keep terminal open if script exits
echo ""
echo "Server stopped. Press any key to close..."
read -n 1