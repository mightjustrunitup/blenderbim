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
    # Values are in meters from the edge function
    length = params.get('length', 5.0)
    height = params.get('height', 3.0)
    thickness = params.get('thickness', 0.2)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    # Create wall
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y, z + height/2))
    wall_obj = bpy.context.active_object
    wall_obj.scale = (length, thickness, height)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcWall", predefined_type="SOLIDWALL", userdefined_type="")
    
    return wall_obj

def create_slab(params: dict):
    """Create a slab/floor using BlenderBIM"""
    # Values are in meters from the edge function
    length = params.get('length', 5.0)
    width = params.get('width', 5.0)
    thickness = params.get('thickness', 0.2)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    # Create slab
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y + width/2, z + thickness/2))
    slab_obj = bpy.context.active_object
    slab_obj.scale = (length, width, thickness)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcSlab", predefined_type="FLOOR", userdefined_type="")
    
    return slab_obj

def create_door(params: dict):
    """Create a door using BlenderBIM"""
    # Values are in meters from the edge function
    width = params.get('width', 0.9)
    height = params.get('height', 2.1)
    thickness = params.get('thickness', 0.05)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    # Create door panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y, z + height/2))
    door_obj = bpy.context.active_object
    door_obj.scale = (width, thickness, height)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcDoor", predefined_type="DOOR", userdefined_type="")
    
    return door_obj

def create_window(params: dict):
    """Create a window using BlenderBIM"""
    # Values are in meters from the edge function
    width = params.get('width', 1.2)
    height = params.get('height', 1.2)
    thickness = params.get('thickness', 0.1)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 1.0)
    
    # Create window frame
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y, z + height/2))
    window_obj = bpy.context.active_object
    window_obj.scale = (width, thickness, height)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcWindow", predefined_type="WINDOW", userdefined_type="")
    
    return window_obj

def create_column(params: dict):
    """Create a column using BlenderBIM"""
    # Values are in meters from the edge function
    width = params.get('width', 0.3)
    depth = params.get('depth', 0.3)
    height = params.get('height', 3.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    # Create column
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z + height/2))
    column_obj = bpy.context.active_object
    column_obj.scale = (width, depth, height)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcColumn", predefined_type="COLUMN", userdefined_type="")
    
    return column_obj

def create_beam(params: dict):
    """Create a beam using BlenderBIM"""
    # Values are in meters from the edge function
    length = params.get('length', 5.0)
    width = params.get('width', 0.3)
    height = params.get('height', 0.4)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 3.0)
    
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
    # Values are in meters from the edge function
    length = params.get('length', 10.0)
    width = params.get('width', 10.0)
    thickness = params.get('thickness', 0.2)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 6.0)
    
    # Create roof slab
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y + width/2, z))
    roof_obj = bpy.context.active_object
    roof_obj.scale = (length, width, thickness)
    
    # Assign IFC class
    bpy.ops.bim.assign_class(ifc_class="IfcRoof", predefined_type="FLAT_ROOF", userdefined_type="")
    
    return roof_obj

def create_box(params: dict):
    """Create a box/cube using BlenderBIM"""
    width = params.get('width', 1.0)
    height = params.get('height', 1.0)
    depth = params.get('depth', 1.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + depth/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, depth, height)
    obj.name = params.get('name', 'Box')
    
    bpy.ops.bim.assign_class(ifc_class="IfcBuildingElementProxy", predefined_type="ELEMENT", userdefined_type="")
    return obj

def create_cylinder(params: dict):
    """Create a cylinder using BlenderBIM"""
    radius = params.get('radius', 0.5)
    height = params.get('height', 2.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height, location=(x, y, z + height/2))
    obj = bpy.context.active_object
    obj.name = params.get('name', 'Cylinder')
    
    bpy.ops.bim.assign_class(ifc_class="IfcColumn", predefined_type="COLUMN", userdefined_type="")
    return obj

def create_sphere(params: dict):
    """Create a sphere using BlenderBIM"""
    radius = params.get('radius', 0.5)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(x, y, z))
    obj = bpy.context.active_object
    obj.name = params.get('name', 'Sphere')
    
    bpy.ops.bim.assign_class(ifc_class="IfcBuildingElementProxy", predefined_type="ELEMENT", userdefined_type="")
    return obj

