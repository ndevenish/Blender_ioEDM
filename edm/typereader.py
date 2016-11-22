"""
Allows registration of type-readers by name, and retrieval of those readers.

Each reader function takes a single argument; a BaseReader object

"""
from inspect import isclass

from collections import namedtuple
from .mathtypes import Vector

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
    if not isclass(fn):
      _typeReaders[withName] = fn
    elif hasattr(fn, "read"):
      _typeReaders[withName] = fn.read
    else:
      raise RuntimeError("Unrecognised type reader {}".format(fn))
    fn.forTypeName = withName
    return fn
  return wrapper

def allow_properties(w):
  """Decorator to generate type-readers for type-as-property values"""
  name = "model::Property<{}>".format(w.forTypeName)
  _typeReaders[name] = generate_property_reader(w.forTypeName)
  return w

# Vector2 = namedtuple("Vector2", ["x", "y"])
# Vector3 = namedtuple("Vector3", ["x", "y", "z"])

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
  return Vector(data.read_format("<ff"))

@allow_properties
@reads_type("osg::Vec3f")
def _read_vec2f(data):
  return Vector(data.read_format("<fff"))

@reads_type("osg::Matrixf")
def readMatrixf(stream):
  return stream.read_floats(16)

@reads_type("osg::Matrixd")
def readMatrixd(stream):
  return stream.read_doubles(16)

print("Loaded typereaders ({})".format(len(_typeReaders)))
