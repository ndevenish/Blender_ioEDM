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


# TBC:
  # ("building","Building", "Building"), 
  # ("mirror","Mirror", "Mirror"), 
  # ("phosphor","Phosphor", "Phosphor"), 
  # ("aluminium","Aluminium", "Aluminium"), 
  # ("billboard","Billboard", "Billboard"), 
  # ("chrome","Chrome", "Chrome"), 
  # ("lines_material","lines_material", "lines_material"), 
  # ("fake_omni_lights", "Fake Omni-lights", "Fake Omni-lights"), 
  # ("building_fake_omni_lights", "Building Fake Omni-lights", "Building Fake Omni-lights"), 
  # ("fake_spot_lights", "Fake Spotlights", "Fake Spotlights"), 
  # ("bano", "bano", "bano"), 
  # ("old_tree", "old_tree", "old_tree"), 
  # ("fake_als_lights","Fake ALS Lights", "Fake ALS Lights"), 
  # ("color", "Color", "Color"))

def register():
  # Is an empty object a connector?
  bpy.types.Object.is_connector = bpy.props.BoolProperty(
      default=False, 
      name="Is Connector?", 
      description="Is this empty a connector object?")
  bpy.types.Action.argument = bpy.props.IntProperty(name="Argument", default=0, min=0)
  bpy.types.Material.edm_material = bpy.props.EnumProperty(
      items=_edm_matTypes, default="def_material", name="Base Material",
      description="The internal EDM material to use as a basis")

def unregister():
  del bpy.types.Material.edm_material
  del bpy.types.Object.is_connector
  del bpy.types.Action.argument
