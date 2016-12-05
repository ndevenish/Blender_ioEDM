
import bpy

import itertools
import os
from .edm.types import *
from .edm.mathtypes import Matrix, vector_to_edm, matrix_to_edm, Vector
from .edm.basewriter import BaseWriter

def write_file(filename, options={}):

  # Get a list of all mesh objects to be exported as renderables
  renderables = [x for x in bpy.context.scene.objects if x.type == "MESH" and x.edm.is_renderable]
  materials, materialMap = _create_material_map(renderables)  

  # Now, build each RenderNode object, with it's parents
  renderNodes = []
  rootNode = Node()
  transformNodes = [rootNode]
  for obj in [x for x in renderables]:
    node = RenderNodeWriter(obj)
    node.material = materialMap[obj.material_slots[0].material.name]
    # Calculate the parents for this node's animation
    parents = node.calculate_parents()
    for parent in parents:
      parent.index = len(transformNodes)
      transformNodes.append(parent)
    # We now have the information to properly enmesh the object
    node.calculate_mesh(options)
    # And, prepare references for writing
    node.convert_references_to_index()
    renderNodes.append(node)

  # Materials:    √
  # Render Nodes: √
  # Parents:      √
  # Let's build the root node
  root = RootNodeWriter()
  root.set_bounding_box_from(renderables)
  root.materials = materials
  
  # And finally the wrapper
  file = EDMFile()
  file.root = root
  file.nodes = transformNodes
  file.renderNodes = renderNodes

  writer = BaseWriter(filename)
  file.write(writer)
  writer.close()


def _create_material_map(blender_objects):
  """Creates an list, and indexed material map from a list of blender objects.
  The map will connect material names to the edm-Material instance.
  In addition, each Material instance will know it's own .index"""
  
  all_Materials = [obj.material_slots[0].material for obj in blender_objects]
  materialMap = {m.name: create_material(m) for m in all_Materials}
  materials = []
  for i, bMat in enumerate(all_Materials):
    mat = materialMap[bMat.name]
    mat.index = i
    materials.append(mat)
  return materials, materialMap


def build_parent_nodes(obj):
  """Inspects an object's actions to build a parent transform node.
  Possibly returns a chain of nodes, as in cases of position/visibility
  these must be handled by separate nodes. The returned nodes (or none)
  must then be parented onto whatever parent nodes the objects parents
  posess. If no nodes are returned, then the object should have it's
  local transformation applied."""

  # Collect all actions for this object
  if not obj.animation_data:
    return []
  actions = set()
  if obj.animation_data.action and obj.animation_data.action.argument != -1:
    actions.add(obj.animation_data.action)
  for track in obj.animation_data.nla_tracks:
    for strip in track.strips:
      if strip.action.argument != -1:
        actions.add(strip.action)
  # Verify each action handles a separate argument, otherwise - who knows -
  # if this becomes a problem we may need to merge actions (ouch)
  arguments = set()
  for action in actions:
    if action.argument in arguments:
      raise RuntimeError("More than one action on an object share arguments. Not sure how to deal with this")
    arguments.add(action.argument)
  if not actions:
    return []
  # No multiple animations for now - get simple right first
  assert len(actions) <= 1, "Do not support multiple actions on object export at this time"
  action = next(iter(actions))

    
  import pdb
  pdb.set_trace()
  
  nodes = []

  # All keyframe types we know how to handle
  ALL_KNOWN = {"location", "rotation_quaternion", "scale", "hide_render"}
  # Keyframe types that are handled by ArgAnimationNode
  AAN_KNOWN = {"location", "rotation_quaternion", "scale"}

  data_categories = set(x.data_path for x in action.fcurves)
  if not data_categories <= ALL_KNOWN:
    print("WARNING: Action has animated keys ({}) that ioEDM can not translate yet!".format(data_categories-ALL_KNOWN))
  # do we need to make an ArgAnimationNode?
  if data_categories & {"location", "rotation_quaternion", "scale"}:
    print("Creating ArgAnimationNode")
    nodes.append(create_arganimation_node(obj, [action]))
  return nodes



