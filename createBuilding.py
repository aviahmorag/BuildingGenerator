#!/usr/bin/env python3
"""
Building Generator for Blender
(C) 2025 Aviah Morag
Contact: pashoshington@gmail.com

Command-line tool to create Blender files with buildings from facade images.

Usage:
    python createBuilding.py path/to/image.jpg
    python createBuilding.py path/to/image.jpg --width 15 --depth 12
    python createBuilding.py path/to/folder/ --batch
"""

import sys
import os
import argparse
import subprocess
import tempfile
from pathlib import Path

# Blender Python script template
BLENDER_SCRIPT_TEMPLATE = '''
import bpy
import os
from mathutils import Vector

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Remove default camera and light if they exist
for obj in bpy.data.objects:
    bpy.data.objects.remove(obj, do_unlink=True)

def create_building_from_facade(image_path, building_width={width}, building_depth={depth}):
    """Create a building with a facade image applied to all 4 sides."""
    
    # Load the image
    image_name = os.path.basename(image_path)
    img = bpy.data.images.load(image_path)
    # Pack the image into the blend file to remove external dependency
    img.pack()
    
    # Get the output filename (without .blend extension) for naming
    output_name = os.path.splitext(os.path.basename("{output_path}"))[0]
    
    # Get image dimensions to calculate aspect ratio
    img_width = img.size[0]
    img_height = img.size[1]
    aspect_ratio = img_width / img_height
    
    # Calculate building height based on width and image aspect ratio
    building_height = building_width / aspect_ratio
    
    # Print the actual dimensions
    print(f"Dimensions: width={{building_width:.1f}}m, height={{building_height:.1f}}m")
    
    # Create a collection for the building first
    collection_name = "Building_" + output_name
    building_collection = bpy.data.collections.new(name=collection_name)
    bpy.context.scene.collection.children.link(building_collection)
    
    # Set the new collection as active
    layer_collection = bpy.context.view_layer.layer_collection.children[building_collection.name]
    bpy.context.view_layer.active_layer_collection = layer_collection
    
    # Create the building mesh in the new collection
    bpy.ops.mesh.primitive_cube_add(
        size=2,
        location=(0, 0, 0)  # Create at origin first
    )
    
    building = bpy.context.active_object
    # Use the full name for the mesh object since it's the asset
    building.name = "Building_" + output_name
    
    # Scale the cube to building dimensions
    building.scale = (building_width/2, building_depth/2, building_height/2)
    bpy.ops.object.transform_apply(scale=True)
    
    # Now move the building so its bottom sits at Z=0
    building.location.z = building_height/2
    
    # Create facade material (for sides)
    facade_mat = bpy.data.materials.new(name="Facade_Material")
    facade_mat.use_nodes = True
    nodes = facade_mat.node_tree.nodes
    links = facade_mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Add nodes for facade material
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)
    
    bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf_node.location = (200, 0)
    
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.location = (0, 0)
    tex_node.image = img
    
    # Create UV mapping node
    uv_map_node = nodes.new(type='ShaderNodeUVMap')
    uv_map_node.location = (-400, 0)
    
    # Add Mapping node to rotate texture
    mapping_node = nodes.new(type='ShaderNodeMapping')
    mapping_node.location = (-200, 0)
    # Rotate 90 degrees (in radians: pi/2 = 1.5708)
    mapping_node.inputs['Rotation'].default_value[2] = 1.5708
    
    # Connect nodes
    links.new(uv_map_node.outputs['UV'], mapping_node.inputs['Vector'])
    links.new(mapping_node.outputs['Vector'], tex_node.inputs['Vector'])
    links.new(tex_node.outputs['Color'], bsdf_node.inputs['Base Color'])
    links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
    
    # Create roof/floor material (solid color)
    roof_mat = bpy.data.materials.new(name="Roof_Floor_Material")
    roof_mat.use_nodes = True
    roof_nodes = roof_mat.node_tree.nodes
    roof_links = roof_mat.node_tree.links
    
    # Clear and setup simple material
    roof_nodes.clear()
    roof_output = roof_nodes.new(type='ShaderNodeOutputMaterial')
    roof_output.location = (400, 0)
    
    roof_bsdf = roof_nodes.new(type='ShaderNodeBsdfPrincipled')
    roof_bsdf.location = (200, 0)
    # Set a neutral gray color
    roof_bsdf.inputs['Base Color'].default_value = (0.3, 0.3, 0.3, 1.0)
    
    roof_links.new(roof_bsdf.outputs['BSDF'], roof_output.inputs['Surface'])
    
    # Add both materials to the building
    building.data.materials.append(facade_mat)
    building.data.materials.append(roof_mat)
    
    # UV Unwrap for proper texture mapping
    bpy.context.view_layer.objects.active = building
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    
    # Smart UV project
    bpy.ops.uv.smart_project(
        angle_limit=66,
        island_margin=0.01,
        area_weight=0.0,
        correct_aspect=True,
        scale_to_bounds=True
    )
    
    # Mark seams for better UV unwrapping
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Select top and bottom faces
    mesh = building.data
    for i, face in enumerate(mesh.polygons):
        face_normal = face.normal
        if abs(face_normal.z) > 0.9:
            face.select = True
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.mark_seam()
    
    # Proper UV unwrap
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
    
    # Scale UVs for side faces
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Select only side faces
    for i, face in enumerate(mesh.polygons):
        face_normal = face.normal
        if abs(face_normal.z) < 0.1:
            face.select = True
    
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Switch to UV editor to reset UVs
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            old_type = area.type
            area.type = 'IMAGE_EDITOR'
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.reset()
            area.type = old_type
            break
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Assign materials to faces based on their orientation
    mesh = building.data
    for face in mesh.polygons:
        face_normal = face.normal
        # If face is horizontal (top or bottom), use roof material (index 1)
        if abs(face_normal.z) > 0.9:
            face.material_index = 1
        # If face is vertical (side), use facade material (index 0)
        else:
            face.material_index = 0
    
    # Get the collection reference and mark it as an asset
    collection_name = "Building_" + output_name
    building_collection = bpy.data.collections.get(collection_name)
    
    if building_collection:
        # Clear any existing asset data first
        if hasattr(building_collection, 'asset_data'):
            building_collection.asset_clear()
        
        # Mark the collection as an asset
        building_collection.asset_mark()
        
        # Force preview generation - this is the key!
        building_collection.asset_generate_preview()
    
    return building

# Create the building
building = create_building_from_facade("{image_path}", {width}, {depth})

# Remove the default empty collection if it exists and is empty
default_collection = bpy.context.scene.collection.children.get("Collection")
if default_collection and len(default_collection.objects) == 0:
    bpy.context.scene.collection.children.unlink(default_collection)

# Set viewport shading to Material Preview for better visualization
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
                break

# Save the file
output_path = "{output_path}"
bpy.ops.wm.save_as_mainfile(filepath=output_path)
print(f"Saved: {{output_path}}")
'''

