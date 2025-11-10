"""
BlenderBIM IFC Generator Script
Runs inside Blender to generate professional IFC files
"""
import bpy
import sys
import json
import argparse
from pathlib import Path

print("Starting BlenderBIM IFC Generator")
print(f"Blender version: {bpy.app.version_string}")

# Enable BlenderBIM addon
import addon_utils
addon_result = addon_utils.enable("blenderbim")
if not addon_result:
    print("ERROR: Failed to enable BlenderBIM addon")
    sys.exit(1)
print("BlenderBIM addon enabled successfully")

import blenderbim.tool as tool
from blenderbim.bim.ifc import IfcStore

def create_project(project_name: str):
    """Initialize a new IFC project with proper structure"""
    # Clear existing scene
    bpy.ops.wm.read_homefile(use_empty=True)
    
    # Create new IFC project
    bpy.ops.bim.create_project()
    
    # Set project name
    ifc_file = IfcStore.get_file()
    project = ifc_file.by_type("IfcProject")[0]
    project.Name = project_name
    
    # Get or create building structure
    site = ifc_file.by_type("IfcSite")[0] if ifc_file.by_type("IfcSite") else None
    building = ifc_file.by_type("IfcBuilding")[0] if ifc_file.by_type("IfcBuilding") else None
    storey = ifc_file.by_type("IfcBuildingStorey")[0] if ifc_file.by_type("IfcBuildingStorey") else None
    
    return ifc_file, storey

def create_wall(params: dict):
    """Create a wall using BlenderBIM"""
    # Auto-scale if values are already in meters (< 10 suggests meters, not mm)
    length = params.get('length', 5000)
    height = params.get('height', 3000)
    thickness = params.get('thickness', 200)
    if length < 10 or height < 10 or thickness < 1:
        print(f"⚠️ Auto-scaling wall (detected meter values instead of mm)")
        length *= 1000
        height *= 1000
        thickness *= 1000
    
    length = length / 1000.0  # Convert to meters
    height = height / 1000.0
    thickness = thickness / 1000.0
    x = params.get('x', 0) / 1000.0
    y = params.get('y', 0) / 1000.0
    z = params.get('z', 0) / 1000.0
    
    # Create wall
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y, z + height/2))
    wall_obj = bpy.context.active_object
    wall_obj.scale = (length, thickness, height)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcWall", predefined_type="SOLIDWALL", userdefined_type="")
    
    return wall_obj

def create_slab(params: dict):
    """Create a slab/floor using BlenderBIM"""
    length = params.get('length', 5000)
    width = params.get('width', 5000)
    thickness = params.get('thickness', 200)
    if length < 10 or width < 10 or thickness < 1:
        print(f"⚠️ Auto-scaling slab (detected meter values)")
        length *= 1000
        width *= 1000
        thickness *= 1000
    
    length = length / 1000.0
    width = width / 1000.0
    thickness = thickness / 1000.0
    x = params.get('x', 0) / 1000.0
    y = params.get('y', 0) / 1000.0
    z = params.get('z', 0) / 1000.0
    
    # Create slab
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y + width/2, z + thickness/2))
    slab_obj = bpy.context.active_object
    slab_obj.scale = (length, width, thickness)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcSlab", predefined_type="FLOOR", userdefined_type="")
    
    return slab_obj

def create_door(params: dict):
    """Create a door using BlenderBIM"""
    width = params.get('width', 900)
    height = params.get('height', 2100)
    thickness = params.get('thickness', 50)
    if width < 10 or height < 10:
        print(f"⚠️ Auto-scaling door (detected meter values)")
        width *= 1000
        height *= 1000
        thickness *= 1000
    
    width = width / 1000.0
    height = height / 1000.0
    thickness = thickness / 1000.0
    x = params.get('x', 0) / 1000.0
    y = params.get('y', 0) / 1000.0
    z = params.get('z', 0) / 1000.0
    
    # Create door panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y, z + height/2))
    door_obj = bpy.context.active_object
    door_obj.scale = (width, thickness, height)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcDoor", predefined_type="DOOR", userdefined_type="")
    
    return door_obj

