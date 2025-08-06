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

app = Flask(__name__)
CORS(app)

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
        
        # Ensure output name has .blend extension
        if not output_name.endswith('.blend'):
            output_name += '.blend'
        
        # Use Downloads folder for output
        downloads_dir = Path.home() / 'Downloads'
        output_path = downloads_dir / output_name
        
        # Create temp directory for image
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save the image from base64
            image_path = os.path.join(temp_dir, 'facade.png')
            
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
            
            cmd = [
                sys.executable, str(script_path),
                image_path,
                '--width', str(width),
                '--depth', str(depth),
                '--output', str(output_path)
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
                return jsonify({
                    'success': False,
                    'error': error_msg
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
    # Check if Blender is available - check common paths
    blender_paths = [
        '/Applications/Blender.app/Contents/MacOS/Blender',
        '/Applications/Blender.app/Contents/MacOS/blender',
        'blender'
    ]
    
    blender_available = False
    blender_version = 'Not found'
    
    for blender_cmd in blender_paths:
        try:
            result = subprocess.run(
                [blender_cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                blender_available = True
                blender_version = result.stdout.split('\n')[0]
                break
        except:
            continue
    
    # Check if createBuilding.py exists
    script_exists = (Path(__file__).parent / 'createBuilding.py').exists()
    
    return jsonify({
        'status': 'running',
        'blender_available': blender_available,
        'blender_version': blender_version,
        'script_exists': script_exists
    })

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
    
    # Check for Blender in common locations
    blender_found = False
    blender_paths = [
        '/Applications/Blender.app/Contents/MacOS/Blender',
        '/Applications/Blender.app/Contents/MacOS/blender',
        'blender'
    ]
    
    for blender_cmd in blender_paths:
        try:
            result = subprocess.run([blender_cmd, '--version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                print(f"✅ Blender found: {blender_cmd}")
                blender_found = True
                break
        except:
            continue
    
    if not blender_found:
        print("⚠️  WARNING: Blender not found")
        print("   Please install Blender from https://www.blender.org/download/")
    
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