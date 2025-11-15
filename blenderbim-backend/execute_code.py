"""
Wrapper script to execute user-generated BlenderBIM Python code
and export the resulting IFC file
"""
import sys
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, help='Output IFC file path')
    parser.add_argument('--project-name', default='AI Generated Model', help='Project name')
    args = parser.parse_args()
    
    print(f"Executing BlenderBIM Python code...")
    print(f"Output path: {args.output}")
    print(f"Project name: {args.project_name}")
    
    # At this point, the user's code should have already been executed
    # (since it's passed via --python to Blender before this script)
    # Now we just need to export the IFC file
    
    import bpy
    from blenderbim.bim.ifc import IfcStore
    
    # Get the IFC file from the store
    ifc_file = IfcStore.get_file()
    
    if not ifc_file:
        print("ERROR: No IFC project found in store")
        sys.exit(1)
    
    # Write the IFC file
    print(f"Writing IFC file to: {args.output}")
    ifc_file.write(args.output)
    print(f"✓ IFC file written successfully: {args.output}")
    
    # Verify file was created
    import os
    if os.path.exists(args.output):
        file_size = os.path.getsize(args.output)
        print(f"✓ File verified: {file_size} bytes")
    else:
        print("ERROR: Output file was not created")
        sys.exit(1)

if __name__ == "__main__":
    main()