def create_window(params: dict):
    """Create a window using BlenderBIM"""
    width = params.get('width', 1200)
    height = params.get('height', 1200)
    thickness = params.get('thickness', 100)
    if width < 10 or height < 10:
        print(f"⚠️ Auto-scaling window (detected meter values)")
        width *= 1000
        height *= 1000
        thickness *= 1000
    
    width = width / 1000.0
    height = height / 1000.0
    thickness = thickness / 1000.0
    x = params.get('x', 0) / 1000.0
    y = params.get('y', 0) / 1000.0
    z = params.get('z', 1000) / 1000.0
    
    # Create window frame
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y, z + height/2))
    window_obj = bpy.context.active_object
    window_obj.scale = (width, thickness, height)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcWindow", predefined_type="WINDOW", userdefined_type="")
    
    return window_obj

def create_column(params: dict):
    """Create a column using BlenderBIM"""
    width = params.get('width', 300)
    depth = params.get('depth', 300)
    height = params.get('height', 3000)
    if width < 10 or depth < 10 or height < 10:
        print(f"⚠️ Auto-scaling column (detected meter values)")
        width *= 1000
        depth *= 1000
        height *= 1000
    
    width = width / 1000.0
    depth = depth / 1000.0
    height = height / 1000.0
    x = params.get('x', 0) / 1000.0
    y = params.get('y', 0) / 1000.0
    z = params.get('z', 0) / 1000.0
    
    # Create column
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z + height/2))
    column_obj = bpy.context.active_object
    column_obj.scale = (width, depth, height)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcColumn", predefined_type="COLUMN", userdefined_type="")
    
    return column_obj

def create_beam(params: dict):
    """Create a beam using BlenderBIM"""
    length = params.get('length', 5000)
    width = params.get('width', 300)
    height = params.get('height', 400)
    if length < 10 or width < 10 or height < 10:
        print(f"⚠️ Auto-scaling beam (detected meter values)")
        length *= 1000
        width *= 1000
        height *= 1000
    
    length = length / 1000.0
    width = width / 1000.0
    height = height / 1000.0
    x = params.get('x', 0) / 1000.0
    y = params.get('y', 0) / 1000.0
    z = params.get('z', 3000) / 1000.0
    
    print(f"Creating beam: L={length}m, W={width}m, H={height}m at ({x}, {y}, {z})")
    
    # Create beam geometry
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y, z))
    beam_obj = bpy.context.active_object
    beam_obj.scale = (length, width, height)
    beam_obj.name = params.get('name', 'Beam')
    
    print(f"Beam geometry created: {beam_obj.name}")
    
    # Ensure object is selected and active
    bpy.ops.object.select_all(action='DESELECT')
    beam_obj.select_set(True)
    bpy.context.view_layer.objects.active = beam_obj
    
    # Assign IFC class
    try:
        bpy.ops.bim.assign_class(ifc_class="IfcBeam", predefined_type="BEAM", userdefined_type="")
        print(f"IFC class assigned to {beam_obj.name}")
    except Exception as e:
        print(f"ERROR assigning IFC class: {e}")
        raise
    
    return beam_obj

def create_roof(params: dict):
    """Create a roof using BlenderBIM"""
    length = params.get('length', 10000)
    width = params.get('width', 10000)
    thickness = params.get('thickness', 200)
    if length < 10 or width < 10 or thickness < 1:
        print(f"⚠️ Auto-scaling roof (detected meter values)")
        length *= 1000
        width *= 1000
        thickness *= 1000
    
    length = length / 1000.0
    width = width / 1000.0
    thickness = thickness / 1000.0
    x = params.get('x', 0) / 1000.0
    y = params.get('y', 0) / 1000.0
    z = params.get('z', 6000) / 1000.0
    
    # Create roof slab
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y + width/2, z))
    roof_obj = bpy.context.active_object
    roof_obj.scale = (length, width, thickness)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcRoof", predefined_type="FLAT_ROOF", userdefined_type="")
    
    return roof_obj

