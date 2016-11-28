

# from .typereader import Property, allow_properties, reads_type
# from collections import namedtuple

from .typereader import reads_type, readMatrixf, readMatrixd, readQuaternion, readVec3d, readVec3f, readVec2f
from .typereader import get_type_reader as _tr_get_type_reader
from .basereader import BaseReader

from collections import namedtuple, OrderedDict, Counter
import struct

from .mathtypes import Vector, sequence_to_matrix

from abc import ABC

# VertexFormat = namedtuple("VertexFormat", ["position", "normal", "texture"])
Texture = namedtuple("Texture", ["unknownA", "name", "unknownB", "matrix"])

class AnimatingNode(ABC):
  """Abstract base class for all nodes that animate the object"""

class VertexFormat(object):
  def __init__(self, position, normal, texture):
    self.nposition = position
    self.nnormal = normal
    self.ntexture = texture

  @property
  def position_indices(self):
    return [0,1,2]

  @property
  def normal_indices(self):
    return list(range(self.nposition, self.nposition+self.nnormal))

  @property
  def texture_indices(self):
    return list(range(self.nposition+self.nnormal, self.nposition+self.nnormal+self.ntexture))


class TrackingReader(BaseReader):
  def __init__(self, *args, **kwargs):
    self.typecount = Counter()
    self.autoTypeCount = Counter()
    super(TrackingReader, self).__init__(*args, **kwargs)

  def mark_type_read(self, name, amount=1):
    self.typecount[name] += amount

def get_type_reader(name):
  _readfun = _tr_get_type_reader(name)
  def _reader(reader):
    reader.typecount[name] += 1
    return _readfun(reader)
  return _reader

def read_named_type(reader):
  """Reads a typename, and then reads the type named"""
  typename = reader.read_string()
  # reader.typecount[typename] += 1
  # reader.autoTypeCount[typename] += 1
  try:
    return get_type_reader(typename)(reader)
  except KeyError:
    print("Error at position {}".format(reader.tell()))
    raise

def read_string_uint_dict(stream):
  """Reads a dictionary of type String : uint"""
  length = stream.read_uint()
  data = OrderedDict()
  for _ in range(length):
    key = stream.read_string()
    value = stream.read_uint()
    data[key] = value
  return data


def read_propertyset(stream):
  """Reads a typed list of properties and returns as an ordered dict"""
  data = read_raw_propertiesset(stream)
  if data:
    stream.mark_type_read("model::PropertiesSet")
  return data


def read_raw_propertiesset(stream):
  # Read the potential Propertiesset-like dictionary
  length = stream.read_uint()
  data = OrderedDict()
  for _ in range(length):
    prop = read_named_type(stream)
    if hasattr(prop, "keys"):
      data[prop.name] = prop.keys
    else:
      data[prop.name] = prop.value
  return data

