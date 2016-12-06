#!/usr/bin/env blender

import sys
import os

import bpy
import addon_utils


def render_to(filename):
  PI = 3.1415926

  for material in bpy.data.materials:
    material.use_shadeless = True
  scene = bpy.context.scene

  cam = bpy.data.cameras.new("Camera")
  cam.type = "ORTHO"
  cam.ortho_scale = 10

  cam_ob = bpy.data.objects.new("Camera", cam)
  cam_ob.location = (20,20,16.32)
  cam_ob.rotation_euler = (2*PI/6, 0, 3*2*PI/8)

  scene.objects.link(cam_ob)
  scene.camera = cam_ob

  scene.render.resolution_x = 800
  scene.render.resolution_y = 800
  scene.render.resolution_percentage = 100
  scene.render.filepath = filename
  bpy.ops.render.render(write_still=True)


def _main(args):
  try:
    myArgumentIndex = next(i for i, v in enumerate(sys.argv) if v == "--")
    args = args[myArgumentIndex+1:]
  except StopIteration:
    print("Error: No .EDM files passed for opening. Rememeber to separate from blender arguments with '--'")
    return -1

  assert len(args) == 2
  print("Reading", args)
  infile, outfile = args

  default, state = addon_utils.check("io_EDM")
  if not state:
    import io_EDM
    io_EDM.register()

  # Should get rid of all objects for simple read script
  for obj in bpy.context.scene.objects:
    if obj.type == "CAMERA":
      continue
    bpy.context.scene.objects.unlink(obj)

  # Call the import operator
  bpy.ops.import_mesh.edm(filepath=infile)

  render_to(outfile)
  sys.exit()

if __name__ == "__main__":
  if _main(sys.argv) == -1:
    sys.exit()