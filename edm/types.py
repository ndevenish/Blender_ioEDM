

# from .typereader import Property, allow_properties, reads_type
# from collections import namedtuple

from .typereader import reads_type, readMatrixf, readMatrixd
from .typereader import get_type_reader as _tr_get_type_reader
from .basereader import BaseReader

from collections import namedtuple, OrderedDict, Counter
import struct

from .mathtypes import Vector

# VertexFormat = namedtuple("VertexFormat", ["position", "normal", "texture"])
AnimatedProperty = namedtuple("AnimatedProperty", ["name", "id", "keys"])

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
  return get_type_reader(typename)(reader)

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
  length = stream.read_uint()
  if length > 0:
    stream.mark_type_read("model::PropertiesSet")
  data = OrderedDict()
  for _ in range(length):
    prop = read_named_type(stream)
    data[prop.name] = prop.value
  return data

class EDMFile(object):
  def __init__(self, filename):
    reader = TrackingReader(filename)
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
    data = reader.read(20)
    while True:
      if data[-10:] == b"CONNECTORS":
        objPos = reader.tell()-18
        objCount = struct.unpack("<I", data[-18:-14])[0]
        print("objects: {}".format(objCount))
        objects = read_object_list(reader, objCount, "CONNECTORS")
        break
      if data[-12:] == b"RENDER_NODES":
        objPos = reader.tell()-20
        objCount = struct.unpack("<I", data[-20:-16])[0]
        objects = read_object_list(reader, objCount, "RENDER_NODES")
        break
      data = data[1:] + reader.read(1)

    print("Found object list at {}, gap size = {}".format(objPos, objPos-preObjPos))

    # Validate against the index
    rems = Counter(self.indexA)
    rems.subtract(Counter({x: c for (x,c) in reader.typecount.items() if x in self.indexA}))
    for k in [x for x in rems.keys() if rems[x] == 0]:
      del rems[k]

    print("IndexA items remaining before RENDER_NODES/CONNECTORS: {}".format(rems))
    cB = Counter({x: c for (x,c) in reader.typecount.items() if x in self.indexB})
    remBs = Counter(self.indexB)
    remBs.subtract(cB)
    for k in [x for x in remBs.keys() if remBs[x] == 0]:
      del remBs[k]
    
    import pdb
    pdb.set_trace()

    assert len(objects) <= 2
    self.connectors = objects.get("CONNECTORS", [])
    self.renderNodes = objects.get("RENDER_NODES", [])

    # Tie each of the renderNodes to the relevant material
    for node in self.renderNodes:
      node.material = self.node.materials[node.material]

    # Verify we are at the end of the file without unconsumed data.
    endPos = reader.tell()
    if len(reader.read(1)) != 0:
      print("Warning: Ended parse at {} but still have data remaining".format(endPos))

@reads_type("model::RootNode")
class RootNode(object):
  unknown_parts = []
  @classmethod
  def read(cls, stream):
    # stream.mark_type_read("model::RootNode")
    self = cls()
    self.name = stream.read_string()
    self.version = stream.read_uint()
    self.properties = read_propertyset(stream)
    print("Unknown A: {}x145".format(stream.tell()))
    self.unknown_parts.append(stream.read_uchar())
    self.unknown_parts.append(stream.read_doubles(12))
    self.unknown_parts.append(stream.read(48))
    self.materials = stream.read_list(Material.read)
    print("Unknown B: {}x8".format(stream.tell()))
    self.unknown_parts.append(stream.read(8))
    self.nodes = stream.read_list(read_named_type)
    return self

@reads_type("model::BaseNode")
class BaseNode(object):
  @classmethod
  def read(cls, stream):
    node = cls()
    node.base_data = stream.read_uints(3)
    return node

@reads_type("model::Node")
class Node(BaseNode):
  @classmethod
  def read(cls, stream):
    # stream.mark_type_read("model::Node")
    super(Node, cls).read(stream)

@reads_type("model::TransformNode")
class TransformNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = super(TransformNode, cls).read(stream)
    self.matrix = readMatrixd(stream)
    return self

