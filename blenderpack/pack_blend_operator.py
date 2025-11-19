import bpy
import os
import pathlib
import sys
import traceback

class WM_OT_pack_blend(bpy.types.Operator):
    bl_idname = "wm.pack_blend"
    bl_label = "Pack this Blend File"
    bl_description = "Pack current .blend file and dependencies into ZIP"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        blend_path_str = bpy.data.filepath
        if not blend_path_str or not os.path.exists(blend_path_str):
            self.report({'ERROR'}, "Save the .blend file first.")
            return {'CANCELLED'}
        blend_path = pathlib.Path(blend_path_str)
        
        zip_path_str = context.scene.blenderpack_zip_path
        if not zip_path_str:
            zip_path = blend_path.with_stem(blend_path.stem + "_packed").with_suffix('.zip')
        else:
            prop_path = pathlib.Path(zip_path_str)
            if prop_path.is_dir():
                zip_path = prop_path / f"{blend_path.stem}_packed.zip"
            elif prop_path.suffix.lower() not in {'.zip', ''}:
                zip_path = prop_path.with_suffix('.zip')
            else:
                zip_path = prop_path
                
        if zip_path.exists():
            self.report({'ERROR'}, f"ZIP exists: {zip_path}. Delete or choose another path.")
            return {'CANCELLED'}
            
        context.scene.blenderpack_zip_path = str(zip_path.parent if zip_path.parent != blend_path.parent else zip_path)

        # --- IMPORT LOGIC ---
        try:
            # This uses the local folder enabled by __init__.py
            from blender_asset_tracer.pack import zipped
        except ImportError as e:
            # This error usually means boto3/requests/zstandard are missing
            self.report({'ERROR'}, f"Import failed: {e}. Please click 'Install Dependencies' in Preferences.")
            print(f"BlenderPack Error: {e}")
            return {'CANCELLED'}
        # --------------------

        class ProgressCallback(object):
            def __init__(self, op):
                self.op = op
            def __getattr__(self, name):
                return lambda *a, **k: None 

        try:
            packer = zipped.ZipPacker(blend_path, project=blend_path.parent, target=str(zip_path), relative_only=True)
            packer.progress_cb = ProgressCallback(self)
            packer.strategise()
            packer.execute()
            self.report({'INFO'}, f"Packed blend and dependencies to {zip_path}")
        except Exception as e:
            self.report({'ERROR'}, f"Packing failed: {str(e)}")
            traceback.print_exc()
            return {'CANCELLED'}
            
        return {'FINISHED'}