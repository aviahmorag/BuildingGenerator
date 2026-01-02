#!/usr/bin/env python3
"""
Building Generator - Local Tool
One-click launcher that opens the web interface and handles Blender generation
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import subprocess
import tempfile
import base64
from pathlib import Path
import shutil
import webbrowser
import threading
import time
import sys
import json

app = Flask(__name__)
CORS(app)

# Config file in same directory as script
CONFIG_FILE = Path(__file__).parent / 'config.json'

def load_config():
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def find_blender():
    """Find Blender executable on the system."""
    # First check config
    config = load_config()
    if config.get('blender_path') and os.path.exists(config['blender_path']):
        return config['blender_path']

    # Common Blender installation paths
    possible_paths = [
        # macOS
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/Applications/Blender.app/Contents/MacOS/blender",
        # Linux
        "/usr/bin/blender",
        "/usr/local/bin/blender",
        "/snap/bin/blender",
        # Windows
        "C:\\Program Files\\Blender Foundation\\Blender\\blender.exe",
        "C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe",
        "C:\\Program Files\\Blender Foundation\\Blender 4.1\\blender.exe",
        "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
        "C:\\Program Files\\Blender Foundation\\Blender 3.6\\blender.exe",
    ]

    # Check if blender is in PATH
    try:
        if sys.platform == "win32":
            result = subprocess.run(["where", "blender"], capture_output=True, text=True)
        else:
            result = subprocess.run(["which", "blender"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass

    # Check common paths
    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None

def get_blender_version(blender_path):
    """Get Blender version string."""
    try:
        result = subprocess.run(
            [blender_path, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.split('\n')[0]
    except:
        pass
    return None

# Serve the HTML file
@app.route('/')
def index():
    html_path = Path(__file__).parent / 'building-generator.html'
    with open(html_path, 'r') as f:
        content = f.read()
        # Modify the HTML to use our local server endpoint
        content = content.replace(
            'document.getElementById(\'outputLog\').textContent = logText;',
            '''
            // Call our local server to generate the file
            fetch('http://localhost:5555/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    image: this.imageDataUrl,
                    width: width,
                    depth: depth, 
                    output: outputFileName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('outputLog').textContent = data.log || 'Building generated successfully!';
                    this.showGenerateStatus('✅ Building generated! File saved to: ' + data.output_path, 'success');
                    
                    // Trigger download if we have the file data
                    if (data.blend_data) {
                        const link = document.createElement('a');
                        link.download = data.filename;
                        link.href = 'data:application/octet-stream;base64,' + data.blend_data;
                        link.click();
                    }
                } else {
                    document.getElementById('outputLog').textContent = 'Error: ' + data.error;
                    this.showGenerateStatus('Error generating building: ' + data.error, 'error');
                }
            })
            .catch(error => {
                document.getElementById('outputLog').textContent = 'Error: ' + error.message;
                this.showGenerateStatus('Error connecting to generator: ' + error.message, 'error');
            });
            '''
        )
        return content

@app.route('/generate', methods=['POST'])
def generate_building():
    try:
        # Get parameters from request
        data = request.json
        image_data = data.get('image')
        width = data.get('width', 12)
        depth = data.get('depth', 12)
        output_name = data.get('output', 'building.blend')
        original_filename = data.get('originalFileName', 'facade.png')
        
        # Ensure output name has .blend extension
        if not output_name.endswith('.blend'):
            output_name += '.blend'
        
        # Use Downloads folder for output
        downloads_dir = Path.home() / 'Downloads'
        output_path = downloads_dir / output_name
        
        # Create temp directory for image
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save the image from base64 - use original filename to preserve name for Blender object
            image_path = os.path.join(temp_dir, original_filename if original_filename else 'facade.png')
            
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode and save image
            with open(image_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            
            # Run the createBuilding.py script
            script_path = Path(__file__).parent / 'createBuilding.py'
            
            # Check if script exists
            if not script_path.exists():
                return jsonify({
                    'success': False,
                    'error': f'createBuilding.py not found at {script_path}'
                }), 500
            
            # Find Blender path
            blender_path = find_blender()
            if not blender_path:
                return jsonify({
                    'success': False,
                    'error': 'Blender not found. Please configure the Blender path in Settings.'
                }), 500

            cmd = [
                sys.executable, str(script_path),
                image_path,
                '--width', str(width),
                '--depth', str(depth),
                '--output', str(output_path),
                '--blender-path', blender_path
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or 'Failed to generate building'
                print(f"Error: {error_msg}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }), 500
            
            # Check if the blend file was created
            if not output_path.exists():
                return jsonify({
                    'success': False,
                    'error': f'Blend file was not created at {output_path}'
                }), 500
            
            # Read the blend file for download (optional - for smaller files)
            try:
                if output_path.stat().st_size < 10 * 1024 * 1024:  # Only if < 10MB
                    with open(output_path, 'rb') as f:
                        blend_data = base64.b64encode(f.read()).decode('utf-8')
                else:
                    blend_data = None
            except:
                blend_data = None
            
            return jsonify({
                'success': True,
                'blend_data': blend_data,
                'filename': output_name,
                'output_path': str(output_path),
                'log': f"✅ Building generated successfully!\n📁 Saved to: {output_path}\n\n{result.stdout}"
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Generation timed out (>30 seconds)'
        }), 500
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Exception: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    # Check if Blender is available using our find function
    blender_path = find_blender()
    blender_available = blender_path is not None
    blender_version = get_blender_version(blender_path) if blender_path else 'Not found'

    # Check if createBuilding.py exists
    script_exists = (Path(__file__).parent / 'createBuilding.py').exists()

    return jsonify({
        'status': 'running',
        'blender_available': blender_available,
        'blender_path': blender_path,
        'blender_version': blender_version,
        'script_exists': script_exists
    })

@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    config = load_config()
    blender_path = find_blender()
    blender_version = get_blender_version(blender_path) if blender_path else None

    return jsonify({
        'blender_path': config.get('blender_path', ''),
        'detected_blender_path': blender_path,
        'blender_version': blender_version,
        'blender_available': blender_path is not None
    })

@app.route('/config', methods=['POST'])
def set_config():
    """Save configuration."""
    data = request.json
    config = load_config()

    if 'blender_path' in data:
        path = data['blender_path']
        # Validate the path
        if path and not os.path.exists(path):
            return jsonify({'success': False, 'error': 'Path does not exist'}), 400
        config['blender_path'] = path

    save_config(config)

    # Return updated status
    blender_path = find_blender()
    blender_version = get_blender_version(blender_path) if blender_path else None

    return jsonify({
        'success': True,
        'blender_path': config.get('blender_path', ''),
        'detected_blender_path': blender_path,
        'blender_version': blender_version,
        'blender_available': blender_path is not None
    })

@app.route('/browse-blender', methods=['POST'])
def browse_blender():
    """Open native file dialog to select Blender executable."""
    try:
        filepath = None

        if sys.platform == 'darwin':
            # macOS - use AppleScript for native dialog
            script = '''
            tell application "System Events"
                activate
                set blenderApp to choose file with prompt "Select Blender Application" of type {"app", "public.unix-executable"} default location "/Applications"
                return POSIX path of blenderApp
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0 and result.stdout.strip():
                filepath = result.stdout.strip()
            elif 'User canceled' in result.stderr:
                return jsonify({'success': False, 'cancelled': True})
            else:
                return jsonify({
                    'success': False,
                    'error': result.stderr.strip() or 'Dialog was cancelled'
                }), 400

        elif sys.platform == 'win32':
            # Windows - use PowerShell for native dialog
            script = '''
            Add-Type -AssemblyName System.Windows.Forms
            $dialog = New-Object System.Windows.Forms.OpenFileDialog
            $dialog.Title = "Select Blender Application"
            $dialog.Filter = "Blender|blender.exe|All files|*.*"
            $dialog.InitialDirectory = "C:\\Program Files\\Blender Foundation"
            if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
                Write-Output $dialog.FileName
            }
            '''
            result = subprocess.run(
                ['powershell', '-Command', script],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0 and result.stdout.strip():
                filepath = result.stdout.strip()
            else:
                return jsonify({'success': False, 'cancelled': True})

        else:
            # Linux - try zenity, kdialog, or fallback
            for cmd in [
                ['zenity', '--file-selection', '--title=Select Blender', '--file-filter=*.* | *'],
                ['kdialog', '--getopenfilename', '/usr/bin', '*']
            ]:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0 and result.stdout.strip():
                        filepath = result.stdout.strip()
                        break
                except FileNotFoundError:
                    continue

            if not filepath:
                return jsonify({
                    'success': False,
                    'error': 'No file dialog available. Please enter the path manually.'
                }), 500

        if not filepath:
            return jsonify({'success': False, 'cancelled': True})

        # On macOS, if user selected .app, get the actual executable inside
        if sys.platform == 'darwin' and filepath.endswith('.app'):
            executable = os.path.join(filepath, 'Contents', 'MacOS', 'Blender')
            if not os.path.exists(executable):
                executable = os.path.join(filepath, 'Contents', 'MacOS', 'blender')
            if os.path.exists(executable):
                filepath = executable
            else:
                return jsonify({
                    'success': False,
                    'error': 'Could not find Blender executable inside the app bundle'
                }), 400

        # Validate it's actually Blender
        version = get_blender_version(filepath)
        if not version:
            return jsonify({
                'success': False,
                'error': 'Selected file does not appear to be a valid Blender executable'
            }), 400

        # Save to config
        config = load_config()
        config['blender_path'] = filepath
        save_config(config)

        return jsonify({
            'success': True,
            'blender_path': filepath,
            'blender_version': version
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Dialog timed out'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def open_browser():
    """Open the browser after a short delay"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5555')

if __name__ == '__main__':
    print("=" * 60)
    print("🏢 Building Generator")
    print("=" * 60)
    print("Starting local server...")
    print("-" * 60)
    
    # Check requirements
    script_path = Path(__file__).parent / 'createBuilding.py'
    if not script_path.exists():
        print("⚠️  WARNING: createBuilding.py not found!")
        print(f"   Expected at: {script_path}")
    
    # Check for Blender
    blender_path = find_blender()
    if blender_path:
        version = get_blender_version(blender_path)
        print(f"Blender found: {blender_path}")
        if version:
            print(f"  Version: {version}")
    else:
        print("WARNING: Blender not found")
        print("  Configure it in Settings or install from https://www.blender.org/download/")
    
    print("-" * 60)
    print("Opening browser at: http://localhost:5555")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the server
    app.run(debug=False, port=5555, host='127.0.0.1')