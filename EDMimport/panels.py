import bpy


class DCSWorldPanel(bpy.types.Panel):
  bl_idname = "OBJECT_PT_dcs_world"
  bl_label = "DCS World"
  bl_space_type = 'PROPERTIES'
  bl_region_type = 'WINDOW'
  bl_context = "data"

  @classmethod
  def poll(cls, context):
    return context.object.type == 'EMPTY'  

  def draw(self, context):
    self.layout.prop(context.object, "is_connector")

bpy.utils.register_class(DCSWorldPanel)

# In unregistration:
# del bpy.types.Object.is_connector
