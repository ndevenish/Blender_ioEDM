"""
reader

Contains the central EDM->Blender conversion code
"""

import bpy
import bmesh

from .utils import chdir
from .edm import EDMFile
from .edm.mathtypes import *
from .edm.types import (AnimatingNode, ArgAnimationNode,
  ArgRotationNode, ArgPositionNode, ArgVisibilityNode)

import re
import glob
import fnmatch
import os

def read_file(filename):
  # Parse the EDM file
  edm = EDMFile(filename)
  edm.postprocess()

  # Convert the materials. These will be used by objects
  # We need to change the directory as the material searcher
  # currently uses the cwd
  with chdir(os.path.dirname(os.path.abspath(filename))):
    for material in edm.root.materials:
      material.blender_material = create_material(material)

  # Convert all the connectors!
  for connector in edm.connectors:
    obj = create_connector(connector)  

  # Go through all render nodes, and children
  for node in edm.renderNodes:
    # If a node has children, parent an empty to them all
    if node.children:
      parent = bpy.data.objects.new(node.name, None)
      bpy.context.scene.objects.link(parent)
      for child in node.children:
        obj = create_object(child)
        obj.parent = parent
    else:
      obj = create_object(node)

  # Update the scene
  bpy.context.scene.update()


def create_visibility_actions(visNode):
  """Creates visibility actions from an ArgVisibilityNode"""
  actions = []
  for (arg, ranges) in visNode.visData:
    # Creates a visibility animation track
    action = bpy.data.actions.new("Visibility_{}".format(arg))
    actions.append(action)
    action.argument = arg
    # Create f-curves for hide_render
    curve = action.fcurves.new(data_path="hide_render")
    # Probably need an extra keyframe to specify start visibility
    if ranges[0][0] >= -0.995:
      curve.keyframe_points.add()
      curve.keyframe_points[0].co = (-100, 1.0)
      curve.keyframe_points[0].interpolation = 'CONSTANT'
    # Create the keyframe data
    for (start, end) in ranges:
      frameStart = int(start*100)
      frameEnd = 100 if end > 1.0 else int(end*100)
      curve.keyframe_points.add()
      key = curve.keyframe_points[-1]
      key.co = (frameStart, 0.0)
      key.interpolation = 'CONSTANT'
      if frameEnd < 100:
        curve.keyframe_points.add()
        key = curve.keyframe_points[-1]
        key.co = (frameEnd, 1.0)
        key.interpolation = 'CONSTANT'
  return actions

def add_position_fcurves(action, keys, transform_left, transform_right):
  "Adds position fcurve data to an animation action"
  frameScale = 100. / max(abs(x.frame) for x in keys)
  # Create an fcurve for every component  
  curves = []
  for i in range(3):
    curve = action.fcurves.new(data_path="location", index=i)
    curves.append(curve)

  # Loop over every keyframe in this animation
  for framedata in keys:
    frame = int(frameScale*framedata.frame)
    
    # Calculate the rotation transformation
    newPosMat = transform_left * Matrix.Translation(framedata.value) * transform_right
    newPos = newPosMat.decompose()[0]

    for curve, component in zip(curves, newPos):
      curve.keyframe_points.add()
      curve.keyframe_points[-1] = (frame, component)
      curve.keyframe_points[-1].interpolation = 'LINEAR'

def add_rotation_fcurves(action, keys, transform_left, transform_right):
  "Adds rotation fcurve action to an animation action"
  frameScale = 100. / max(abs(x.frame) for x in keys)
  
  # Create an fcurve for every component  
  curves = []
  for i in range(4):
    curve = action.fcurves.new(data_path="rotation_quaternion", index=i)
    curves.append(curve)

  # Loop over every keyframe in this animation
  for framedata in keys:
    frame = int(frameScale*framedata.frame)
    
    # Calculate the rotation transformation
    newRot = transform_left * framedata.value * transform_right

    for curve, component in zip(curves, newRot):
      curve.keyframe_points.add()
      curve.keyframe_points[-1] = (frame, component)
      curve.keyframe_points[-1].interpolation = 'LINEAR'

