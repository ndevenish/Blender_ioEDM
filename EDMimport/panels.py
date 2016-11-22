import bpy

bpy.types.Object.is_connector = bpy.props.BoolProperty(
    default=False, 
    name="Is Connector?", 
    description="Is this empty a connector object?")

class DCSWorldPanel(bpy.types.Panel):
  bl_idname = "OBJECT_PT_dcs_world"
  bl_label = "DCS World"
  bl_space_type = 'PROPERTIES'
  bl_region_type = 'WINDOW'
  bl_context = "data"

  def draw(self, context):
    if context.object.type == 'EMPTY':
      self.layout.prop(context.object, "is_connector")

bpy.utils.register_class(DCSWorldPanel)
