bl_info = {
    "name": "BlenderPack",
    "author": "Your Name Here",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > UI > BlenderPack and Properties > Render",
    "description": "Packs a .blend file and its dependencies into a zip file.",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

import bpy

from .blenderpack.blenderpack_panel import VIEW3D_PT_blenderpack
from .blenderpack.render_panel import PROPERTIES_PT_blenderpack
from .blenderpack.pack_blend_operator import WM_OT_pack_blend
from .blenderpack.install_dependencies import InstallDependenciesOperator

class Blenderpack_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout

        # --- Dependency Installer UI ---
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
                row.label(text="Missing dependencies", icon="ERROR")

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
                row.label(text="All dependencies are installed", icon="SOLO_ON")

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
        name="Zip Path",
        description="Path to save the packed zip file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.blenderpack_zip_path

if __name__ == "__main__":
    register()
