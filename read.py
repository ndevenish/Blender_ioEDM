#!/usr/bin/env python3

import sys
sys.path.append("/Users/xgkkp/python/edm")

# Ensure we have loaded all the EDM meta-tools
import EDMimport
EDMimport.register()

from edm import EDMFile
import code

import re
import glob, fnmatch


edm = EDMFile("Cockpit_Su-25T.EDM")
# edm = EDMFile("samples/ArgUnambiguous.EDM")
# edm = EDMFile("Intro_Spheres.EDM")

import bpy
import bmesh
from edm.mathtypes import *
from edm.types import ArgAnimationNode, ArgRotationNode, ArgPositionNode

def create_object(renderNode):
  # Marshal the vertices/faces into sets ready for consumption
  assert renderNode.material.vertex_format.nposition == 4
  posIndex = renderNode.material.vertex_format.position_indices
  vertexPositionData = [vector_to_blender(Vector(x[idx] for idx in posIndex)) for x in renderNode.vertexData]
  # assert len(renderNode.indexData) % 3 == 0
  # indexData = [renderNode.indexData[i:i+3] for i in range(0, len(renderNode.indexData), 3)]
  indexData = renderNode.indexData

  # Prepare the normals for each vertex
  if renderNode.material.vertex_format.nnormal == 3:
    nI = renderNode.material.vertex_format.normal_indices
    normal_vectors = [Vector([x[ind] for ind in nI]) for x in renderNode.vertexData]
    normalData = [vector_to_blender(x) for x in normal_vectors]
  else:
    normalData = None
    
  bm = bmesh.new()

  # Create the BMesh vertices, optionally with normals
  for i, vtx in enumerate(vertexPositionData):
    vert = bm.verts.new(vtx)
    if normalData:
      vert.normal = normalData[i]

  bm.verts.ensure_lookup_table()

  # Only do texture coordinate generation if we have texture coordinates....
  if renderNode.material.vertex_format.ntexture:
    # Generate a lookup table of UV data for each face
    uI = renderNode.material.vertex_format.texture_indices
    def _getIndexUV(index):
      try:
        return tuple(renderNode.vertexData[index][x] for x in uI)
      except IndexError:
        import pdb
        pdb.set_trace()
    uvData = [tuple(_getIndexUV(index) for index in face) for face in indexData]

    # Ensure a UV layer exists before creating faces
    uv_layer = bm.loops.layers.uv.verify()
    bm.faces.layers.tex.verify()  # currently blender needs both layers.
  else:
    uvData = None

  for i, face in enumerate(indexData):
  # for face, uvs in zip(indexData, uvData):
    try:
      f = bm.faces.new([bm.verts[i] for i in face])
      # Add UV data if we have any
      if uvData:
        for loop, uv in zip(f.loops, uvData[i]):
          loop[uv_layer].uv = (uv[0], -uv[1])
    except ValueError as e:
      print("Error: {}".format(e))

  # Put the mesh data into the scene
  mesh = bpy.data.meshes.new(renderNode.name)
  bm.to_mesh(mesh)
  mesh.update()
  ob = bpy.data.objects.new(renderNode.name, mesh)
  ob.data.materials.append(renderNode.material.blender_material)

  # Start putting in animation data
  ob.rotation_mode = 'QUATERNION'

  if isinstance(renderNode.parent, ArgAnimationNode):
    argNode = renderNode.parent
    # print ("""from collections import namedtuple\nArgAnimationBase = namedtuple("ArgAnimationBase", ["unknown", "matrix", "position", "quat_1", "quat_2", "scale"])""")
    print(renderNode.name)
    print("aab = " + repr(argNode.base))
    print("posData = " + repr(argNode.posData))
    print("rotData = " + repr(argNode.rotData))

    # obj.keyframe_insert(data_path="location", frame=10.0, index=2)
    # Work out the transformation chain for this object

    # Scale is weird because there is no easy direct way to build it in blender
    fixScale = Matrix.Scale(1,4)
    fixScale[0][0] = argNode.base.scale[0]
    fixScale[1][1] = argNode.base.scale[1]
    fixScale[2][2] = argNode.base.scale[2]
    
    fixTrans = Matrix.Translation(argNode.base.position)
    fixQuat1 = argNode.base.quat_1.to_matrix().to_4x4()
    fixQuat2 = argNode.base.quat_2.to_matrix().to_4x4()
    baseTransform = fixTrans * fixQuat1 * fixQuat2 * fixScale * argNode.base.matrix

    # With:
    #   aabT = Matrix.Translation(argNode.base.position)
    #   aabS = argNode.base.scale as a Scale Matrix
    #   q1m  = argNode.base.quat_1 as a Matrix (e.g. fixQuat1)
    #   q2m  = argNode.base.quat_2 as a Matrix (e.g. fixQuat2)
    #   mat  = argNode.base.matrix
    #   m2b  = matrix_to_blender e.g. swapping Z -> -Y

    # Initial tests had supposed that the transformation was:
    #    baseTransform = aabT * q1m * q2m * aabS * mat
    # However the correct transform for e.g. kpp_baraban_0 is the following
    #    C.object.location = (m2b(mat)*aabT*q1m).decompose()[0]
    # For which case where q2m, aabS are identity. 

    ob.location, ob.rotation_quaternion, ob.scale = baseTransform.decompose()

    ob.animation_data_create()

    if isinstance(argNode, ArgRotationNode):
      for arg, rotData in argNode.rotData:
        # Calculate the frame range
        maxFrame = max(abs(x.frame) for x in rotData)
        frameScale = 100 / maxFrame
        # Create an action for this rotation
        actionName = "{}Action{}".format(renderNode.name, arg)
        action = bpy.data.actions.new(actionName)
        action.use_fake_user = True
        action.argument = arg
        ob.animation_data.action = action

        for key in rotData:
          keyRot = key.value
          # keyRot = key.value.to_matrix().to_4x4()
          # keyTransform = fixTrans * fixQuat1 * keyRot * fixQuat2 * fixScale * argNode.base.matrix
          rot = argNode.base.quat_1 * key.value * argNode.base.quat_2 * argNode.base.matrix.decompose()[1]
          # l, r, s = keyTransform.decompose()   
          ob.rotation_quaternion = rot
          ob.keyframe_insert(data_path="rotation_quaternion", frame=int(key.frame*frameScale))

        # Go through and set everything to linear interpolation
        for fcurve in ob.animation_data.action.fcurves:
          for kf in fcurve.keyframe_points:
            kf.interpolation = 'LINEAR'

    if isinstance(argNode, ArgPositionNode):
      for arg, posData in argNode.posData:
        # Calculate the frame range
        maxFrame = max(abs(x.frame) for x in posData)
        frameScale = 100 / maxFrame
        # Create an action for this translation
        actionName = "{}Action{}".format(renderNode.name, arg)
        action = bpy.data.actions.new(actionName)
        action.use_fake_user = True
        action.argument = arg
        ob.animation_data.action = action

        # for key in posData:
        #   import pdb
        #   pdb.set_trace()

  # import pdb
  # pdb.set_trace()
  bpy.context.scene.objects.link(ob)

  return ob