def create_arganimation_node(object, actions):
  # For now, let's assume single-action
  import pdb
  pdb.set_trace()
  node = ArgAnimationNode()
  assert len(actions) == 1
  for action in actions:
    curves = set(x.data_path for x in action.fcurves)
    rotCurves = [x for x in action.fcurves if x.data_path == "rotation_quaternion"]
    posCurves = [x for x in action.fcurves if x.data_path == "location"]
    argument = action.argument

    # Firstly, we need to decompose the current transform so that the 
    # animation arguments are all applied corrently

    # Build the 

    if "location" in curves:
      # Build up a set of keys
      posKeys = []
      for time in get_all_keyframe_times(posCurves):
        position = get_fcurve_position(posCurves, time)
        key = PositionKey(frame=time, value=position)
        posKeys.append(key)
      node.posData.append((argument, posKeys))
    if "rotation_quaternion" in curves:
      raise NotImplementedError()
    if "scale" in curves:
      raise NotImplementedError("Curves not totally understood yet")

  # Now we've processed everything
  return node


def get_all_keyframe_times(fcurves):
  """Get all fixed-point times in a collection of keyframes"""
  times = set()
  for curve in fcurves:
    for keyframe in curve.keyframe_points:
      times.add(keyframe.co[0])
  return sorted(times)

def get_fcurve_quaternion(fcurves, frame):
  """Retrieve an evaluated quaternion for a single action at a single frame"""
  # Get each channel for the quaternion
  all_quat = [x for x in fcurves if x.data_path == "rotation_quaternion"]
  # Really, quaternion rotation without all channels is stupid
  assert len(all_quat) == 4, "Incomplete quaternion rotation channels in action"
  channels = [[x for x in all_quat if x.array_index == index][0] for index in range(4)]
  return Quaternion([channels[i].evaluate(frame) for i in range(4)])

def get_fcurve_position(fcurves, frame):
  """Retrieve an evaluated fcurve for position"""
  all_quat = [x for x in fcurves if x.data_path == "location"]
  channelL = [[x for x in all_quat if x.array_index == index] for index in range(3)]
  # Get an array of lookups to get the channel value, or zero
  channels = [(x[0].evaluate if x else lambda x: 0) for i, x in enumerate(channelL)]
  return Vector([channels[i](frame) for i in range(3)])

def calculate_edm_world_bounds(objects):
  """Calculates, in EDM-space, the bounding box of all objects"""
  mins = [1e38, 1e38, 1e38]
  maxs = [-1e38, -1e38, -1e38]
  for obj in objects:
    points = [vector_to_edm(obj.matrix_world * Vector(x)) for x in obj.bound_box]
    for index in range(3):
      mins[index] = min([point[index] for point in points] + [mins[index]])
      maxs[index] = max([point[index] for point in points] + [maxs[index]])
  return Vector(mins), Vector(maxs)

def create_texture(source):
  # Get the texture name stripped of ALL extensions
  texName = os.path.basename(source.texture.image.filepath)
  texName = texName[:texName.find(".")]
  
  # Work out the channel for this texture
  if source.use_map_color_diffuse:
    index = 0
  elif source.use_map_normal:
    index = 1
  elif source.use_map_specular:
    index = 2

  # For now, assume identity transformation until we understand
  matrix = Matrix()
  return Texture(index=index, name=texName, matrix=matrix)

def create_material(source):
  mat = Material()
  mat.blending = int(source.edm_blending)
  mat.material_name = source.edm_material
  mat.name = source.name
  mat.uniforms = {
    "specPower": float(source.specular_hardness), # Important this is a float
    "specFactor": source.specular_intensity,
    "diffuseValue": source.diffuse_intensity,
    "reflectionValue": 0.0, # Always in uniforms, so keep here for compatibility
  }
  # No ide what this corresponds to yet:
  # "diffuseShift": Vector((0,0)),
  if source.raytrace_mirror.use:
    mat.uniforms["reflectionValue"] = source.raytrace_mirror.reflect_factor
    mat.uniforms["reflectionBlurring"] = 1.0-source.raytrace_mirror.gloss_factor
  mat.shadows.recieve = source.use_shadows
  mat.shadows.cast = source.use_cast_shadows
  mat.shadows.cast_only = source.use_cast_shadows_only

  mat.vertex_format = VertexFormat({
    "position": 4,
    "normal": 3,
    "tex0": 2
    })
  
  mat.texture_coordinates_channels = [0] + [-1]*11
  # Find the textures for each of the layers
  # Find diffuse - this will sometimes also include a translucency map
  try:
    diffuseTex = [x for x in source.texture_slots if x is not None and x.use_map_color_diffuse]
  except:
    import pdb
    pdb.set_trace()
  # normalTex = [x for x in source.texture_slots if x.use_map_normal]
  # specularTex = [x for x in source.texture_slots if x.use_map_specular]

  assert len(diffuseTex) == 1
  mat.textures.append(create_texture(diffuseTex[0]))

  return mat

