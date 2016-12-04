"""
rna

Contains extensions to the blender data model
"""

import bpy

_edm_matTypes = (
  ("def_material", "Default", "Default"),
  ("glass_material","Glass", "Glass"), 
  ("self_illum_material","Self-illuminated", "Self-illuminated"), 
  ("transparent_self_illum_material","Transparent Self-illuminated", "Transparent Self-illuminated"), 
  ("additive_self_illum_material", "additive_self_illum_material", "additive_self_illum_material"),
  ("bano_material", "bano_material", "bano_material"),
  ("building_material", "building_material", "building_material"),
  ("chrome_material", "chrome_material", "chrome_material"),
  ("color_material", "color_material", "color_material"),
  ("fake_omni_lights", "fake_omni_lights", "fake_omni_lights"),
  ("fake_spot_lights", "fake_spot_lights", "fake_spot_lights"),
  ("forest_material", "forest_material", "forest_material"),
  ("lines_material", "lines_material", "lines_material"),
  ("mirror_material", "mirror_material", "mirror_material"),
)

_edm_blendTypes = (
  ("0", "None", "None"),
  ("1", "Blend", "Blend"),
  ("2", "Alpha Test", "Alpha Test"),
  ("3", "Sum. Blending", "Sum. Blending"),
  # (4. "Z Written Blending", "Z Written Blending"),
)


class EDMObjectSettings(bpy.types.PropertyGroup):
  # Only for empty objects: Is this a connector
  is_connector = bpy.props.BoolProperty(
      default=False, 
      name="Is Connector?", 
      description="Is this empty a connector object?")
  is_renderable = bpy.props.BoolProperty(
      default=True, 
      name="Renderable", 
      description="Can this object's mesh be rendered")
  is_collision_shell = bpy.props.BoolProperty(
      default=False, 
      name="Collision Shell", 
      description="Is this mesh used for collision calculations?")
  damage_argument = bpy.props.IntProperty(
      default=-1, 
      name="Damage Argument", 
      description="The damage argument affecting this object")

def updateSceneArgument(self, context):
  print(self, context)
  print("Updating scene argument")

def register():
  bpy.utils.register_class(EDMObjectSettings)
  bpy.types.Object.edm = bpy.props.PointerProperty(type=EDMObjectSettings)
  bpy.types.Action.argument = bpy.props.IntProperty(name="Argument", default=0, min=0)
  bpy.types.Material.edm_material = bpy.props.EnumProperty(
      items=_edm_matTypes, default="def_material", name="Base Material",
      description="The internal EDM material to use as a basis")
  bpy.types.Material.edm_blending = bpy.props.EnumProperty(
      items=_edm_blendTypes, default="0", name="Opacity mode",
      description="The method to use for calculating material opacity/alpha blending")

  bpy.types.Scene.active_edm_argument = bpy.props.IntProperty(name="Active Argument", default=-1, min=-1, update=updateSceneArgument)


def unregister():
  del bpy.types.Scene.active_edm_argument
  del bpy.types.Material.edm_blending
  del bpy.types.Material.edm_material
  del bpy.types.Action.argument
  del bpy.types.Object.edm
  bpy.utils.unregister_class(EDMObjectSettings)