def _find_texture_file(name):
  files = glob.glob(name+".*")
  if not files:
    matcher = re.compile(fnmatch.translate(name+".*"), re.IGNORECASE)
    files = [x for x in glob.glob(".*") if matcher.match(x)]
    if not files:
      files = glob.glob("textures/"+name+".*")
      if not files:
        matcher = re.compile(fnmatch.translate("textures/"+name+".*"), re.IGNORECASE)
        files = [x for x in glob.glob("textures/.*") if matcher.match(x)]
        if not files:
          print("Warning: Could not find texture named {}".format(name))
          return None
  # print("Found {} as: {}".format(name, files))
  assert len(files) == 1
  textureFilename = files[0]
  return textureFilename

def create_material(material):
  """Create a blender material from an EDM one"""
  # Find the actual file for the texture name
  if len(material.props["TEXTURES"]) == 0:
    return None
  assert len(material.props["TEXTURES"]) == 1
  name = material.props["TEXTURES"][0][0]
  filename = _find_texture_file(name)
  tex = bpy.data.textures.new(name, type="IMAGE")
  if filename:
    tex.image = bpy.data.images.load(filename)
    tex.image.use_alpha = False

  # Create material
  mat = bpy.data.materials.new(material.name)
  mat.use_shadeless = True
  mat.edm_material = material.base_material

  mtex = mat.texture_slots.add()
  mtex.texture = tex
  mtex.texture_coords = "UV"
  mtex.use_map_color_diffuse = True
  # import pdb
  # pdb.set_trace()

  return mat

def create_connector(connector):
  xform = connector.parent.matrix
  # Swap into blender coordinates
  mat = Matrix([xform[0], -xform[2], xform[1], xform[3]])
  loc, rot, sca = mat.decompose()

  # Create a new empty object with a cube representation
  ob = bpy.data.objects.new(connector.name, None)
  ob.empty_draw_type = "CUBE"
  ob.empty_draw_size = 0.01
  ob.location = loc
  ob.rotation_quaternion = rot
  ob.scale = sca
  ob.is_connector = True
  # import pdb
  # pdb.set_trace()
  bpy.context.scene.objects.link(ob)

# def createMaterial():    
#     # Create image texture from image. Change here if the snippet 
#     # folder is not located in you home directory.
#     realpath = os.path.expanduser('~/snippets/textures/color.png')
#     tex = bpy.data.textures.new('ColorTex', type = 'IMAGE')
#     tex.image = bpy.data.images.load(realpath)
#     tex.use_alpha = True
 