def create_cone(params: dict):
    """Create a cone using BlenderBIM"""
    radius = params.get('radius', 0.5)
    height = params.get('height', 2.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cone_add(radius1=radius, depth=height, location=(x, y, z + height/2))
    obj = bpy.context.active_object
    obj.name = params.get('name', 'Cone')
    
    bpy.ops.bim.assign_class(ifc_class="IfcBuildingElementProxy", predefined_type="ELEMENT", userdefined_type="")
    return obj

def create_torus(params: dict):
    """Create a torus using BlenderBIM"""
    radius = params.get('radius', 1.0)
    tube = params.get('tube', 0.25)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=tube, location=(x, y, z))
    obj = bpy.context.active_object
    obj.name = params.get('name', 'Torus')
    
    bpy.ops.bim.assign_class(ifc_class="IfcBuildingElementProxy", predefined_type="ELEMENT", userdefined_type="")
    return obj

def create_plane(params: dict):
    """Create a plane using BlenderBIM"""
    width = params.get('width', 2.0)
    height = params.get('height', 2.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x + width/2, y + height/2, z))
    obj = bpy.context.active_object
    obj.scale = (width, height, 1)
    obj.name = params.get('name', 'Plane')
    
    bpy.ops.bim.assign_class(ifc_class="IfcSlab", predefined_type="FLOOR", userdefined_type="")
    return obj

# ===== STRUCTURAL FOUNDATIONS =====
def create_footing(params: dict):
    """Create a foundation footing"""
    width = params.get('width', 2.0)
    depth = params.get('depth', 2.0)
    thickness = params.get('thickness', 0.5)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', -0.5)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + depth/2, z + thickness/2))
    obj = bpy.context.active_object
    obj.scale = (width, depth, thickness)
    obj.name = params.get('name', 'Footing')
    
    bpy.ops.bim.assign_class(ifc_class="IfcFooting", predefined_type="PAD_FOOTING", userdefined_type="")
    return obj

def create_pile(params: dict):
    """Create a deep foundation pile"""
    diameter = params.get('diameter', 0.6)
    length = params.get('length', 10.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=diameter/2, depth=length, location=(x, y, z - length/2))
    obj = bpy.context.active_object
    obj.name = params.get('name', 'Pile')
    
    bpy.ops.bim.assign_class(ifc_class="IfcPile", predefined_type="DRIVEN", userdefined_type="")
    return obj

def create_pile_cap(params: dict):
    """Create a pile cap"""
    width = params.get('width', 2.0)
    depth = params.get('depth', 2.0)
    thickness = params.get('thickness', 0.8)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', -0.3)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + depth/2, z + thickness/2))
    obj = bpy.context.active_object
    obj.scale = (width, depth, thickness)
    obj.name = params.get('name', 'PileCap')
    
    bpy.ops.bim.assign_class(ifc_class="IfcFooting", predefined_type="PILE_CAP", userdefined_type="")
    return obj

# ===== STRUCTURAL FRAMING =====
def create_truss(params: dict):
    """Create a structural truss"""
    length = params.get('length', 10.0)
    height = params.get('height', 2.0)
    width = params.get('width', 0.2)
    x = params.get('x', 0.0)
    y = params.get('y', 3.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (length, width, height)
    obj.name = params.get('name', 'Truss')
    
    bpy.ops.bim.assign_class(ifc_class="IfcMember", predefined_type="TRUSS", userdefined_type="")
    return obj

def create_brace(params: dict):
    """Create a diagonal structural brace"""
    length = params.get('length', 3.0)
    width = params.get('width', 0.2)
    height = params.get('height', 0.2)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    angle = params.get('angle', 45)
    
    import math
    angle_rad = math.radians(angle)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y, z + length/2 * math.sin(angle_rad)))
    obj = bpy.context.active_object
    obj.scale = (length, width, height)
    obj.rotation_euler[1] = angle_rad
    obj.name = params.get('name', 'Brace')
    
    bpy.ops.bim.assign_class(ifc_class="IfcMember", predefined_type="BRACE", userdefined_type="")
    return obj

def create_plate(params: dict):
    """Create a structural steel plate"""
    width = params.get('width', 0.5)
    height = params.get('height', 0.5)
    thickness = params.get('thickness', 0.02)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + thickness/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, thickness, height)
    obj.name = params.get('name', 'Plate')
    
    bpy.ops.bim.assign_class(ifc_class="IfcPlate", predefined_type="BASE_PLATE", userdefined_type="")
    return obj

def create_reinforcing_bar(params: dict):
    """Create reinforcing steel bar (rebar)"""
    diameter = params.get('diameter', 0.016)
    length = params.get('length', 5.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=diameter/2, depth=length, location=(x + length/2, y, z))
    obj = bpy.context.active_object
    obj.rotation_euler[1] = 1.5708  # 90 degrees to make it horizontal
    obj.name = params.get('name', 'Rebar')
    
    bpy.ops.bim.assign_class(ifc_class="IfcReinforcingBar", predefined_type="SPACEBAR", userdefined_type="")
    return obj

