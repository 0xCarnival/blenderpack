import bpy

class PROPERTIES_PT_blenderpack(bpy.types.Panel):
    bl_label = "BlenderPack"
    bl_idname = "PROPERTIES_PT_blenderpack"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "blenderpack_zip_path", text="", icon='FILE_FOLDER')
        layout.separator()
        layout.operator("wm.pack_blend", text="Pack this Blend File", icon='PACKAGE')