def create_stairs(params: dict):
    """Create stairs using BlenderBIM"""
    width = params.get('width', 1200)
    length = params.get('length', 3000)
    height = params.get('height', 3000)
    if width < 10 or length < 10 or height < 10:
        print(f"⚠️ Auto-scaling stairs (detected meter values)")
        width *= 1000
        length *= 1000
        height *= 1000
    
    width = width / 1000.0
    length = length / 1000.0
    height = height / 1000.0
    steps = params.get('steps', 15)
    x = params.get('x', 0) / 1000.0
    y = params.get('y', 0) / 1000.0
    z = params.get('z', 0) / 1000.0
    
    step_height = height / steps
    step_depth = length / steps
    
    # Create stairs as a series of steps
    for i in range(steps):
        step_z = z + i * step_height
        step_y = y + i * step_depth
        
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(x + width/2, step_y + step_depth/2, step_z + step_height/2)
        )
        step_obj = bpy.context.active_object
        step_obj.scale = (width, step_depth, step_height)
        
        if i == 0:
            # Only assign IFC class to the first step (representing the whole stair)
            bpy.ops.bim.assign_class(ifc_class="IfcStair", predefined_type="STRAIGHT_RUN_STAIR", userdefined_type="")
    
    return step_obj

# Handler mapping
ELEMENT_HANDLERS = {
    'create_wall': create_wall,
    'create_slab': create_slab,
    'create_door': create_door,
    'create_window': create_window,
    'create_column': create_column,
    'create_beam': create_beam,
    'create_roof': create_roof,
    'create_stairs': create_stairs,
}

def main():
    """Main execution function"""
    # Parse command line arguments (after --)
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        print("Error: No arguments provided")
        sys.exit(1)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--output", required=True, help="Output IFC file")
    args = parser.parse_args(argv)
    
    # Load input data
    with open(args.input, 'r') as f:
        data = json.load(f)
    
    project_name = data.get('project_name', 'AI Generated BIM Model')
    tool_calls = data.get('tool_calls', [])
    
    print(f"Creating IFC project: {project_name}")
    print(f"Processing {len(tool_calls)} tool calls")
    
    # Create project
    ifc_file, storey = create_project(project_name)
    
    # Process tool calls
    for i, call in enumerate(tool_calls):
        function = call.get('function')
        params = call.get('params', {})
        
        print(f"Processing {i+1}/{len(tool_calls)}: {function}")
        
        if function in ELEMENT_HANDLERS:
            try:
                ELEMENT_HANDLERS[function](params)
            except Exception as e:
                print(f"Warning: Failed to create {function}: {e}")
        else:
            print(f"Warning: Unknown function {function}")
    
    # Verify IFC file exists
    ifc_file = IfcStore.get_file()
    if not ifc_file:
        print("ERROR: No IFC file in store")
        sys.exit(1)
    
    elements = ifc_file.by_type("IfcProduct")
    print(f"Total IFC elements created: {len(elements)}")
    
    if len(elements) == 0:
        print("WARNING: No IFC elements created")
    
    # Save IFC file
    print(f"Saving IFC to: {args.output}")
    try:
        bpy.ops.export_ifc.bim(filepath=args.output)
        print(f"IFC export completed")
    except Exception as e:
        print(f"ERROR during IFC export: {e}")
        raise
    
    # Verify output file exists
    from pathlib import Path
    if not Path(args.output).exists():
        print(f"ERROR: Output file not created at {args.output}")
        sys.exit(1)
    
    file_size = Path(args.output).stat().st_size
    print(f"IFC generation complete! File size: {file_size} bytes")

if __name__ == "__main__":
    main()
