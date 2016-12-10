#!/usr/bin/env python3

import pickle
import code
from io_EDM import edm

print("Loading data file....")
with open("dump.dat", "rb") as f:
  dataSet = pickle.load(f)
  data = dataSet["data"]
  errors = dataSet["errors"]


def all_materials():
  for edm in data.values():
    for mat in edm.root.materials:
      yield mat

def all_nodes():
  for edm in data.values():
    for node in edm.nodes:
      yield node

def all_renderNodes():
  for edm in data.values():
    for node in edm.renderNodes:
      yield node

def all_shellNodes():
  for edm in data.values():
    for node in edm.shellNodes:
      yield node

def all_Textures():
  for mat in all_materials():
    for tex in mat.textures:
      yield tex

def all_lights():
  for edm in data.values():
    for light in edm.lightNodes:
      yield light

def print_material_table():
  matData = {}
  for edm in data.values():
    for mat in edm.node.materials:
      name = mat.base_material
      uniforms = set(mat.props["UNIFORMS"].keys()) | set(mat.props["ANIMATED_UNIFORMS"].keys())
      matData[name] = uniforms

  print("Table of base material => Uniform values")
  print("\n".join([x.ljust(31) + " | " + ", ".join("`{}`".format(i) for i in sorted(l)) + " |" for x, l in sorted(matData.items(), key=lambda g: g[0])]))

def print_vertex_channel_count():
  chanCount = {}
  for mat in all_materials():
    for i, count in enumerate(mat.vertex_format.data):
      if not i in chanCount and count > 0:
        chanCount[i] = set()
      if count > 0:
        chanCount[i].add(count)
  print(chanCount)

# dat = set()
# for edm in data.values():
#   dat = dat | {x.data for x in edm.connectors}
# print(dat)

# Look at all material channels
code.interact(local=locals())