# ===== ARCHITECTURAL ELEMENTS =====
def create_ramp(params: dict):
    """Create an accessible ramp"""
    width = params.get('width', 1.5)
    length = params.get('length', 10.0)
    height = params.get('height', 1.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    import math
    
    # Create ramp as an angled slab
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + length/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, length, 0.2)
    obj.rotation_euler[0] = math.atan(height / length)
    obj.name = params.get('name', 'Ramp')
    
    bpy.ops.bim.assign_class(ifc_class="IfcRamp", predefined_type="STRAIGHT_RUN_RAMP", userdefined_type="")
    return obj

def create_railing(params: dict):
    """Create a safety railing"""
    length = params.get('length', 5.0)
    height = params.get('height', 1.1)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    # Create top rail
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y, z + height))
    obj = bpy.context.active_object
    obj.scale = (length, 0.05, 0.05)
    obj.name = params.get('name', 'Railing')
    
    bpy.ops.bim.assign_class(ifc_class="IfcRailing", predefined_type="HANDRAIL", userdefined_type="")
    return obj

def create_curtain_wall(params: dict):
    """Create a glass curtain wall facade"""
    width = params.get('width', 10.0)
    height = params.get('height', 3.0)
    thickness = params.get('thickness', 0.1)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, thickness, height)
    obj.name = params.get('name', 'CurtainWall')
    
    bpy.ops.bim.assign_class(ifc_class="IfcCurtainWall", predefined_type="USERDEFINED", userdefined_type="")
    return obj

def create_ceiling(params: dict):
    """Create a ceiling"""
    width = params.get('width', 5.0)
    depth = params.get('depth', 5.0)
    thickness = params.get('thickness', 0.05)
    x = params.get('x', 0.0)
    y = params.get('y', 2.7)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y, z + depth/2))
    obj = bpy.context.active_object
    obj.scale = (width, thickness, depth)
    obj.name = params.get('name', 'Ceiling')
    
    bpy.ops.bim.assign_class(ifc_class="IfcCovering", predefined_type="CEILING", userdefined_type="")
    return obj

def create_covering(params: dict):
    """Create floor, wall, or ceiling covering"""
    width = params.get('width', 5.0)
    depth = params.get('depth', 5.0)
    thickness = params.get('thickness', 0.01)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + thickness/2, z + depth/2))
    obj = bpy.context.active_object
    obj.scale = (width, thickness, depth)
    obj.name = params.get('name', 'Covering')
    
    bpy.ops.bim.assign_class(ifc_class="IfcCovering", predefined_type="FLOORING", userdefined_type="")
    return obj

# ===== MEP SYSTEMS =====
def create_duct(params: dict):
    """Create HVAC ductwork"""
    width = params.get('width', 0.4)
    height = params.get('height', 0.3)
    length = params.get('length', 5.0)
    x = params.get('x', 0.0)
    y = params.get('y', 2.5)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y, z + width/2))
    obj = bpy.context.active_object
    obj.scale = (length, height, width)
    obj.name = params.get('name', 'Duct')
    
    bpy.ops.bim.assign_class(ifc_class="IfcDuctSegment", predefined_type="RIGIDSEGMENT", userdefined_type="")
    return obj

def create_pipe(params: dict):
    """Create piping"""
    diameter = params.get('diameter', 0.05)
    length = params.get('length', 5.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=diameter/2, depth=length, location=(x + length/2, y, z))
    obj = bpy.context.active_object
    obj.rotation_euler[1] = 1.5708  # Horizontal
    obj.name = params.get('name', 'Pipe')
    
    bpy.ops.bim.assign_class(ifc_class="IfcPipeSegment", predefined_type="RIGIDSEGMENT", userdefined_type="")
    return obj

def create_cable_carrier(params: dict):
    """Create cable tray or conduit"""
    width = params.get('width', 0.3)
    height = params.get('height', 0.1)
    length = params.get('length', 5.0)
    x = params.get('x', 0.0)
    y = params.get('y', 2.8)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y, z + width/2))
    obj = bpy.context.active_object
    obj.scale = (length, height, width)
    obj.name = params.get('name', 'CableTray')
    
    bpy.ops.bim.assign_class(ifc_class="IfcCableCarrierSegment", predefined_type="CABLETRAY", userdefined_type="")
    return obj

