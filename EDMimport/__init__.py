
print("Loading EDMimport")

bl_info = {
  'name': "Import: DCS World .EDM",
  'description': "Importing of DCS world .edm files for aircraft/cockpits",
  'author': "Nicholas Devenish",
  'version': (0,0,1),
  'blender': (2, 78, 0),
  'location': "File > Import/Export > DCS World",
  'category': 'Import-Export',
}

# This handles reloads
# if "bpy" in locals():
#     import importlib
#     if "stl_utils" in locals():
#         importlib.reload(stl_utils)
#     if "blender_utils" in locals():
#         importlib.reload(blender_utils)

import code
import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator, OperatorFileListElement
from bpy.props import ( StringProperty,
                        BoolProperty,
                        CollectionProperty,
                        EnumProperty,
                        FloatProperty,
                      )

class ImportEDM(Operator, ImportHelper):
  bl_idname = "import_mesh.edm"
  bl_label = "Import EDM"
  filename_ext = ".edm"

  filter_glob = StringProperty(
          default="*.edm",
          options={'HIDDEN'},
          )
  files = CollectionProperty(
          name="File Path",
          type=OperatorFileListElement,
          )
  directory = StringProperty(
          subtype='DIR_PATH',
          )

  def execute(self, context):
    # Get a list of files
    paths = [os.path.join(self.directory, name.name) for name in self.files]
    if not paths:
      paths.append(self.filepath)

    # Get a nice display name
    # bpy.path.display_name(os.path.basename(self.filepath))

    # From stl example: Seems to ensure set in correct mode?
    # if bpy.ops.object.mode_set.poll():
    #         bpy.ops.object.mode_set(mode='OBJECT')
    # if bpy.ops.object.select_all.poll():
    #     bpy.ops.object.select_all(action='DESELECT')

    # print("Importing EDM via operator")
    code.interact(local=locals())

    return {'FINISHED'}


def menu_import(self, context):
  print("Menu function")
  self.layout.operator(ImportEDM.bl_idname, text="DCS World (.edm)")


def register():
  bpy.utils.register_module(__name__)
  bpy.types.INFO_MT_file_import.append(menu_import)

def unregister():
  bpt.types.INFO_MT_file_import.remove(menu_import)
  bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
  register()