def find_blender():
    """Find Blender executable on the system."""
    
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
        "C:\\Program Files\\Blender Foundation\\Blender 3.6\\blender.exe",
    ]
    
    # Check if blender is in PATH
    try:
        result = subprocess.run(["which", "blender"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    # Check common paths
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Try to find using 'where' on Windows
    if sys.platform == "win32":
        try:
            result = subprocess.run(["where", "blender"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
    
    return None

def create_building(image_path, output_path=None, width=12, depth=12, blender_path=None):
    """
    Create a Blender file with a building from a facade image.
    
    Args:
        image_path: Path to the facade image
        output_path: Output .blend file path (optional)
        width: Building width in meters
        depth: Building depth in meters
        blender_path: Path to Blender executable (optional)
    """
    
    # Resolve paths
    image_path = os.path.abspath(image_path)
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return False
    
    # Generate output path if not provided
    if output_path is None:
        image_name = Path(image_path).stem
        output_dir = Path(image_path).parent
        output_path = output_dir / f"{image_name}.blend"
    else:
        output_path = Path(output_path)
    
    output_path = str(output_path.absolute())
    
    # Find Blender
    if blender_path is None:
        blender_path = find_blender()
        if blender_path is None:
            print("Error: Blender not found. Please install Blender or specify path with --blender-path")
            print("Download from: https://www.blender.org/download/")
            return False
    
    # Create temporary Python script for Blender
    script_content = BLENDER_SCRIPT_TEMPLATE.format(
        image_path=image_path.replace('\\', '\\\\'),
        output_path=output_path.replace('\\', '\\\\'),
        width=width,
        depth=depth
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        temp_script = f.name
    
    try:
        # Run Blender in background mode
        cmd = [
            blender_path,
            '--background',
            '--python', temp_script
        ]
        
        print(f"Creating building from: {os.path.basename(image_path)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Show the dimension output from Blender
            if result.stdout:
                # Extract and show the dimension line
                for line in result.stdout.split('\n'):
                    if 'Dimensions:' in line:
                        print(line)
            print(f"✓ Successfully created: {output_path}")
            return True
        else:
            print(f"Error running Blender:")
            print(result.stderr)
            return False
            
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_script)
        except:
            pass

def batch_process(folder_path, width=12, depth=12, blender_path=None):
    """Process all images in a folder."""
    
    folder_path = Path(folder_path)
    if not folder_path.is_dir():
        print(f"Error: Not a directory: {folder_path}")
        return
    
    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
    image_files = [f for f in folder_path.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"No image files found in: {folder_path}")
        return
    
    print(f"Found {len(image_files)} images to process")
    print("-" * 40)
    
    success_count = 0
    for i, image_file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] Processing: {image_file.name}")
        if create_building(str(image_file), None, width, depth, blender_path):
            success_count += 1
    
    print("\n" + "=" * 40)
    print(f"Batch processing complete: {success_count}/{len(image_files)} successful")

def main():
    parser = argparse.ArgumentParser(
        description='Create Blender buildings from facade images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s photo.jpg
  %(prog)s photo.jpg --width 15 --depth 12
  %(prog)s photo.jpg --output building.blend
  %(prog)s /path/to/photos/ --batch
  %(prog)s photo.jpg --blender-path /custom/path/to/blender
        '''
    )
    
    parser.add_argument('input', help='Path to image file or folder (with --batch)')
    parser.add_argument('--output', '-o', help='Output .blend file path')
    parser.add_argument('--width', '-w', type=float, default=12, 
                        help='Building width in meters (default: 12)')
    parser.add_argument('--depth', '-d', type=float, default=12,
                        help='Building depth in meters (default: 12)')
    parser.add_argument('--batch', '-b', action='store_true',
                        help='Process all images in a folder')
    parser.add_argument('--blender-path', help='Path to Blender executable')
    
    args = parser.parse_args()
    
    if args.batch:
        batch_process(args.input, args.width, args.depth, args.blender_path)
    else:
        success = create_building(
            args.input, 
            args.output, 
            args.width, 
            args.depth,
            args.blender_path
        )
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()