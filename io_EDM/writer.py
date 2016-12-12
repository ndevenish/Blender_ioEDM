
import bpy

import itertools
import os
from .edm.types import *
from .edm.mathtypes import Matrix, vector_to_edm, matrix_to_edm, Vector, MatrixScale, matrix_to_blender
from .edm.basewriter import BaseWriter
from .utils import matrix_string, vector_string

from .translation import TranslationGraph, TranslationNode

def write_file(filename, options={}):

  # Get a set of all mesh objects to be exported as renderables
  renderables = {x for x in bpy.context.scene.objects if x.type == "MESH" and x.edm.is_renderable}
  print("Writing {} objects as renderables".format(len(renderables)))
  # Generate the materials for every renderable
  materials, materialMap = _create_material_map(renderables)  
  
  # Build a graph from ALL blender objects we want ported across
  graph = TranslationGraph.from_blender_objects(renderables)
  print("Blender graph we are exporting:")
  graph.print_tree()

  # For every object, create a parent transform node if it needs one
  # e.g. if it has animation this will be handled by a transform node
  #       If not, then it ends up being just a static mesh in the parent
  #       tranform frame, and so on until the root object - in which case the
  #       mesh will just be rendered static.
  graph.root.transform = Node()
  graph.walk_tree(_build_transform)

  # Create the basic rendernode structures
  def _create_renderNode(node):
    if node.blender and node.blender.edm.is_renderable:
      node.render = RenderNodeWriter(node.blender)
      node.render.material = materialMap[node.blender.material_slots[0].material.name]
    # If we have an ArgAnimationNode, don't apply the transformation
    if node.transform and isinstance(node.transform, ArgAnimationNode):
      node.apply_transform = False
    else:
      node.apply_transform = True
  graph.walk_tree(_create_renderNode)
  
  # Now set all the transform parents, both for blender objects AND transforms
  # RenderNodes get connected to their associated transform
  # Transform nodes get connected to the parent transform node
  def _connect_parents(node):
    if node.render and node.transform:
      node.render.parent = node.transform
    if node.transform and node.parent and node.parent.transform:
      node.transform.parent = node.parent.transform
  graph.walk_tree(_connect_parents)


  # Now dump a load of information on our calculated base transforms
  def _inspect_animarg(node, prefix):
    if not node.transform or not isinstance(node.transform, ArgAnimationNode):
      return
    node.transform.print_summary(prefix)
    
  print("Animation base transforms:")
  graph.print_tree(_inspect_animarg)

  # Now do enmeshing
  def _enmesh(node):
    if node.render:
      node.render.calculate_mesh(options)
  graph.walk_tree(_enmesh)

  # Build the linear list of transformation nodes and render nodes
  transformNodes = []
  renderNodes = []
  def _add_transforms(node):
    if node.render:
      renderNodes.append(node.render)
    if node.transform:
      if not node.transform in transformNodes:
        transformNodes.append(node.transform)
  graph.walk_tree(_add_transforms, include_root=True)

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


def _build_transform(node):
  """Given a translation node, creates the parent transform nodes for that 
  blender object. If more than one parent transform, takes care of stitching
  them into the end graph."""

  # Skip any nodes that are not JUST blender objects
  if not node.type == "BLEND":
    return
  transforms = build_parent_nodes(node.blender)
  if transforms:
    node.transform = transforms[-1]
    for parent in transforms[:-1]:
      parentNode = node.insert_parent()
      parentNode.transform = parent


def build_parent_nodes(obj):
  """Inspects an object's actions to build a parent transform node.
  Possibly returns a chain of nodes, as in cases of position/visibility
  these must be handled by separate nodes. The returned nodes (or none)
  must then be parented onto whatever parent nodes the objects parents
  posess. If no nodes are returned, then the object should have it's
  local transformation applied."""

  # If the object has no animation data, it is static and so just embedded
  if not obj.animation_data:
    return [create_animation_base(obj)]

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
    return [create_animation_base(obj)]

  # No multiple animations for now - get simple right first
  assert len(actions) <= 1, "Do not support multiple actions on object export at this time"
  action = next(iter(actions))

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
    # print("Creating ArgAnimationNode for {}".format(obj.name))
    nodes.append(create_arganimation_node(obj, [action]))
  return nodes

