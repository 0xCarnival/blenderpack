bl_info = {
    "name": "BlenderPack",
    "author": "Boring Always Bored",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > UI > BlenderPack and Properties > Render",
    "description": "Packs a .blend file and its dependencies into a zip file.",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

import bpy
import sys
import os

# --- FIX: REGISTER PATHS ---
# 1. Add the Addon's own directory to sys.path so we can import the local 'blender_asset_tracer'
addon_dir = os.path.dirname(os.path.abspath(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

# 2. Add the User Modules directory so we can import pip-installed libs (boto3, etc.)
modules_path = bpy.utils.user_resource('SCRIPTS', path="modules")
if not os.path.exists(modules_path):
    os.makedirs(modules_path)
if modules_path not in sys.path:
    sys.path.append(modules_path)
# ---------------------------

from .blenderpack.blenderpack_panel import VIEW3D_PT_blenderpack
from .blenderpack.render_panel import PROPERTIES_PT_blenderpack
from .blenderpack.pack_blend_operator import WM_OT_pack_blend
from .blenderpack.install_dependencies import InstallDependenciesOperator

class Blenderpack_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout

        if not InstallDependenciesOperator.get_installed_packages_initialized():
            InstallDependenciesOperator.set_installed_packages()

        _, missing_packages = InstallDependenciesOperator.check_dependencies_installed()
        is_installing = InstallDependenciesOperator.get_running()

        if is_installing:
            row = layout.row()
            row.label(icon=InstallDependenciesOperator.get_progress_icon(), text="")
            row.progress(
                text=InstallDependenciesOperator.get_progress_name(),
                factor=InstallDependenciesOperator.get_progress(),
            )

        if len(missing_packages) > 0:
            row = layout.row()
            if not is_installing:
                row.label(text="Missing dependencies (boto3, requests, etc)", icon="ERROR")
            row = layout.row()
            install_op = row.operator(
                InstallDependenciesOperator.bl_idname,
                icon="IMPORT",
                text="Install Dependencies",
            )
            install_op.uninstall = False
            if not is_installing:
                row.enabled = True
        else:
            row = layout.row()
            if not is_installing:
                row.label(text="External dependencies installed", icon="SOLO_ON")
            row = layout.row()
            uninstall_op = row.operator(
                InstallDependenciesOperator.bl_idname,
                icon="TRASH",
                text="Uninstall Dependencies",
            )
            uninstall_op.uninstall = True
            if not is_installing:
                row.enabled = True

classes = (
    VIEW3D_PT_blenderpack,
    PROPERTIES_PT_blenderpack,
    WM_OT_pack_blend,
    Blenderpack_Preferences,
    InstallDependenciesOperator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.blenderpack_zip_path = bpy.props.StringProperty(
        name="Zip Path", description="Path to save the packed zip file", default="", maxlen=1024, subtype='FILE_PATH'
    )
    bpy.types.Scene.blenderpack_progress = bpy.props.FloatProperty(
        name="Progress", default=0.0, min=0.0, max=100.0, subtype='PERCENTAGE'
    )
    bpy.types.Scene.blenderpack_status = bpy.props.StringProperty(
        name="Status", default="Idle"
    )
    bpy.types.Scene.blenderpack_is_packing = bpy.props.BoolProperty(
        name="Is Packing", default=False
    )
    bpy.types.Scene.blenderpack_result_msg = bpy.props.StringProperty(
        name="Result Message", default=""
    )
    bpy.types.Scene.blenderpack_result_type = bpy.props.StringProperty(
        name="Result Type", default="INFO"  # INFO or ERROR
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.blenderpack_zip_path
    del bpy.types.Scene.blenderpack_progress
    del bpy.types.Scene.blenderpack_status
    del bpy.types.Scene.blenderpack_is_packing
    del bpy.types.Scene.blenderpack_result_msg
    del bpy.types.Scene.blenderpack_result_type

if __name__ == "__main__":
    register()