class EDMFile(object):
  def __init__(self, filename):
    reader = TrackingReader(filename)
    try:
      self._read(reader)
    except:
      print("ERROR at {}".format(reader.tell()))
      raise

  def _read(self, reader):
    reader.read_constant(b'EDM')
    self.version = reader.read_ushort()
    assert self.version == 8, "Unexpected .EDM file version"
    # Read the two indexes
    self.indexA = read_string_uint_dict(reader)
    self.indexB = read_string_uint_dict(reader)
    self.node = read_named_type(reader)
    assert reader.read_int() == -1

    # Read the object list once we find it
    def read_object_list(reader, count, name):
      """Reads an object list having already read the first name and count"""
      objects = {}
      for i in range(count):
        if i > 0:
          name = reader.read_string()
        objects[name] = reader.read_list(read_named_type)
      return objects

    # Ends with <count> <10> "CONNECTORS"
    # or                <12> "RENDER_NODES"
    # So, search keeping last 20 bytes until we find one of the above
    preObjPos = reader.tell()
    objects = {}
    possible_entries = [b"CONNECTORS", b"RENDER_NODES", b"SHELL_NODES", b"LIGHT_NODES"]
    possible_entries = sorted(possible_entries, key=lambda x: len(x))
    
    data = reader.read(min(len(x) for x in possible_entries)+8)
    maxLen = max(len(x) for x in possible_entries)+8
    unfound = True
    while unfound:
      for entry in possible_entries:
        if data[-len(entry):] == entry:
          objPos = reader.tell()-8-len(entry)
          print("Found object list at {}, gap size = {}".format(objPos, objPos-preObjPos))
          objCount = struct.unpack("<I", data[-len(entry)-8:-len(entry)-4])[0]
          # print("objects: {}".format(objCount))
          unfound = False
          objects = read_object_list(reader, objCount, entry.decode("utf-8"))
          break
      if unfound:
        data = data + reader.read(1)
        if len(data) > maxLen:
          data = data[-maxLen:]

    # Validate against the index
    rems = Counter(self.indexA)
    rems.subtract(Counter({x: c for (x,c) in reader.typecount.items() if x in self.indexA}))
    for k in [x for x in rems.keys() if rems[x] == 0]:
      del rems[k]

    if rems:
      print("IndexA items remaining before RENDER_NODES/CONNECTORS: {}".format(rems))
    cB = Counter({x: c for (x,c) in reader.typecount.items() if x in self.indexB})
    remBs = Counter(self.indexB)
    remBs.subtract(cB)
    for k in [x for x in remBs.keys() if remBs[x] == 0]:
      del remBs[k]
    if remBs:
      print("IndexB items remaining before RENDER_NODES/CONNECTORS: {}".format(remBs))

    # Make sure all objects are identified
    assert all(x.encode("utf-8") in possible_entries for x in objects.keys())    
    self.connectors = objects.get("CONNECTORS", [])
    self.renderNodes = objects.get("RENDER_NODES", [])
    self.shellNodes = objects.get("SHELL_NODES", [])
    self.lightNodes = objects.get("LIGHT_NODES", [])

    # Tie each of the renderNodes to the relevant material
    for node in self.renderNodes:
      node.material = self.node.materials[node.material]
      if isinstance(node, RenderNode):
        node.split_subobjects()

    # Tie each of the connectors to it's parent node
    for conn in self.connectors:
      conn.parent = self.node.nodes[conn.parent]

    # Assign each of the nodes/children to a parent node
    for node in [x for x in self.renderNodes if isinstance(x, RenderNode)]:
      if len(node.parentData) == 1:
        node.parent = self.node.nodes[node.parentData[0][0]]
      if node.children:
        for child in node.children:
          child.parent = self.node.nodes[child.parentData[0]]

    # Read and dump information about the render arg node
    # argNode = self.node.nodes[1]
    # doubs = struct.unpack("<30d", argNode.base_data[8:])
    # mat = sequence_to_matrix(doubs[:16])
    # other = doubs[16:]
    # print("Matrix:\n{}".format(mat))
    # print("Other:\n{}".format(other))
    # print("Position:\n{}".format(argNode.posData))
    # print("Rotation:\n{}".format(argNode.rotData))

    # Pause at end of file parsing, before generation
    # import pdb
    # pdb.set_trace()

    # Verify we are at the end of the file without unconsumed data.
    endPos = reader.tell()
    if len(reader.read(1)) != 0:
      print("Warning: Ended parse at {} but still have data remaining".format(endPos))

@reads_type("model::BaseNode")
class BaseNode(object):
  @classmethod
  def read(cls, stream):
    node = cls()
    # Have now encountered a non-root node with a name..
    # Which basically confirms that it has at least similar
    # structure. Now need a third entry with a dictionary...
    node.name = stream.read_string()
    node.version = stream.read_uint()
    node.props = read_raw_propertiesset(stream)
    return node

@reads_type("model::RootNode")
class RootNode(BaseNode):
  unknown_parts = []
  @classmethod
  def read(cls, stream):
    self = super(RootNode, cls).read(stream)
    self.unknown_parts.append(stream.read_uchar())
    self.unknown_parts.append(stream.read_doubles(12))
    self.unknown_parts.append(stream.read(48))
    self.materials = stream.read_list(Material.read)
    stream.materials = self.materials
    self.unknown_parts.append(stream.read(8))
    self.nodes = stream.read_list(read_named_type)
    stream.nodes = self.nodes
    print("NodeCount: {}".format(len(self.nodes)))
    return self

@reads_type("model::Node")
class Node(BaseNode):
  @classmethod
  def read(cls, stream):
    # stream.mark_type_read("model::Node")
    return super(Node, cls).read(stream)

@reads_type("model::TransformNode")
class TransformNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = super(TransformNode, cls).read(stream)
    self.matrix = readMatrixd(stream)
    return self

@reads_type("model::Bone")
class Bone(BaseNode):
  @classmethod
  def read(cls, reader):
    self = super(Bone, cls).read(reader)
    self.data = [readMatrixd(reader), readMatrixd(reader)]
    return self

