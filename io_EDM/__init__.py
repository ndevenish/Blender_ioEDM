
bl_info = {
  'name': "Import: .EDM model files",
  'description': "Importing of .EDM model files",
  'author': "Nicholas Devenish",
  'version': (0,0,1),
  'blender': (2, 78, 0),
  'location': "File > Import/Export > .EDM Files",
  'category': 'Import-Export',
}

import bpy

# This handles reloads
# if "bpy" in locals():
#     import importlib
#     if "stl_utils" in locals():
#         importlib.reload(stl_utils)
#     if "blender_utils" in locals():
#         importlib.reload(blender_utils)


def register():
  from .importer import register as importer_register
  from .rna import register as rna_register
  from .panels import register as panels_register
  rna_register()
  panels_register()
  importer_register()
  bpy.utils.register_module(__name__)
  
def unregister():
  from .importer import unregister as importer_unregister
  from .rna import unregister as rna_unregister
  from .panels import unregister as panels_unregister
  importer_unregister()
  panels_unregister()
  rna_unregister()
  bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
  register()
