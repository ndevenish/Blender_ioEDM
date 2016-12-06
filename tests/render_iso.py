#!/usr/bin/env blender

import sys
import bpy

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
    print("Error: No output filenames")
    return -1

  if len(args) > 1:
    print("Error: Too many output files")
    return 1

  print("Rendering to " + args[0])
  render_to(args[0])
  sys.exit()

if __name__ == "__main__":
  if _main(sys.argv) == -1:
    sys.exit()