def create_arganimation_actions(node):
  "Creates a set of actions to represent an ArgAnimationNode"
  actions = []

  # Calculate the base transform data for the node

  # Rotation quaternion for rotating -90 degrees around the X
  # axis. It seems animation data is not transformed into the
  # DCS world space automatically, and so we need to 'undo' the
  # transformation that was initially applied to the vertices when
  # reading into blender.
  RX = Quaternion((0.707, -0.707, 0, 0))
  RXm = RX.to_matrix().to_4x4()

  # Work out the transformation chain for this object
  aabS = MatrixScale(node.base.scale)
  aabT = Matrix.Translation(node.base.position)
  q1  = node.base.quat_1
  q2  = node.base.quat_2
  q1m = q1.to_matrix().to_4x4()
  q2m = q2.to_matrix().to_4x4()
  mat = node.base.matrix

  # Calculate the transform matrix quaternion part for pure rotations
  matQuat = matrix_to_blender(mat).decompose()[1]

  # With:
  #   aabT = Matrix.Translation(argNode.base.position)
  #   aabS = argNode.base.scale as a Scale Matrix
  #   q1m  = argNode.base.quat_1 as a Matrix (e.g. fixQuat1)
  #   q2m  = argNode.base.quat_2 as a Matrix (e.g. fixQuat2)
  #   mat  = argNode.base.matrix
  #   m2b  = matrix_to_blender e.g. swapping Z -> -Y

  # Initial tests had supposed that the transformation was:
  #    baseTransform = aabT * q1m * q2m * aabS * mat
  # However the correct partial transform for e.g. kpp_baraban_0 is the following
  #    C.object.location = (m2b(mat)*aabT*q1m).decompose()[0]
  # For which case where q2m, aabS are identity. Need more verification from
  # other items. Still confused as to why axis swapping doesn't always work?  
  #
  # For stick_base_1 the scale-expanded:
  #     loc, scale <<= m2b(mat) * aabT * q1m * aabS
  # works, however rotation is off by 90 degrees in y
  # 
  # For Cylinder55_13 with RXm as a rotation -90 degrees in X,
  # and Ar as the rotation from animation:
  # 
  #   l, r, s <<= m2b(mat) * aabT * q1m * Ar * aabS * RXm
  #
  # Wondering if animation vertex data is unshifted in coordinate
  # space, and so the correction when importing needs to be
  # uncorrected when applying rotations

  # Save the 'null' transform onto the node, because we will need to
  # apply it to any object using this node's animation. This is independant
  # of any argument-based animation
  # baseTransform = aabT * q1m * q2m * aabS * mat
  node.zero_transform = matrix_to_blender(mat) * aabT * q1m * aabS * RXm
  # ob.location, ob.rotation_quaternion, ob.scale = baseTransform.decompose()

  # Split a single node into separate actions based on the argument
  for arg in node.get_all_args():
    # Filter the animation data for this node to just this action
    posData = [x for x in node.posData if x[0] == arg]
    rotData = [x for x in node.rotData if x[0] == arg]
    scaleData = [x for x in node.scaleData if x[0] == arg]
    # Create the action
    action = bpy.data.actions.new("AnimationArg{}".format(arg))
    actions.append(action)
    action.argument = arg
    
    # Calculate the pre and post-animation-value transforms
    leftRotation = matQuat * q1
    rightRotation = RX
    # At the moment, we don't understand the position transform
    prePosition = Matrix()
    postPosition = Matrix()


    # Build the f-curves for the action
    for pos in posData:
      add_position_fcurves(action, posData, leftPosition, rightPosition)
    for rot in rotData:
      add_rotation_fcurves(action, rotData, leftRotation, rightRotation)
  # Return these new actions
  return actions


def create_actions_for_node(node):
  """Accepts a node and creates actions to apply their animations"""
  
  # Don't do this twice
  if hasattr(node, "actions") and node.actions:
    actions = node.actions
  else:
    if isinstance(node, ArgVisibilityNode):
      actions = create_visibility_actions(node)
    if isinstance(node, ArgAnimationNode):
      actions = create_arganimation_actions(node)
    # Save these actions on the node
    node.actions = actions

  # For now, only use the first action until we are doing NLA stuff
  if len(actions) > 1:
    print("WARNING: More than one action generated by node, but not yet implemented")
  return actions[0]



def _find_texture_file(name):
  """
  Searches for a texture file given a basename without extension.

  The current working directory will be searched, as will any
  subdirectories called "textures/", for any file starting with the
  designated name '{name}.'
  """
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
  return os.path.abspath(textureFilename)