def create_mesh_data(source, material, options={}):
  # Always remesh, because we will want to apply transformations
  mesh = source.to_mesh(bpy.context.scene,
    apply_modifiers=options.get("apply_modifiers", False),
    settings="RENDER", calc_tessface=True)

  # Apply the local transform. IF there are no parents, then this should
  # be identical to the world transform anyway
  if options.get("apply_transform", True):
    mesh.transform(source.matrix_local)

  # Should be more complicated for multiple layers, but will do for now
  uv_tex = mesh.tessface_uv_textures.active.data

  newVertices = []
  newIndexValues = []
  # Loop over every face, and the UV data for that face
  for face, uvFace in zip(mesh.tessfaces, uv_tex):
    # What are the new index values going to be?
    newFaceIndex = [len(newVertices)+x for x in range(len(face.vertices))]
    # Build the new vertex data
    for i, vtxIndex in enumerate(face.vertices):
      if options.get("convert_axis", True):
        position = vector_to_edm(mesh.vertices[vtxIndex].co)
        normal = vector_to_edm(mesh.vertices[vtxIndex].normal)
      else:
        position = mesh.vertices[vtxIndex].co
        normal = mesh.vertices[vtxIndex].normal
      uv = [uvFace.uv[i][0], -uvFace.uv[i][1]]
      newVertices.append(tuple(itertools.chain(position, [0], normal, uv)))

    # We either have triangles or quads. Split into triangles, based on the
    # vertex index subindex in face.vertices
    if len(face.vertices) == 3:
      triangles =  ((0, 1, 2),)
    else:
      triangles = ((0, 1, 2),(2, 3, 0))

    # Write each vertex of each triangle
    for tri in triangles:
      for i in tri:
        newIndexValues.append(newFaceIndex[i])

  # Cleanup
  bpy.data.meshes.remove(mesh)

  return newVertices, newIndexValues

class RenderNodeWriter(RenderNode):
  def __init__(self, obj):
    super(RenderNodeWriter, self).__init__(name=obj.name)
    self.source = obj

  def calculate_parents(self):
    """Calculate parent objects, assign, and then return them"""
    parents = build_parent_nodes(self.source)
    if parents:
      self.parent = parents[-1]
    return parents

  def calculate_mesh(self, options):
    assert self.material
    assert self.source
    opt = dict(options)
    # If we have any kind of parent (OTHER than an ArgVisibilityNode), then 
    # we don't want to apply transformations
    opt["apply_transform"] = self.parent == None or isinstance(self.parent, ArgVisibilityNode)
    # ArgAnimationNode-based parents don't have axis-shifted data
    opt["convert_axis"] = not isinstance(self.parent, ArgAnimationNode)
    self.vertexData, self.indexData = create_mesh_data(self.source, self.material, options)

  def convert_references_to_index(self):
    """Convert all stored references into their index equivalent"""
    self.material = self.material.index
    if not self.parent:
      self.parent = 0
    else:
      self.parent = self.parent.index

class RootNodeWriter(RootNode):
  def __init__(self, *args, **kwargs):
    super(RootNodeWriter, self).__init__(*args, **kwargs)

  def set_bounding_box_from(self, objectList):
    bboxmin, bboxmax = calculate_edm_world_bounds(objectList)
    self.boundingBoxMin = bboxmin
    self.boundingBoxMax = bboxmax
