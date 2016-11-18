"""
Allows registration of type-readers by name, and retrieval of those readers.

Each reader function takes a single argument; a BaseReader object

"""

from collections import namedtuple

_typeReaders = {}

Property = namedtuple("Property", ["name", "value"])

def get_type_reader(typeName):
  try:
    return _typeReaders[typeName]
  except KeyError:
    raise KeyError("No reader defined for stream type '{}'".format(typeName)) from None

def generate_property_reader(generic_type):
  def _read_property(data):
    name = data.read_string()
    data = get_type_reader(generic_type)(data)
    return Property(name, data)
  return _read_property


def reads_type(withName):
  """Simple registration function to read named type objects"""
  def wrapper(fn):
    _typeReaders[withName] = fn
    fn.forTypeName = withName
    return fn
  return wrapper

def allow_properties(w):
  """Decorator to generate type-readers for type-as-property values"""
  name = "model::Property<{}>".format(w.forTypeName)
  _typeReaders[name] = generate_property_reader(w.forTypeName)
  return w

Vector2 = namedtuple("Vector2", ["x", "y"])
Vector3 = namedtuple("Vector3", ["x", "y", "z"])

@allow_properties
@reads_type("unsigned int")
def _read_uint(data):
  return data.read_uint()

@allow_properties
@reads_type("float")
def read_prop_float(data):
  return data.read_float()

@allow_properties
@reads_type("osg::Vec2f")
def _read_vec2f(data):
  return Vector2(*data.read_format("<ff"))

@allow_properties
@reads_type("osg::Vec3f")
def _read_vec2f(data):
  return Vector3(*data.read_format("<fff"))

@reads_type("model::AnimatedProperty<float>")
def _read_apf(data):
  name = data.read_string()
  unk = data.read_format("<8f")
  return Property(name, unk)

@reads_type("model::BaseNode")
def read_baseNode(stream):
  return stream.read_uints(3)

@reads_type("model::RootNode")
def read_rootNode(stream):
  return RootNode.read(stream)


class RootNode(object):
  @classmethod
  def read(cls, stream):
    