ArgAnimationBase = namedtuple("ArgAnimationBase", ["matrix", "position", "quat_1", "quat_2", "scale"])

@reads_type("model::ArgAnimationNode")
class ArgAnimationNode(BaseNode, AnimatingNode):
  @classmethod
  def read(cls, stream):
    self = super(ArgAnimationNode, cls).read(stream)
    self.base = self._read_base_data(stream)
    self.posData = stream.read_list(ArgPositionNode._read_AANPositionArg)
    self.rotData = stream.read_list(ArgRotationNode._read_AANRotationArg)
    self.scaleData = stream.read_list(ArgScaleNode._read_AANScaleArg)
    return self

  def _read_base_data(self, stream):
    # base_data = stream.read(248)
    data = {}
    data["matrix"] = readMatrixd(stream)
    data["position"] = readVec3d(stream)
    data["quat_1"] = readQuaternion(stream)
    data["quat_2"] = readQuaternion(stream)
    data["scale"] = readVec3d(stream)
    return ArgAnimationBase(**data)


@reads_type("model::ArgAnimatedBone")
class ArgAnimatedBone(ArgAnimationNode):
  @classmethod
  def read(cls, stream):
    self = super(ArgAnimatedBone, cls).read(stream)
    self.boneTransform = readMatrixd(stream)
    return self

