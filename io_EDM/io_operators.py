import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator, OperatorFileListElement
from bpy.props import ( StringProperty,
                        BoolProperty,
                        CollectionProperty,
                        EnumProperty,
                        FloatProperty,
                      )
import os

import logging
logger = logging.getLogger(__name__)

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

    if len(paths) > 1:
      self.report("ERROR", "Importer cannot handle more than one input file currently")
      return "CANCELLED"
    
    # Import the file
    logger.warning("Reading EDM file {}".format(paths[0]))
    

    return {'FINISHED'}

def menu_import(self, context):
  print("Menu function")
  self.layout.operator(ImportEDM.bl_idname, text="DCS World (.edm)")

def register():
  bpy.types.INFO_MT_file_import.append(menu_import)

def unregister():
  bpy.types.INFO_MT_file_import.remove(menu_import)