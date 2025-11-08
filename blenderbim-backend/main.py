"""
FastAPI Backend for IFC Generation using IfcOpenShell
This is the same core library that powers BlenderBIM.

Deploy this to Railway, Render, or any Python hosting platform.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
import tempfile
import os
import math

app = FastAPI(title="IFC Generator API")

# Enable CORS for Supabase Edge Functions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ToolCall(BaseModel):
    function: Dict[str, Any]

class IFCGenerateRequest(BaseModel):
    tool_calls: List[ToolCall]
    project_name: Optional[str] = "AI Generated BIM Model"

def create_ifc_project(project_name: str):
    """Create a new IFC project with proper structure"""
    ifc_file = ifcopenshell.api.run("project.create_file")
    
    # Create project
    project = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcProject", name=project_name)
    
    # Create units (use meters, not millimeters)
    length_unit = ifcopenshell.api.run("unit.add_si_unit", ifc_file, unit_type="LENGTHUNIT")
    area_unit = ifcopenshell.api.run("unit.add_si_unit", ifc_file, unit_type="AREAUNIT")
    volume_unit = ifcopenshell.api.run("unit.add_si_unit", ifc_file, unit_type="VOLUMEUNIT")
    
    ifcopenshell.api.run("unit.assign_unit", ifc_file, units=[length_unit, area_unit, volume_unit])
    
    # Create context for 3D geometry
    model_context = ifcopenshell.api.run("context.add_context", ifc_file, context_type="Model")
    body_context = ifcopenshell.api.run(
        "context.add_context", ifc_file,
        context_type="Model", context_identifier="Body",
        target_view="MODEL_VIEW", parent=model_context
    )
    
    # Create site and building structure
    site = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBuilding", name="Building")
    storey = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBuildingStorey", name="Ground Floor")
    
    # Assign spatial hierarchy
    ifcopenshell.api.run("aggregate.assign_object", ifc_file, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", ifc_file, relating_object=site, products=[building])
    ifcopenshell.api.run("aggregate.assign_object", ifc_file, relating_object=building, products=[storey])
    
    return ifc_file, storey, body_context

def create_box(ifc_file, storey, context, params):
    """Create a box/cube using IfcBuildingElementProxy"""
    box = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBuildingElementProxy", name=params.get("name", "Box"))
    
    width = params.get("width", 1.0)
    height = params.get("height", 1.0)
    depth = params.get("depth", 1.0)
    
    # Create rectangle profile
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        XDim=width,
        YDim=depth
    )
    
    # Create extrusion direction (Z-axis)
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=height
    )
    
    # Create shape representation
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    box.Representation = product_shape
    
    # Set position - adjust Z so box sits on floor
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    z_adjusted = z + height / 2  # Position bottom at z, not center
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=box, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z_adjusted],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[box], relating_structure=storey)
    
    return box

def create_sphere(ifc_file, storey, context, params):
    """Create a sphere using IfcBuildingElementProxy with swept disk solid"""
    sphere = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBuildingElementProxy", name=params.get("name", "Sphere"))
    
    radius = params.get("radius", 0.5)
    
    # Create circle profile
    circle = ifc_file.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        Radius=radius
    )
    
    # Create revolve around axis to make sphere
    axis = ifc_file.create_entity("IfcAxis1Placement",
        Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
        Axis=ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    )
    
    revolved_solid = ifc_file.create_entity(
        "IfcRevolvedAreaSolid",
        SweptArea=circle,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.)),
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 1., 0.))
        ),
        Axis=axis,
        Angle=360.0
    )
    
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[revolved_solid]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    sphere.Representation = product_shape
    
    # Adjust Z so sphere sits on floor
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    z_adjusted = z + radius  # Position bottom at z
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=sphere, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z_adjusted],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[sphere], relating_structure=storey)
    
    return sphere

def create_cylinder(ifc_file, storey, context, params):
    """Create a cylinder using IfcBuildingElementProxy"""
    cylinder = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBuildingElementProxy", name=params.get("name", "Cylinder"))
    
    radius = params.get("radius", 0.5)
    height = params.get("height", 1.0)
    
    # Create circle profile
    profile = ifc_file.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        Radius=radius
    )
    
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=height
    )
    
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    cylinder.Representation = product_shape
    
    # Adjust Z so cylinder sits on floor
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    z_adjusted = z + height / 2  # Position bottom at z
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=cylinder, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z_adjusted],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[cylinder], relating_structure=storey)
    
    return cylinder

def create_cone(ifc_file, storey, context, params):
    """Create a cone using IfcBuildingElementProxy"""
    cone = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBuildingElementProxy", name=params.get("name", "Cone"))
    
    radius = params.get("radius", 0.5)
    height = params.get("height", 1.0)
    
    # Create circle profile at base
    profile = ifc_file.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        Radius=radius
    )
    
    # Tapering to point - use arbitrary profile with end radius
    # IFC doesn't have direct cone, so we use a tapered extrusion approximation
    # For simplicity, create an extruded circle (cylinder) - full cone support needs more complex geometry
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=height
    )
    
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    cone.Representation = product_shape
    
    # Adjust Z so cone sits on floor
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    z_adjusted = z + height / 2  # Position bottom at z
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=cone, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z_adjusted],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[cone], relating_structure=storey)
    
    return cone

def create_plane(ifc_file, storey, context, params):
    """Create a plane/flat surface using IfcBuildingElementProxy"""
    plane = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBuildingElementProxy", name=params.get("name", "Plane"))
    
    width = params.get("width", 1.0)
    height = params.get("height", 1.0)
    
    # Create rectangle profile for plane
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        XDim=width,
        YDim=height
    )
    
    # Very thin extrusion to simulate plane
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=0.001  # Very thin to simulate plane
    )
    
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    plane.Representation = product_shape
    
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=plane, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[plane], relating_structure=storey)
    
    return plane

def create_wall(ifc_file, storey, context, params):
    """Create an IFC wall with proper BIM properties"""
    wall = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcWall", name=params.get("name", "Wall"))
    
    # Create extrusion profile
    length = params.get("length", 5.0)
    height = params.get("height", 3.0)
    thickness = params.get("thickness", 0.2)
    
    # Create rectangle profile for wall cross-section
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName="Wall Profile",
        XDim=thickness,
        YDim=height
    )
    
    # Create extrusion direction
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    # Create extrusion with proper positioning
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 1., 0.)),
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.)),
        Depth=length
    )
    
    # Create shape representation
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    # Create product definition shape
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    wall.Representation = product_shape
    
    # Set position
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=wall, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    # Add to spatial structure
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[wall], relating_structure=storey)
    
    # Add properties
    pset = ifcopenshell.api.run("pset.add_pset", ifc_file, product=wall, name="Pset_WallCommon")
    ifcopenshell.api.run("pset.edit_pset", ifc_file, pset=pset, properties={
        "Reference": params.get("name", "Wall"),
        "LoadBearing": True,
        "IsExternal": False,
    })
    
    return wall

def create_door(ifc_file, storey, context, params):
    """Create an IFC door"""
    door = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcDoor", name=params.get("name", "Door"))
    
    width = params.get("width", 0.9)
    height = params.get("height", 2.1)
    thickness = params.get("thickness", 0.05)
    
    # Create door panel geometry
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        XDim=width,
        YDim=height
    )
    
    # Create extrusion with proper direction
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=thickness
    )
    
    # Create shape representation
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    door.Representation = product_shape
    
    # Set position
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=door, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[door], relating_structure=storey)
    
    return door

def create_window(ifc_file, storey, context, params):
    """Create an IFC window"""
    window = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcWindow", name=params.get("name", "Window"))
    
    width = params.get("width", 1.2)
    height = params.get("height", 1.5)
    
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        XDim=width,
        YDim=height
    )
    
    # Create extrusion with proper direction
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=0.05
    )
    
    # Create shape representation
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    window.Representation = product_shape
    
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=window, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[window], relating_structure=storey)
    
    return window

def create_column(ifc_file, storey, context, params):
    """Create an IFC column"""
    column = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcColumn", name=params.get("name", "Column"))
    
    width = params.get("width", 0.3)
    depth = params.get("depth", 0.3)
    height = params.get("height", 3.0)
    
    # Create profile
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        XDim=width,
        YDim=depth
    )
    
    # Create extrusion direction (Z-axis up)
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    # Create extrusion with explicit direction
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=height
    )
    
    # Create shape representation
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    # Create product definition shape
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    column.Representation = product_shape
    
    # Set position - adjust Z so column sits on floor
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    z_adjusted = z + height / 2  # Position bottom at z
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=column, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z_adjusted],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[column], relating_structure=storey)
    
    return column

def create_beam(ifc_file, storey, context, params):
    """Create an IFC beam"""
    beam = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBeam", name=params.get("name", "Beam"))
    
    width = params.get("width", 0.3)
    height = params.get("height", 0.4)
    length = params.get("length", 5.0)
    
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        XDim=width,
        YDim=height
    )
    
    # Create extrusion direction (along X-axis for beams)
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.)),
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=length
    )
    
    # Create shape representation
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    beam.Representation = product_shape
    
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=beam, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[beam], relating_structure=storey)
    
    return beam

def create_slab(ifc_file, storey, context, params):
    """Create an IFC slab"""
    slab = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcSlab", name=params.get("name", "Slab"))
    
    width = params.get("width", 10.0)
    depth = params.get("depth", 10.0)
    thickness = params.get("thickness", 0.2)
    
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        XDim=width,
        YDim=depth
    )
    
    # Create extrusion direction (Z-axis for slabs)
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=thickness
    )
    
    # Create shape representation
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    slab.Representation = product_shape
    
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=slab, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[slab], relating_structure=storey)
    
    return slab

def create_torus(ifc_file, storey, context, params):
    """Create a torus (donut shape)"""
    torus = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcBuildingElementProxy", name=params.get("name", "Torus"))
    
    radius = params.get("radius", 1.0)
    tube = params.get("tube", 0.3)
    
    # Create circle profile for tube
    profile = ifc_file.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        Radius=tube
    )
    
    # Create circular path for revolve
    axis = ifc_file.create_entity("IfcAxis1Placement",
        Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(radius, 0., 0.)),
        Axis=ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    )
    
    revolved_solid = ifc_file.create_entity(
        "IfcRevolvedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(radius, 0., 0.)),
            Axis=ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 1., 0.)),
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        Axis=axis,
        Angle=360.0
    )
    
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[revolved_solid]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    torus.Representation = product_shape
    
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    z_adjusted = z + tube  # Position bottom at z
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=torus, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z_adjusted],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[torus], relating_structure=storey)
    
    return torus

def create_stairs(ifc_file, storey, context, params):
    """Create stairs"""
    stairs = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcStair", name=params.get("name", "Stairs"))
    
    width = params.get("width", 1.2)
    steps = params.get("steps", 10)
    step_height = params.get("stepHeight", 0.18)
    step_depth = params.get("stepDepth", 0.28)
    
    # Create each step as a box
    for i in range(steps):
        step_profile = ifc_file.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            XDim=width,
            YDim=step_depth
        )
        
        direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
        
        extrusion = ifc_file.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=step_profile,
            Position=ifc_file.create_entity("IfcAxis2Placement3D",
                Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., i * step_depth, i * step_height)),
                Axis=direction,
                RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
            ),
            ExtrudedDirection=direction,
            Depth=step_height
        )
        
        if i == 0:
            items = [extrusion]
        else:
            break  # For simplicity, create single geometry representing stairs
    
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=items
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    stairs.Representation = product_shape
    
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 0)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=stairs, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[stairs], relating_structure=storey)
    
    return stairs

def create_roof(ifc_file, storey, context, params):
    """Create a roof"""
    roof = ifcopenshell.api.run("root.create_entity", ifc_file, ifc_class="IfcRoof", name=params.get("name", "Roof"))
    
    width = params.get("width", 10.0)
    depth = params.get("depth", 10.0)
    pitch = params.get("pitch", 30)  # degrees
    
    # Calculate roof height from pitch
    pitch_rad = math.radians(pitch)
    roof_height = (width / 2) * math.tan(pitch_rad)
    
    # Create simple pitched roof as extruded profile
    profile = ifc_file.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        XDim=width,
        YDim=depth
    )
    
    direction = ifc_file.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.))
    
    extrusion = ifc_file.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc_file.create_entity("IfcAxis2Placement3D",
            Location=ifc_file.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)),
            Axis=direction,
            RefDirection=ifc_file.create_entity("IfcDirection", DirectionRatios=(1., 0., 0.))
        ),
        ExtrudedDirection=direction,
        Depth=0.2  # Roof thickness
    )
    
    shape_representation = ifc_file.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extrusion]
    )
    
    product_shape = ifc_file.create_entity(
        "IfcProductDefinitionShape",
        Representations=[shape_representation]
    )
    
    roof.Representation = product_shape
    
    x, y, z = params.get("x", 0), params.get("y", 0), params.get("z", 3.0)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=roof, matrix=[
        [1.0, 0.0, 0.0, x],
        [0.0, 1.0, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0]
    ])
    
    ifcopenshell.api.run("spatial.assign_container", ifc_file, products=[roof], relating_structure=storey)
    
    return roof

def create_room(ifc_file, storey, context, params):
    """Create a complete room with walls, floor, and ceiling"""
    width = params.get("width", 5.0)
    depth = params.get("depth", 5.0)
    height = params.get("height", 2.7)
    wall_thickness = params.get("wallThickness", 0.2)
    x_base = params.get("x", 0)
    y_base = params.get("y", 0)
    z_base = params.get("z", 0)
    
    # Create floor
    floor = create_slab(ifc_file, storey, context, {
        "name": f"{params.get('name', 'Room')}_Floor",
        "width": width,
        "depth": depth,
        "thickness": 0.2,
        "x": x_base,
        "y": y_base,
        "z": z_base
    })
    
    # Create walls
    # Front wall
    create_wall(ifc_file, storey, context, {
        "name": f"{params.get('name', 'Room')}_Wall_Front",
        "length": width,
        "height": height,
        "thickness": wall_thickness,
        "x": x_base,
        "y": y_base,
        "z": z_base
    })
    
    # Back wall
    create_wall(ifc_file, storey, context, {
        "name": f"{params.get('name', 'Room')}_Wall_Back",
        "length": width,
        "height": height,
        "thickness": wall_thickness,
        "x": x_base,
        "y": y_base + depth,
        "z": z_base
    })
    
    # Left wall
    create_wall(ifc_file, storey, context, {
        "name": f"{params.get('name', 'Room')}_Wall_Left",
        "length": depth,
        "height": height,
        "thickness": wall_thickness,
        "x": x_base,
        "y": y_base,
        "z": z_base,
        "rotationY": 90
    })
    
    # Right wall
    create_wall(ifc_file, storey, context, {
        "name": f"{params.get('name', 'Room')}_Wall_Right",
        "length": depth,
        "height": height,
        "thickness": wall_thickness,
        "x": x_base + width,
        "y": y_base,
        "z": z_base,
        "rotationY": 90
    })
    
    # Create ceiling
    ceiling = create_slab(ifc_file, storey, context, {
        "name": f"{params.get('name', 'Room')}_Ceiling",
        "width": width,
        "depth": depth,
        "thickness": 0.2,
        "x": x_base,
        "y": y_base,
        "z": z_base + height
    })
    
    return floor

def create_building(ifc_file, storey, context, params):
    """Create a complete building structure"""
    width = params.get("width", 10.0)
    depth = params.get("depth", 10.0)
    floors = params.get("floors", 2)
    floor_height = params.get("floorHeight", 3.0)
    
    # Create foundation slab
    foundation = create_slab(ifc_file, storey, context, {
        "name": f"{params.get('name', 'Building')}_Foundation",
        "width": width,
        "depth": depth,
        "thickness": 0.3,
        "x": 0,
        "y": 0,
        "z": 0
    })
    
    # Create columns at corners for each floor
    for floor in range(floors):
        z_level = floor * floor_height
        
        # Corner columns
        positions = [
            (0, 0), (width, 0), (0, depth), (width, depth)
        ]
        
        for i, (x, y) in enumerate(positions):
            create_column(ifc_file, storey, context, {
                "name": f"{params.get('name', 'Building')}_Column_{floor}_{i}",
                "width": 0.4,
                "depth": 0.4,
                "height": floor_height,
                "x": x,
                "y": y,
                "z": z_level
            })
        
        # Floor slab (not for ground floor)
        if floor > 0:
            create_slab(ifc_file, storey, context, {
                "name": f"{params.get('name', 'Building')}_Floor_{floor}",
                "width": width,
                "depth": depth,
                "thickness": 0.2,
                "x": 0,
                "y": 0,
                "z": z_level
            })
    
    # Create roof
    create_roof(ifc_file, storey, context, {
        "name": f"{params.get('name', 'Building')}_Roof",
        "width": width,
        "depth": depth,
        "pitch": 30,
        "x": 0,
        "y": 0,
        "z": floors * floor_height
    })
    
    return foundation

# Map function names to handlers
ELEMENT_HANDLERS = {
    "create_box": create_box,
    "create_sphere": create_sphere,
    "create_cylinder": create_cylinder,
    "create_cone": create_cone,
    "create_plane": create_plane,
    "create_torus": create_torus,
    "create_wall": create_wall,
    "create_door": create_door,
    "create_window": create_window,
    "create_column": create_column,
    "create_beam": create_beam,
    "create_slab": create_slab,
    "create_stairs": create_stairs,
    "create_roof": create_roof,
    "create_room": create_room,
    "create_building": create_building,
}

@app.post("/generate-ifc")
async def generate_ifc(request: IFCGenerateRequest):
    """
    Generate an IFC file from AI tool calls
    Returns the IFC file as bytes
    """
    try:
        # Create new IFC project
        ifc_file, storey, context = create_ifc_project(request.project_name)
        
        created_elements = []
        
        # Process each tool call
        for tool_call in request.tool_calls:
            function_name = tool_call.function.get("name")
            arguments = tool_call.function.get("arguments", {})
            
            # Parse arguments if they're a string
            if isinstance(arguments, str):
                import json
                arguments = json.loads(arguments)
            
            print(f"Processing: {function_name} with args: {arguments}")
            
            # Get handler for this element type
            handler = ELEMENT_HANDLERS.get(function_name)
            
            if handler:
                try:
                    element = handler(ifc_file, storey, context, arguments)
                    created_elements.append({
                        "name": arguments.get("name", function_name),
                        "type": function_name
                    })
                    print(f"✓ Created {function_name}: {arguments.get('name', 'unnamed')}")
                except Exception as e:
                    print(f"✗ Failed to create {function_name}: {str(e)}")
            else:
                print(f"✗ Unknown element type: {function_name}")
        
        # Write IFC to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            ifc_file.write(tmp.name)
            tmp_path = tmp.name
        
        # Read file as bytes
        with open(tmp_path, "rb") as f:
            ifc_bytes = f.read()
        
        # Clean up temporary file
        os.remove(tmp_path)
        
        return Response(
            content=ifc_bytes,
            media_type="application/x-step",
            headers={
                "Content-Disposition": f"attachment; filename={request.project_name.replace(' ', '_')}.ifc",
                "X-Created-Elements": str(len(created_elements))
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IFC generation failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "ifcopenshell_version": ifcopenshell.version
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
