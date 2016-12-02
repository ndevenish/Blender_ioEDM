#!/usr/bin/env blender

import sys
import os

import bpy
import addon_utils

def _main(args):
  print("Writing", args)

  default, state = addon_utils.check("io_EDM")
  if not state:
    import io_EDM
    io_EDM.register()

  # Call the import operator
  bpy.ops.export_mesh.edm(filepath="test.edm")

if __name__ == "__main__":
  if _main(sys.argv) == -1:
    sys.exit()