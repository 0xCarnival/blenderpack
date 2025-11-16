import bpy


class VIEW3D_PT_blenderpack(bpy.types.Panel):
    bl_label = "BlenderPack"
    bl_idname = "VIEW3D_PT_blenderpack"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BlenderPack"  # Dedicated tab

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "blenderpack_zip_path", text="", icon='FILE_FOLDER')
        layout.separator()
        layout.operator("wm.pack_blend", text="Pack this Blend File", icon='PACKAGE')