def create_animation_base(object):
  node = ArgAnimationNodeBuilder(name=object.name)

  # Build the base transforms.
  node.base.matrix = matrix_to_edm(object.matrix_parent_inverse)
  
  sM = MatrixScale(object.scale)
  rM = object.rotation_quaternion.to_matrix().to_4x4()
  tM = Matrix.Translation(object.location)
  # Verify this
  buildVec = object.matrix_parent_inverse * tM * rM * sM * Vector((1,1,1,1))
  localVec = object.matrix_local * Vector((1,1,1,1))
  delta = localVec - buildVec
  # print("Delta vector = {}".format(delta.length))
  if delta.length > 0.01:
    print("Incorrect local matrix calculation")
    import pdb
    pdb.set_trace()

  pos, rot, sca = object.matrix_basis.decompose()
  node.base.position = pos #object.location
  node.base.scale = sca #object.scale
  node.base.quat_1 = rot #object.rotation_quaternion

  # This swaps edm-space to blender space - rotate -ve around x 90 degrees
  RX = Quaternion((0.707, -0.707, 0, 0))
  RXm = RX.to_matrix().to_4x4()

  # ON THE OTHER SIDE
  # vector_to_blender - z = y, y = -z - positive rotation around X == RPX
  # actual data transformed is RPX * file
  # Base transform is reasonably standard;
  #
  #          ________________Direct values from node
  #         |     |      |
  # mat * aabT * q1m * aabS * [RX * RPX] * file
  # mat *   T  *  R  *  S         *        file
  # 
  # e.g. all transforms are applied in file-space

  # Calculate what we think that the importing script should see
  # zero_transform = matrix_to_blender(node.base.matrix) \
  #       * Matrix.Translation(node.base.position) \
  #       * node.base.quat_1.to_matrix().to_4x4() \
  #       * MatrixScale(node.base.scale) \
  #       * RXm
  # print("   Expected zeroth")
  # print("     Location: {}\n     Rotation: {}\n     Scale: {}".format(*zero_transform.decompose()))
  # This appears to match the no-rot case. What doesn't match is when rotations are applied

  return node

def create_arganimation_node(object, actions):
  # For now, let's assume single-action
  node = create_animation_base(object)

  # Secondary variables for calculation
  #  
  # This swaps blender space to EDM-space - rotate +ve around x 90 degrees
  RPX = Quaternion((0.707, 0.707, 0, 0))
  # This swaps edm-space to blender space - rotate -ve around x 90 degrees
  RX = Quaternion((0.707, -0.707, 0, 0))
  RXm = RX.to_matrix().to_4x4()
  inverse_base_rotation = node.base.quat_1.inverted()
  matQuat = matrix_to_blender(node.base.matrix).decompose()[1]
  invMatQuat = matQuat.inverted()

  assert len(actions) == 1
  for action in actions:
    curves = set(x.data_path for x in action.fcurves)
    rotCurves = [x for x in action.fcurves if x.data_path == "rotation_quaternion"]
    posCurves = [x for x in action.fcurves if x.data_path == "location"]
    argument = action.argument

    # What we should scale to - take the maximum keyframe value as '1.0'
    scale = 1.0 / (max(abs(x) for x in get_all_keyframe_times(posCurves + rotCurves)) or 100.0)
    
    if "location" in curves:
      # Build up a set of keys
      posKeys = []
      # Build up the key data for everything
      for time in get_all_keyframe_times(posCurves):
        position = get_fcurve_position(posCurves, time, node.base.position) - node.base.position
        key = PositionKey(frame=time*scale, value=position)
        posKeys.append(key)
      node.posData.append((argument, posKeys))
    if "rotation_quaternion" in curves:
      rotKeys = []
      for time in get_all_keyframe_times(rotCurves):
        actual = get_fcurve_quaternion(rotCurves, time)
        rotation = inverse_base_rotation * invMatQuat * actual
        key = RotationKey(frame=time*scale, value=rotation)
        rotKeys.append(key)

# leftRotation = matQuat * q1
#     rightRotation = RX
        # Extra RX because the vertex data on reading has had an extra
        # RPX rotation applied
        # predict = matQuat * node.base.quat_1 * rotation * RPX 
        # print("   Quat at time {:6}: {}".format(time, predict))
        # print("                Desired {}".format(actual))
      node.rotData.append((argument, rotKeys))
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