#     # Create shadeless material and MTex
#     mat = bpy.data.materials.new('TexMat')
#     mat.use_shadeless = True
#     mtex = mat.texture_slots.add()
#     mtex.texture = tex
#     mtex.texture_coords = 'UV'
#     mtex.use_map_color_diffuse = True 
#     return mat

# Should get rid of all objects
for obj in bpy.context.scene.objects:
  bpy.context.scene.objects.unlink(obj)

# Convert the materials
for material in edm.node.materials:
  material.blender_material = create_material(material)
# materials = [create_material(x) for x in edm.node.materials]

for node in edm.renderNodes:
  if node.children:
    parent = bpy.data.objects.new(node.name, None)
    bpy.context.scene.objects.link(parent)
    for child in node.children:
      obj = create_object(child)
      obj.parent = parent
  else:
    obj = create_object(node)

# Convert all the connectors!
for connector in edm.connectors:
  obj = create_connector(connector)  


bpy.context.scene.update()
# create_materials(edm.renderNodes[0].material)

# code.interact(local={"edm": edm})


# import struct
# from collections import namedtuple
# import logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)



# MainIndex = namedtuple("MainIndex", ["name", "position"])

# def _read_index(data):
#   indexCount = data.read_uint()
#   print("index count: {}".format(indexCount))

#   # Read the index entries for this
#   def read_index_entry():
#     name = data.read_string()
#     idata = data.read_uint()
#     return MainIndex(name, idata)

#   index = [read_index_entry() for x in range(indexCount)]
#   return index

# def _print_index(index):
#   length = max(len(x.name) for x in index)
#   return "\n".join(["  {} = {}".format(x.name.ljust(length), x.position) for x in index])



# def read_vd_texturedef(stream):
#   def _read_textureblock(stream):
#     # logger.debug("Starting read at {}".format(stream.tell()))
#     stream.read_constant(struct.pack("<ii",0,-1))
#     name = stream.read_string()
#     stream.read_constant(struct.pack("<iiii", 2, 2, 10, 6))
#     # A matrix
#     matrix = stream.read_format("<16f")
#     return name

#   return stream.read_list(_read_textureblock)

# def read_vertex_definition(data):
#   vdProperties = {
#                 "BLENDING": data.read_uchar,
#                 "CULLING": data.read_uchar,
#                 "DEPTH_BIAS": data.read_uint, 
#                 "VERTEX_FORMAT": lambda : data.read_format("30B"),
#                 "TEXTURE_COORDINATES_CHANNELS": lambda : data.read_format("52B"),
#                 "MATERIAL_NAME": data.read_string,
#                 "NAME": data.read_string,
#                 "SHADOWS": data.read_uchar,
#                 "UNIFORMS": lambda : data.read_list(data.read_single_type),
#                 "ANIMATED_UNIFORMS": lambda : data.read_list(data.read_single_type),
#                 "TEXTURES": lambda : read_vd_texturedef(data),
#                 }

#   def _read_vdp(data):
#     name = data.read_string()
#     # logger.debug("reading {} at pos {}".format(name, data.tell()))
#     assert name in vdProperties
#     return (name, vdProperties[name]())

#   return {a: b for (a, b) in data.read_list(_read_vdp)}


# def _read_ArgPositionNode(data):
#   # print("APN at {}".format(data.tell()))
#   name = data.read_string()
#   # print("  Name: {}".format(name))
#   data.seek(256,1)
#   count = data.read_uint()
#   # print("  Count = {}".format(count))
#   # 32 bytes per entry, plus eight at end
#   data.seek(32*count + 8, 1)
#   # print("Node end at {}".format(data.tell()))
#   return name

# def dump_bytes(stream, length):
#   print("Data at {}".format(stream.tell()))
#   dump = stream.read(length)
#   fData = struct.unpack("<"+str(length//4)+"f", dump)
#   iData = struct.unpack("<"+str(length//4)+"I", dump)
#   for x, (f, i) in enumerate(zip(fData, iData)):
#     print("{:3}  {:25}  {:11}".format(x, f, i))
#   print("End of Data at {}".format(stream.tell()))
  

# def _read_ArgAnimationNode(data):
#   fixlen = {20526: 636, 22409: 596, 39604: 724}
#   # read_named_node(636)
#   name = data.read_string()

#   fullLen = fixlen[data.tell()]

#   # data.seek(107*4,1)
#   # count = data.read_uint()
#   # data.seek(4*(count*10+1), 1)
  
#   print("AAN Data at {}".format(data.tell()))
#   dump_bytes(data, fullLen)
#   # data.seek(fullLen, 1)
#   print("Data end at {}".format(data.tell()))
#   return name