@reads_type("model::ArgRotationNode")
class ArgRotationNode(object):
  @classmethod
  def read(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode")
    self = cls()
    self.name = stream.read_string()
    self.base_data = stream.read(248)
    assert stream.read_uint() == 0
    self.rotData = stream.read_list(cls._read_AANRotationArg)
    assert stream.read_uint() == 0
    return self

  @classmethod
  def _read_AANRotationArg(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode::Rotation")
    arg = stream.read_uint()
    count = stream.read_uint()
    keys = [get_type_reader("model::Key<key::ROTATION>")(stream) for _ in range(count)]
    return (arg, count, keys)

@reads_type("model::ArgPositionNode")
class ArgPositionNode(object):
  @classmethod
  def read(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode")
    self = cls()
    self.name = stream.read_string()
    self.base_data = stream.read(248)
    self.posData = stream.read_list(cls._read_AANPositionArg)
    self.unknown = stream.read_uints(2)
    return self
    
  @classmethod
  def _read_AANPositionArg(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode::Position")
    arg = stream.read_uint()
    count = stream.read_uint()
    keys = [get_type_reader("model::Key<key::POSITION>")(stream) for _ in range(count)]
    import pdb
    pdb.set_trace()

    return (arg, keys)

@reads_type("model::ArgScaleNode")
class ArgScaleNode(object):
  @classmethod
  def read(cls, stream):
    stream.mark_type_read("model::ArgAnimationNode")
    self = cls()
    self.name = stream.read_string()
    self.base_data = stream.read(248)
    # ASSUME that it is layed out in a similar way, but have no non-null examples.
    # So, until we do, assert that this is zero always
    assert all(x == 0 for x in stream.read(12))
    return self

@reads_type("model::Key<key::ROTATION>")
class RotationKey(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.data = stream.read(40)
    return self

@reads_type("model::Key<key::POSITION>")
class PositionKey(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.key = stream.read_double()
    self.value = Vector(stream.read_doubles(3))
    return self
  def __repr__(self):
    return "key::POSITION({}: {})".format(self.key, repr(self.value))

@reads_type("model::AnimatedProperty<float>")
def _read_apf(stream):
  name = stream.read_string()
  iVal = stream.read_uint()
  count = stream.read_uint()
  keys = [get_type_reader("model::Key<key::FLOAT>")(stream) for _ in range(count)]
  # unk = data.read_format("<8f")
  return AnimatedProperty(name, iVal, keys)

@reads_type("model::Key<key::FLOAT>")
class FloatKey(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    key = stream.read_double()
    value = stream.read_float()
    return self

@reads_type("model::ArgAnimationNode")
class ArgAnimationNode(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.base_data = stream.read(248)
    self.posData = stream.read_list(ArgPositionNode._read_AANPositionArg)
    self.rotData = stream.read_list(ArgRotationNode._read_AANRotationArg)
    assert stream.read_uint() == 0
    return self

@reads_type("model::ArgVisibilityNode")
class ArgVisibilityNode(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.unknown = stream.read(8)
    self.visData = stream.read_list(cls._read_AANVisibilityArg)
    return self

  @classmethod
  def _read_AANVisibilityArg(cls, stream):
    stream.mark_type_read("model::ArgVisibilityNode::Arg")
    arg = stream.read_uint()
    count = stream.read_uint()
    data = stream.read(16*count)
    stream.mark_type_read("model::ArgVisibilityNode::Range", count)
    return (arg, count, data)

def _read_material_VertexFormat(reader):
  channels = reader.read_uint()
  # data = [int(x) for x in reader.read(channels)]
  data = reader.read(channels)
  # Ensure we don't have any unknown values
  assert data[2:4] == b'\x00\x00'
  assert all(x == 0 for x in data[5:])
  vf = VertexFormat(position=int(data[0]), normal=int(data[1]), texture=int(data[4]))
  return vf

def _read_material_texture(reader):
  reader.read_constant(b"\x00\x00\x00\x00\xff\xff\xff\xff")
  name = reader.read_string()
  reader.read_constant(b"\x02\x00\x00\x00\x02\x00\x00\x00\n\x00\x00\x00\x06\x00\x00\x00")
  matrix = readMatrixf(reader)
  return (name, matrix)

def _read_animateduniforms(stream):
  length = stream.read_uint()
  data = OrderedDict()
  for _ in range(length):
    prop = read_named_type(stream)
    data[prop.name] = (prop.id, prop.keys)
  return data

# Lookup table for material reading types
_material_entry_lookup = {
  "BLENDING": lambda x: x.read_uchar(),
  "CULLING" : lambda x: x.read_uchar(),
  "DEPTH_BIAS": lambda x: x.read_uint(),
  "TEXTURE_COORDINATES_CHANNELS": lambda x: x.read(52),
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
    return self

@reads_type("model::Connector")
class Connector(object):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    self.data = stream.read(16)
    return self

uint_negative_one = struct.unpack("<I", struct.pack("<i", -1))[0]

@reads_type("model::RenderNode")
class RenderNode(BaseNode):
  @classmethod
  def read(cls, stream):
    self = cls()
    self.name = stream.read_string()
    super(RenderNode, cls).read(stream)
    self.material = stream.read_uint()
    self.parentData = stream.read_list(cls._read_parent_section)
    self.vertexCount = stream.read_uint()
    self.vertexStride = stream.read_uint()
    # Read and group this according to stride
    vtx = stream.read_floats(self.vertexCount * self.vertexStride)
    stream.mark_type_read("__gv_bytes", len(vtx)*4)
    n = self.vertexStride
    self.vertexData = [vtx[i:i+n] for i in range(0, len(vtx), n)]

    # Now read the index data
    dataType = stream.read_uchar()
    entries = stream.read_uint()
    assert stream.read_uint() == 5
    if dataType == 0:
      self.indexData = stream.read_uchars(entries)
      stream.mark_type_read("__gi_bytes", entries)
    elif dataType == 1:
      self.indexData = stream.read_ushorts(entries)
      stream.mark_type_read("__gi_bytes", entries*2)
    else:
      raise IOError("Unknown vertex index type '{}'".format(dataType))
    return self

  @classmethod
  def _read_parent_section(cls, stream):
    # Read uint values until we get -1 (signed)
    # This will either be <uint> <-1> or <uint> <uint> <-1>
    def _read_to_next_negative():
      data  = stream.read_uint()
      if data == uint_negative_one:
        return []
      else:
        return [data] + _read_to_next_negative()
    section = _read_to_next_negative()
    assert len(section) == 1 or len(section) == 2
    return section

