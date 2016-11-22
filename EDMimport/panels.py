import bpy


class EDMDataPanel(bpy.types.Panel):
  bl_idname = "OBJECT_PT_edmtools"
  bl_label = "EDM Tools"
  bl_space_type = 'PROPERTIES'
  bl_region_type = 'WINDOW'
  bl_context = "data"

  @classmethod
  def poll(cls, context):
    return context.object.type == 'EMPTY'  

  def draw(self, context):
    self.layout.prop(context.object, "is_connector")

def register():
  bpy.utils.register_class(EDMDataPanel)

def unregister():
  bpy.utils.unregister_class(EDMDataPanel)