# def _read_ArgRotationNode(data):
#   # fixLen = {17972: 388, 18405: 388, 18831: 388, 19260: 388, 21963: 388, 23031: 588, 23662: 348}
#   pos = data.tell()
#   # assert pos in fixLen
#   name = data.read_string()

#   data.seek(65*4,1)
#   count = data.read_uint()
#   data.seek((count*10 + 1)*4, 1)
#   # print("ARN Data at {} [length={}]".format(data.tell(), fixLen[pos]))
#   # dump_bytes(data, fixLen[pos])

#   return name

# def _read_ArgVisibilityNode(data):
#   name = data.read_string()
#   data.seek(36,1)
#   return name

# def read_named_node(length):
#   def _readNode(stream):
#     name = stream.read_string()
#     stream.seek(length,1)
#     return name
#   return _readNode

# def read_node(data):
#   FIXED_NODE_LENGTHS = {"model::Node": 12, "model::TransformNode": 140}
#   OTHER_NODE_LENGTHS = {
#     "model::ArgRotationNode": _read_ArgRotationNode, 
#     "model::ArgPositionNode": _read_ArgPositionNode,
#     "model::ArgAnimationNode": _read_ArgAnimationNode,
#     "model::ArgVisibilityNode": _read_ArgVisibilityNode}

#   position = data.tell()
#   nodetype = data.read_string()
#   print("Reading {} at {}".format(nodetype, position))
#   if nodetype in FIXED_NODE_LENGTHS:
#     data.seek(FIXED_NODE_LENGTHS[nodetype], 1)
#     return nodetype
#   elif nodetype in OTHER_NODE_LENGTHS:
#     nodeData = OTHER_NODE_LENGTHS[nodetype](data)
#     return (nodetype, nodeData)
#   else:
#     raise KeyError("Unknown node type at {}: {}".format(data.tell(), nodetype))


# @reads_type("model::RootNode")
# def read_root_node(data):
#   logger.debug("Reading RootNode")
#   description = data.read_string()
#   # Unknown 4-byte value; version? Is zero in known instance
#   data.seek(4, 1)
#   properties = data.read_list(data.read_single_type)

#   # BIGa chunk of unknown data here - of unknown length
#   data.seek(145,1)

#   # # Now an array of what looks like... vertex array information?
#   # matRefCount = data.read_uint()
#   # for x in range()
#   vertexDefs = data.read_list(read_vertex_definition)
#   logger.debug("Read {} vertex definition sets".format(len(vertexDefs)))

#   # Now, read what appears to be a node list.
#   # Next ints are 0 602 417 which could be counts. Assume first two are unrelated
#   # stream.seek(8,1)
#   # nodes = read_nodelist(stream)

#   # 0 602 417
#   # Node 0 0 0 [12]
#   # TransformNode [140]
#   data.seek(8,1)
#   nodes = data.read_list(read_node)





# class EDMFile(object):
#   def __init__(self, filename):
#     self.data = Reader(filename)
#     self.data.read_constant(b"EDM")
#     self.version = self.data.read_ushort()
#     logger.debug("Opened EDM file {}, version {}".format(filename, self.version))
#     # Read the basic file indices
#     self.index_A = _read_index(self.data)
#     self.index_B = _read_index(self.data)
#     logger.debug("First Index:\n{}".format(_print_index(self.index_A)))
#     logger.debug("Second Index:\n{}".format(_print_index(self.index_B)))

# file = EDMFile("Cockpit_Su-25T.EDM")

# nodeStart = file.data.tell()
# firstNode = file.data.read_single_type()
# # nodes = [x for x in file.data.read_single_type()]

# logger.debug("Length so far for node: {}".format(file.data.tell()-nodeStart))
# logger.info("End of reading; file position: {}".format(file.data.tell()))



# # def read_named_node(length):
# #   def _readNode(stream):
# #     name = read_str(stream)
# #     stream.seek(length,1)
# #     return name
# #   return _readNode

# # def read_nodelist(stream):
# #   # We don't know exactly how to interpret. Just store the (common? Lengths now)
# #   NODE_LENGTHS = {
# #     "model::Node": 12, "model::TransformNode": 140, "model::ArgRotationNode": read_named_node(388),
# #     "model::ArgPositionNode": read_named_node(364), "model::ArgAnimationNode": read_named_node(636),
# #     "model::ArgVisibilityNode:": read_named_node(36)
# #   }
# #   count = read_ui(stream)
# #   nodes = []
# #   for i in range(count):
# #     nodeType = read_str(stream)
# #     print("Reading node {} at {}".format(nodeType, stream.tell()))
# #     length = NODE_LENGTHS[nodeType]
# #     if callable(length):
# #       nodes.append({"type": nodeType, "data": length(stream)})
# #     else:
# #       stream.seek(length, 1)
# #       nodes.append(nodeType)

