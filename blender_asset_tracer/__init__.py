# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#  Copyright (C) 2014-2018 Blender Foundation
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

__version__ = "1.20"

import bpy

class BlenderAssetTracerPreferences(bpy.types.AddonPreferences):
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
    BlenderAssetTracerPreferences,
    InstallDependenciesOperator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
