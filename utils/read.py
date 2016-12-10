#!/usr/bin/env blender

import sys
import os

import bpy
import addon_utils

def _main(args):
  try:
    myArgumentIndex = next(i for i, v in enumerate(sys.argv) if v == "--")
    args = args[myArgumentIndex+1:]
  except StopIteration:
    print("Error: No .EDM files passed for opening. Rememeber to separate from blender arguments with '--'")
    return -1

  print("Reading", args)

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
  bpy.ops.import_mesh.edm(filepath=args[0], shadeless=True)

if __name__ == "__main__":
  if _main(sys.argv) == -1:
    sys.exit()