import bpy


class VIEW3D_PT_blenderpack(bpy.types.Panel):
    bl_label = "BlenderPack"
    bl_idname = "VIEW3D_PT_blenderpack"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlenderPack"  # Dedicated tab

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.prop(scene, "blenderpack_zip_path", text="", icon='FILE_FOLDER')
        layout.separator()
        
        row = layout.row()
        row.operator("wm.pack_blend", text="Pack this Blend File", icon='PACKAGE')
        row.enabled = not scene.blenderpack_is_packing

        if scene.blenderpack_is_packing:
            layout.separator()
            layout.label(text=scene.blenderpack_status)
            layout.prop(scene, "blenderpack_progress", text="Progress", slider=True)
        elif scene.blenderpack_result_msg:
            layout.separator()
            icon = 'CHECKMARK' if scene.blenderpack_result_type == 'INFO' else 'ERROR'
            layout.label(text=scene.blenderpack_result_msg, icon=icon)
