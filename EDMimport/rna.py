"""
rna

Contains extensions to the blender data model
"""

import bpy

def register():
  # Is an empty object a connector?
  bpy.types.Object.is_connector = bpy.props.BoolProperty(
      default=False, 
      name="Is Connector?", 
      description="Is this empty a connector object?")
  bpy.types.Action.argument = bpy.props.IntProperty(name="Argument", default=0, min=0)


def unregister():
  del bpy.types.Object.is_connector
  del bpy.types.Action.argument