def create_hvac_equipment(params: dict):
    """Create HVAC equipment"""
    width = params.get('width', 1.0)
    height = params.get('height', 1.0)
    depth = params.get('depth', 0.5)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + depth/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, depth, height)
    obj.name = params.get('name', 'HVAC_Equipment')
    
    bpy.ops.bim.assign_class(ifc_class="IfcUnitaryEquipment", predefined_type="AIRCONDITIONINGUNIT", userdefined_type="")
    return obj

def create_pump(params: dict):
    """Create a mechanical pump"""
    diameter = params.get('diameter', 0.5)
    height = params.get('height', 0.8)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cylinder_add(radius=diameter/2, depth=height, location=(x, y, z + height/2))
    obj = bpy.context.active_object
    obj.name = params.get('name', 'Pump')
    
    bpy.ops.bim.assign_class(ifc_class="IfcPump", predefined_type="CIRCULATOR", userdefined_type="")
    return obj

def create_valve(params: dict):
    """Create a valve"""
    diameter = params.get('diameter', 0.1)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=diameter/2, location=(x, y, z))
    obj = bpy.context.active_object
    obj.name = params.get('name', 'Valve')
    
    bpy.ops.bim.assign_class(ifc_class="IfcValve", predefined_type="ISOLATING", userdefined_type="")
    return obj

def create_sensor(params: dict):
    """Create a sensor"""
    size = params.get('size', 0.1)
    x = params.get('x', 0.0)
    y = params.get('y', 2.5)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_uv_sphere_add(radius=size/2, location=(x, y, z))
    obj = bpy.context.active_object
    obj.name = params.get('name', 'Sensor')
    
    bpy.ops.bim.assign_class(ifc_class="IfcSensor", predefined_type="FIRESENSOR", userdefined_type="")
    return obj

def create_light_fixture(params: dict):
    """Create a lighting fixture"""
    width = params.get('width', 0.6)
    depth = params.get('depth', 0.15)
    height = params.get('height', 0.1)
    x = params.get('x', 0.0)
    y = params.get('y', 2.7)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y, z + depth/2))
    obj = bpy.context.active_object
    obj.scale = (width, height, depth)
    obj.name = params.get('name', 'LightFixture')
    
    bpy.ops.bim.assign_class(ifc_class="IfcLightFixture", predefined_type="POINTSOURCE", userdefined_type="")
    return obj

def create_electrical_outlet(params: dict):
    """Create an electrical outlet"""
    width = params.get('width', 0.08)
    height = params.get('height', 0.12)
    depth = params.get('depth', 0.04)
    x = params.get('x', 0.0)
    y = params.get('y', 0.3)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y + depth/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, depth, height)
    obj.name = params.get('name', 'Outlet')
    
    bpy.ops.bim.assign_class(ifc_class="IfcOutlet", predefined_type="POWEROUTLET", userdefined_type="")
    return obj

def create_switch(params: dict):
    """Create an electrical light switch"""
    width = params.get('width', 0.08)
    height = params.get('height', 0.12)
    depth = params.get('depth', 0.03)
    x = params.get('x', 0.0)
    y = params.get('y', 1.2)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y + depth/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, depth, height)
    obj.name = params.get('name', 'Switch')
    
    bpy.ops.bim.assign_class(ifc_class="IfcSwitchingDevice", predefined_type="TOGGLESWITCH", userdefined_type="")
    return obj

# ===== FURNISHING =====
def create_furniture(params: dict):
    """Create furniture items"""
    width = params.get('width', 1.0)
    height = params.get('height', 0.75)
    depth = params.get('depth', 0.6)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + depth/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, depth, height)
    obj.name = params.get('name', 'Furniture')
    
    bpy.ops.bim.assign_class(ifc_class="IfcFurniture", predefined_type="USERDEFINED", userdefined_type="")
    return obj

def create_cabinet(params: dict):
    """Create a cabinet or storage unit"""
    width = params.get('width', 1.0)
    height = params.get('height', 2.0)
    depth = params.get('depth', 0.6)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + depth/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, depth, height)
    obj.name = params.get('name', 'Cabinet')
    
    bpy.ops.bim.assign_class(ifc_class="IfcFurniture", predefined_type="USERDEFINED", userdefined_type="")
    return obj

def create_countertop(params: dict):
    """Create a countertop or worktop surface"""
    width = params.get('width', 2.0)
    depth = params.get('depth', 0.6)
    thickness = params.get('thickness', 0.04)
    x = params.get('x', 0.0)
    y = params.get('y', 0.9)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y, z + depth/2))
    obj = bpy.context.active_object
    obj.scale = (width, thickness, depth)
    obj.name = params.get('name', 'Countertop')
    
    bpy.ops.bim.assign_class(ifc_class="IfcSlab", predefined_type="FLOOR", userdefined_type="")
    return obj