def create_material(material):
  """Create a blender material from an EDM one"""
  # Find the actual file for the texture name
  if len(material.textures) == 0:
    return None

  diffuse_texture = next(x for x in material.textures if x.index == 0)

  name = diffuse_texture.name
  filename = _find_texture_file(name)
  tex = bpy.data.textures.new(name, type="IMAGE")
  if filename:
    tex.image = bpy.data.images.load(filename)
    tex.image.use_alpha = False

  # Create material
  mat = bpy.data.materials.new(material.name)
  mat.use_shadeless = True
  mat.edm_material = material.material_name
  mat.edm_blending = str(material.blending)
  mat.use_cast_shadows_only = material.shadows.cast_only
  mat.use_shadows = material.shadows.receive
  mat.use_cast_shadows = material.shadows.cast
  # Read uniform values
  mat.diffuse_intensity = material.uniforms.get("diffuseValue", 1.0)
  mat.specular_intensity = material.uniforms.get("specFactor", mat.specular_intensity)
  mat.specular_hardness = material.uniforms.get("specPower", mat.specular_hardness)
  reflection = material.uniforms.get("reflectionValue", 0.0)
  if reflection > 0.0:
    mat.raytrace_mirror.use = True
    mat.raytrace_mirror.reflect_factor = reflection
    mat.raytrace_mirror.gloss_factor = 1 - material.uniforms.get("reflectionBlurring")

  mtex = mat.texture_slots.add()
  mtex.texture = tex
  mtex.texture_coords = "UV"
  mtex.use_map_color_diffuse = True

  return mat


def create_connector(connector):
  """Create an empty object representing a connector"""
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

  bpy.context.scene.objects.link(ob)


def create_object(renderNode):
  """Does most of the work creating a blender object from a renderNode"""

  # We need to reduce the vertex set to match the index set
  all_index = sorted(list(set(renderNode.indexData)))
  new_vertices = [renderNode.vertexData[x] for x in all_index]
  # new_indices = [i for i, _ in enumerate(all_index)]
  indexMap = {idx: i for i, idx in enumerate(all_index)}
  new_indices = [indexMap[x] for x in renderNode.indexData]
  # Make sure we have the right number of indices...
  assert len(new_indices) % 3 == 0


  bm = bmesh.new()

  # Extract where the indices are
  posIndex = renderNode.material.vertex_format.position_indices
  normIndex = renderNode.material.vertex_format.normal_indices
  # Create the BMesh vertices, optionally with normals
  for i, vtx in enumerate(new_vertices):
    pos = vector_to_blender(Vector(vtx[x] for x in posIndex))
    vert = bm.verts.new(pos)
    if normIndex:
      vert.normal = vector_to_blender(Vector(vtx[x] for x in normIndex))

  bm.verts.ensure_lookup_table()

  # Prepare for texture information
  uvIndex = renderNode.material.vertex_format.texture_indices
  if uvIndex:
    # Ensure a UV layer exists before creating faces
    uv_layer = bm.loops.layers.uv.verify()
    bm.faces.layers.tex.verify()  # currently blender needs both layers.
  
  # Generate faces, with texture coordinate information
  for face in [new_indices[i:i+3] for i in range(0, len(new_indices), 3)]:
  # for face, uvs in zip(indexData, uvData):
    try:
      f = bm.faces.new([bm.verts[i] for i in face])
      # Add UV data if we have any
      if uvIndex:
        uvData = [[new_vertices[x][y] for y in uvIndex] for x in face]
        for loop, uv in zip(f.loops, uvData):
          loop[uv_layer].uv = (uv[0], -uv[1])
    except ValueError as e:
      print("Error: {}".format(e))

  # Put the mesh data into the scene
  mesh = bpy.data.meshes.new(renderNode.name)
  bm.to_mesh(mesh)
  mesh.update()
  ob = bpy.data.objects.new(renderNode.name, mesh)
  ob.data.materials.append(renderNode.material.blender_material)

  # Handle application of any direct animations
  ob.rotation_mode = "QUATERNION"
  if isinstance(renderNode.parent, AnimatingNode):
    ob.animation_data_create()
    # Get or create actions
    actions = create_actions_for_node(renderNode.parent)
    # This will go away eventually, but for now should be tested in sub function
    assert len(actions) == 1
    # Set the basis position
    ob.location, ob.rotation_quaternion, ob.scale = renderNode.parent.zero_transform.decompose()
    ob.animation_data.action = actions[0]

  # import pdb
  # pdb.set_trace()
  bpy.context.scene.objects.link(ob)

  return ob