@reads_type("model::ArgRotationNode")
class ArgRotationNode(ArgAnimationNode):
  """A special case of ArgAnimationNode with only rotational data.
  Despite this, it is written and read from disk in exactly the same way."""
  @classmethod
  def read(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode")
    return super(ArgRotationNode, cls).read(stream)

  @classmethod
  def _read_AANRotationArg(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode::Rotation")
    arg = stream.read_uint()
    count = stream.read_uint()
    keys = [get_type_reader("model::Key<key::ROTATION>")(stream) for _ in range(count)]
    return (arg, keys)

@reads_type("model::ArgPositionNode")
class ArgPositionNode(ArgAnimationNode):
  """A special case of ArgAnimationNode with only positional data.
  Despite this, it is written and read from disk in exactly the same way."""
  @classmethod
  def read(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode")
    return super(ArgPositionNode, cls).read(stream)

  @classmethod
  def _read_AANPositionArg(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode::Position")
    arg = stream.read_uint()
    count = stream.read_uint()
    keys = [get_type_reader("model::Key<key::POSITION>")(stream) for _ in range(count)]
    return (arg, keys)

@reads_type("model::ArgScaleNode")
class ArgScaleNode(ArgAnimationNode):
  @classmethod
  def read(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode")
    return super(ArgScaleNode, cls).read(stream)

  @classmethod
  def _read_AANScaleArg(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode::Scale")
    arg = stream.read_uint()
    count = stream.read_uint()
    # Weirdly seems to be two sets of keys; one with 4-components and one with three
    # keys = [get_type_reader("model::Key<key::SCALE>")(stream) for _ in range(count)]
    keys = [ScaleKey.read(stream, 4) for _ in range(count)]
    count2 = stream.read_uint()
    # Second set of keys only has three components...?
    key2s = [ScaleKey.read(stream, 3) for _ in range(count2)]
    # print("Edn of scale arg at ", steam.tell())
    return (arg, (keys, key2s))


@reads_type("model::Key<key::ROTATION>")
class RotationKey(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.frame = stream.read_double()
    self.value = readQuaternion(stream)
    return self

  def __repr__(self):
    return "Key(frame={}, value={})".format(self.frame, repr(self.value))

@reads_type("model::Key<key::POSITION>")
class PositionKey(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.frame = stream.read_double()
    self.value = Vector(stream.read_doubles(3))
    return self
  def __repr__(self):
    return "Key(frame={}, value={})".format(self.frame, repr(self.value))

@reads_type("model::Key<key::SCALE>")
class ScaleKey(object):
  @classmethod
  def read(cls, stream, entrylength):
    self = cls()
    self.frame = stream.read_double()
    self.value = Vector(stream.read_doubles(entrylength))
    return self
  def __repr__(self):
    return "Key(frame={}, value={})".format(self.frame, repr(self.value))

@reads_type("model::ArgVisibilityNode")
class ArgVisibilityNode(BaseNode, AnimatingNode):
  @classmethod
  def read(cls, stream):
    self = super(ArgVisibilityNode, cls).read(stream)
    self.visData = stream.read_list(cls._read_AANVisibilityArg)
    return self

  @classmethod
  def _read_AANVisibilityArg(cls, stream):
    stream.mark_type_read("model::ArgVisibilityNode::Arg")
    arg = stream.read_uint()
    count = stream.read_uint()
    data = [stream.read_doubles(2) for _ in range(count)]
    stream.mark_type_read("model::ArgVisibilityNode::Range", count)
    return (arg, data)

def _read_material_VertexFormat(reader):
  channels = reader.read_uint()
  data = reader.read_uchars(channels)
  # Which channels have data?
  knownChannels = {0,1,4}
  dataChannels = {i: x for i, x in enumerate(data) if x != 0 and not i in knownChannels} 
  # assert not dataChannels, "Unknown vertex data channels"
  if dataChannels:
    print("Warning: Vertex channel data in unrecognised channels: {}".format(dataChannels))
  vf = VertexFormat(position=int(data[0]), normal=int(data[1]), texture=int(data[4]))
  return vf

def _read_material_texture(reader):
  unknowna = reader.read(8)
  name = reader.read_string()
  unknownb = reader.read(16)
  matrix = readMatrixf(reader)
  return Texture(unknowna, name, unknownb, matrix)

def _read_animateduniforms(stream):
  length = stream.read_uint()
  data = OrderedDict()
  for _ in range(length):
    prop = read_named_type(stream)
    data[prop.name] = prop
  return data

def _read_texture_coordinates_channels(stream):
  count = stream.read_uint()
  return stream.read_floats(count)

# Lookup table for material reading types
_material_entry_lookup = {
  "BLENDING": lambda x: x.read_uchar(),
  "CULLING" : lambda x: x.read_uchar(),
  "DEPTH_BIAS": lambda x: x.read_uint(),
  "TEXTURE_COORDINATES_CHANNELS": _read_texture_coordinates_channels,
  "MATERIAL_NAME": lambda x: x.read_string(),
  "NAME": lambda x: x.read_string(),
  "SHADOWS": lambda x: x.read_uchar(),
  "VERTEX_FORMAT": _read_material_VertexFormat,
  "UNIFORMS": read_propertyset,
  "ANIMATED_UNIFORMS": _read_animateduniforms,
  "TEXTURES": lambda x: x.read_list(_read_material_texture)
}

class Material(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    props = OrderedDict()
    for _ in range(stream.read_uint()):
      name = stream.read_string()
      props[name] = _material_entry_lookup[name](stream)
    self.props = props
    self.vertex_format = props["VERTEX_FORMAT"]
    self.name = props["NAME"]
    self.base_material = props["MATERIAL_NAME"]
    return self

@reads_type("model::LodNode")
class LodNode(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    assert stream.read_uints(3) == (0,0,0)
    count = stream.read_uint()
    self.level = [stream.read_floats(4) for x in range(count)]
    stream.mark_type_read("model::LodNode::Level", count)
    return self

@reads_type("model::Connector")
class Connector(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.data = stream.read_uints(2)
    self.parent = stream.read_uint()
    self.data = self.data + (stream.read_uint(),)
    return self

uint_negative_one = struct.unpack("<I", struct.pack("<i", -1))[0]

def _read_index_data(stream, classification=None):
  "Performs the common index-reading operation"
  dtPos = stream.tell()
  dataType = stream.read_uchar()
  entries = stream.read_uint()
  unknown = stream.read_uint()

  if dataType == 0:
    data = stream.read_uchars(entries)
    _bytes = entries
  elif dataType == 1:
    data = stream.read_ushorts(entries)
    _bytes = entries * 2
  elif dataType == 2:
    data = stream.read_uints(entries)
    _bytes = entries * 4
  else:
    raise IOError("Don't know how to read index data type {} @ {}".format(int(dataType), dtPos))

  if classification:
    stream.mark_type_read(classification, _bytes)

  return (unknown, data)

def _read_vertex_data(stream, classification=None):
  count = stream.read_uint()
  stride = stream.read_uint()
  vtxData = stream.read_floats(count*stride)

  # If given a classification, mark it off
  if classification:
    stream.mark_type_read(classification, count*stride*4)

  # Group the vertex data according to stride
  vtxData = [vtxData[i:i+stride] for i in range(0, len(vtxData), stride)]
  return vtxData

@reads_type("model::RenderNode")
class RenderNode(BaseNode):
  children = []
  @classmethod
  def read(cls, stream):
    self = super(RenderNode, cls).read(stream)
    self.unknown_start = stream.read_uint()
    self.material = stream.read_uint()

    # Read the parent section
    parentCount = stream.read_uint()
    if parentCount == 1:
      self.parentData = [stream.read_uint(), stream.read_int()]
    else:
      self.parentData = []
      for _ in range(parentCount):
        node = stream.read_uint()
        ranges = list(stream.read_ints(2))
        self.parentData.append((node, ranges[0], ranges[1]))

    # Read the vertex and index data
    self.vertexData = _read_vertex_data(stream, "__gv_bytes")
    self.unknown_indexPrefix, self.indexData = _read_index_data(stream, classification="__gi_bytes")

    # Group the index data
    if len(self.indexData) % 3 == 0:
      self.indexData = [self.indexData[i:i+3] for i in range(0, len(self.indexData), 3)]
    else:
      print("Warning: Have non-multiple of 3 index data count. Case not understood.")

    return self

  def split_subobjects(self):
    # Assume that we have four-component vertex, or no sub-objects
    assert self.material.vertex_format.nposition == 4
    # Ensure that all index faces DO NOT go over sub-objects
    # Start by calculating range blocks for each subobject
    group = self.vertexData[0][3]
    start = 0
    objects = []
    for i in range(1, len(self.vertexData)):
      if self.vertexData[i][3] != group:
        objects.append((start, i))
        start = i
        group = self.vertexData[i][3]
    # End the final object
    if start != i:
      objects.append((start, len(self.vertexData)))

    # Don't split for one child
    if len(objects) == 1:
      return

    # Validate that we separated properly
    for start, end in objects:
      groups = set(self.vertexData[i][3] for i in range(start, end))
      assert len(groups) == 1

    # Validate that for every index triple, all are within one group
    groupMembership = []
    for i, indexGroup in enumerate(self.indexData):
      # Find the object group
      firstID = indexGroup[0]
      grpIndex, group = next((i, x) for (i, x) in enumerate(objects) if x[0] <= firstID and x[1] > firstID)
      conf = all(x in range(group[0], group[1]) for x in indexGroup)
      groupMembership.append(grpIndex)
      assert conf, "Found index set that crosses vertex groups"

    # Now, split everything into sub-objects
    children = []
    for i, (start, end) in enumerate(objects):
      obj = RenderNode()
      obj.name = "{}_{}".format(self.name, i)
      obj.material = self.material
      parindex = int(self.vertexData[start][3])
      obj.parentData = self.parentData[parindex]
      obj.vertexCount = end-start
      # Recalculate the indices
      # Member indices
      childFaceData = [x for g, x in zip(groupMembership, self.indexData) if g == i]
      obj.indexData = [tuple(y - start for y in x) for x in childFaceData]
      obj.vertexData = self.vertexData[start:end]
      children.append(obj)

    self.children = children


@reads_type("model::ShellNode")
class ShellNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = super(ShellNode, cls).read(stream)
    self.unknown = stream.read_uint()
    self.vertexFormat = _read_material_VertexFormat(stream)

    # Read the vertex and index data
    self.vertexData = _read_vertex_data(stream, "__cv_bytes")
    self.unknown_indexPrefix, self.indexData = _read_index_data(stream, classification="__ci_bytes")

    return self

@reads_type("model::SkinNode")
class SkinNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = super(SkinNode, cls).read(stream)
    self.unknown = stream.read_uint()
    self.material = stream.read_uint()
    # This... appears to be slightly similar to the 'parent'
    # structure on renderNode, but just seems to be a single
    # (-1)-terminated list
    parentCount = stream.read_uint()
    self.parentlike = stream.read_uints(parentCount)
    assert stream.read_int() == -1

    # Read the vertex and index data
    self.vertexData = _read_vertex_data(stream, "__gv_bytes")
    self.unknown_indexPrefix, self.indexData = _read_index_data(stream, classification="__gi_bytes")

    return self

@reads_type("model::SegmentsNode")
class SegmentsNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = super(SegmentsNode, cls).read(stream)
    self.unknown = stream.read_uint()
    count = stream.read_uint()
    self.data = [stream.read_floats(6) for x in range(count)]
    stream.mark_type_read("model::SegmentsNode::Segments", count)
    return self

@reads_type("model::BillboardNode")
class BillboardNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = super(BillboardNode, cls).read(stream)
    self.data = stream.read(154)
    return self

@reads_type("model::LightNode")
class LightNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = super(LightNode, cls).read(stream)
    self.unknown = [stream.read_uint(), stream.read_uchar()]
    self.lightProps = read_raw_propertiesset(stream)
    self.unknown.append(stream.read_uchar())
    return self