# ===== SITE ELEMENTS =====
def create_pavement(params: dict):
    """Create pavement or road surface"""
    width = params.get('width', 3.0)
    length = params.get('length', 10.0)
    thickness = params.get('thickness', 0.2)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', -0.2)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + thickness/2, z + length/2))
    obj = bpy.context.active_object
    obj.scale = (width, thickness, length)
    obj.name = params.get('name', 'Pavement')
    
    bpy.ops.bim.assign_class(ifc_class="IfcPavement", predefined_type="USERDEFINED", userdefined_type="")
    return obj

def create_kerb(params: dict):
    """Create a kerb (curb) along pavement edge"""
    length = params.get('length', 10.0)
    width = params.get('width', 0.15)
    height = params.get('height', 0.15)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + length/2, y + width/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (length, width, height)
    obj.name = params.get('name', 'Kerb')
    
    bpy.ops.bim.assign_class(ifc_class="IfcKerb", predefined_type="USERDEFINED", userdefined_type="")
    return obj

def create_parking_space(params: dict):
    """Create a parking space marking"""
    width = params.get('width', 2.5)
    length = params.get('length', 5.0)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    # Create a thin marking
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x + width/2, y + length/2, z + 0.01))
    obj = bpy.context.active_object
    obj.scale = (width, length, 1)
    obj.name = params.get('name', 'ParkingSpace')
    
    bpy.ops.bim.assign_class(ifc_class="IfcBuildingElementProxy", predefined_type="ELEMENT", userdefined_type="")
    return obj

def create_signage(params: dict):
    """Create signage or wayfinding signs"""
    width = params.get('width', 0.6)
    height = params.get('height', 0.4)
    thickness = params.get('thickness', 0.05)
    x = params.get('x', 0.0)
    y = params.get('y', 1.8)
    z = params.get('z', 0.0)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + width/2, y + thickness/2, z + height/2))
    obj = bpy.context.active_object
    obj.scale = (width, thickness, height)
    obj.name = params.get('name', 'Signage')
    
    bpy.ops.bim.assign_class(ifc_class="IfcSign", predefined_type="USERDEFINED", userdefined_type="")
    return obj

def create_stairs(params: dict):
    """Create stairs using BlenderBIM"""
    # Values are in meters from the edge function
    width = params.get('width', 1.2)
    steps = params.get('steps', 15)
    step_height = params.get('stepHeight', 0.18)
    step_depth = params.get('stepDepth', 0.28)
    x = params.get('x', 0.0)
    y = params.get('y', 0.0)
    z = params.get('z', 0.0)
    
    total_height = step_height * steps
    total_length = step_depth * steps
    
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
    # Basic shapes
    'create_box': create_box,
    'create_cylinder': create_cylinder,
    'create_sphere': create_sphere,
    'create_cone': create_cone,
    'create_torus': create_torus,
    'create_plane': create_plane,
    
    # Basic BIM elements
    'create_wall': create_wall,
    'create_slab': create_slab,
    'create_door': create_door,
    'create_window': create_window,
    'create_column': create_column,
    'create_beam': create_beam,
    'create_roof': create_roof,
    'create_stairs': create_stairs,
    
    # Structural foundations
    'create_footing': create_footing,
    'create_pile': create_pile,
    'create_pile_cap': create_pile_cap,
    
    # Structural framing
    'create_truss': create_truss,
    'create_brace': create_brace,
    'create_plate': create_plate,
    'create_reinforcing_bar': create_reinforcing_bar,
    
    # Architectural elements
    'create_ramp': create_ramp,
    'create_railing': create_railing,
    'create_curtain_wall': create_curtain_wall,
    'create_ceiling': create_ceiling,
    'create_covering': create_covering,
    
    # MEP systems
    'create_duct': create_duct,
    'create_pipe': create_pipe,
    'create_cable_carrier': create_cable_carrier,
    'create_hvac_equipment': create_hvac_equipment,
    'create_pump': create_pump,
    'create_valve': create_valve,
    'create_sensor': create_sensor,
    'create_light_fixture': create_light_fixture,
    'create_electrical_outlet': create_electrical_outlet,
    'create_switch': create_switch,
    
    # Furnishing
    'create_furniture': create_furniture,
    'create_cabinet': create_cabinet,
    'create_countertop': create_countertop,
    
    # Site elements
    'create_pavement': create_pavement,
    'create_kerb': create_kerb,
    'create_parking_space': create_parking_space,
    'create_signage': create_signage,
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