def get_fcurve_position(fcurves, frame, basis=None):
  """Retrieve an evaluated fcurve for position"""
  all_quat = [x for x in fcurves if x.data_path == "location"]
  channelL = [[x for x in all_quat if x.array_index == index] for index in range(3)]
  # Get an array of lookups to get the channel value, or zero
  channels = []
  for index in range(3):
    if channelL[index]:
      channels.append(channelL[index][0].evaluate(frame))
    elif basis:
      channels.append(basis[index])
    else:
      channels.append(0)
  return Vector(channels)

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

  # Convert material 'hardness' to a specular power-like value
  specPower = (float(source.specular_hardness) - 1.0) / 100.0
  mat.uniforms = {
    "specPower": specPower,
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
    print("ERROR: Can not find diffuse texture")
  # normalTex = [x for x in source.texture_slots if x.use_map_normal]
  # specularTex = [x for x in source.texture_slots if x.use_map_specular]

  assert len(diffuseTex) == 1
  mat.textures.append(create_texture(diffuseTex[0]))

  return mat

def create_mesh_data(source, material, options={}):
  """Takes an object and converts it to a mesh suitable for writing"""
  # Always remesh, because we will want to apply transformations
  mesh = source.to_mesh(bpy.context.scene,
    apply_modifiers=options.get("apply_modifiers", False),
    settings="RENDER", calc_tessface=True)

  print("Enmeshing ", source.name)
  # Apply the local transform. IF there are no parents, then this should
  # be identical to the world transform anyway
  if options.get("apply_transform", True):
    mesh.transform(source.matrix_local)
    print("  Applying local transform")
  else:
    print("  Skipping transform application")

  # Should be more complicated for multiple layers, but will do for now
  uv_tex = mesh.tessface_uv_textures.active.data

  if options.get("convert_axis", True):
    print("  Converting axis")
  else:
    print("  NOT Converting axis")
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
    self.parent = None
    # An additional transform to apply to our local space to transform
    # ourselves through any static parent spaces (to the next edm 
    # tranformation node)
    self.additional_transform = Matrix()
    self.apply_transform = False

  def calculate_mesh(self, options):
    assert self.material
    assert self.source
    opt = dict(options)
    # If we have any kind of parent (OTHER than an ArgVisibilityNode), then 
    # we don't want to apply transformations
    opt["apply_transform"] = self.apply_transform
    # ArgAnimationNode-based parents don't have axis-shifted data
    opt["convert_axis"] = self.apply_transform #not isinstance(self.parent, ArgAnimationNode)
    self.vertexData, self.indexData = create_mesh_data(self.source, self.material, opt)

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

class ArgAnimationNodeBuilder(ArgAnimationNode):
  def __init__(self, *args, **kwargs):
    super(ArgAnimationNodeBuilder, self).__init__(*args, **kwargs)

  def apply_transform(self, matrix):
    """Apply an extra transformation to the local space of this 
    transform node. This is because of parenting issues"""
    raise NotImplementedError()

  def print_summary(self, prefix=""):
    print(prefix + "Base (pre-animation) data:")
    print(prefix + "Position:", vector_string(self.base.position))
    print(prefix + "Rotation:", vector_string(self.base.quat_1))
    print(prefix + "Scale:   ", vector_string(self.base.scale))
    print(matrix_string(self.base.matrix, prefix=prefix, title="Matrix:  "))

    # Calculate what the decomposed values will be
    RX = Quaternion((0.707, -0.707, 0, 0))
    RXm = RX.to_matrix().to_4x4()
    zeroth =  matrix_to_blender(self.base.matrix) * \
              Matrix.Translation(self.base.position) * \
              self.base.quat_1.to_matrix().to_4x4() * \
              MatrixScale(self.base.scale) * RXm
    zPos, zRot, zSca = zeroth.decompose()
    print(prefix + "Expected Zeroth Pos:", vector_string(zPos))
    print(prefix + "                Rot:", vector_string(zRot))
    print(prefix + "              Scale:", vector_string(zSca))
    
    if self.rotData:
      print(prefix + "  Rotation Anim Data:")
      for key in self.rotData[0][1]:
        print(prefix + "    {:-6.3f}: {}".format(key.frame, key.value))
