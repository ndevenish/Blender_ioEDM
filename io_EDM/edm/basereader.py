"""
BaseReader

A very simple extended stream reader, with capability to read single or 
arrays of standard types.

It additionally has functions to read a uint-prefixed string, and a 
uint-prefixed list of some item, defined by the function passed in
"""

import struct
from collections import namedtuple

import logging
logger = logging.getLogger(__name__)

class BaseReader(object):
  def __init__(self, filename):
    self.filename = filename
    self.stream = open(filename, "rb")

  def tell(self):
    return self.stream.tell()

  def seek(self, offset, from_what=0):
    self.stream.seek(offset, from_what)

  def close(self):
    self.stream.close()

  def read_constant(self, data):
    filedata = self.stream.read(len(data))
    if not data == filedata:
      raise IOError("Expected constant not encountered; {} != {}".format(filedata, data))

  def read(self, length):
    return self.stream.read(length)
    
  def read_uchar(self):
    return struct.unpack("B", self.stream.read(1))[0]

  def read_uchars(self, count):
    return struct.unpack("{}B".format(count), self.stream.read(1*count))

  def read_ushort(self):
    return struct.unpack("<H", self.stream.read(2))[0]

  def read_ushorts(self, count):
    return struct.unpack("<{}H".format(count), self.stream.read(2*count))

  def read_uint(self):
    """Read an unsigned integer from the data"""
    return struct.unpack("<I", self.stream.read(4))[0]

  def read_uints(self, count):
    """Read an unsigned integer from the data"""
    return struct.unpack("<{}I".format(count), self.stream.read(4*count))

  def read_int(self):
    """Read a signed integer from the data"""
    return struct.unpack("<i", self.stream.read(4))[0]
  
  def read_ints(self, count):
    """Read a signed integer from the data"""
    return struct.unpack("<{}i".format(count), self.stream.read(4*count))

  def read_float(self):
    return struct.unpack("<f", self.stream.read(4))[0]

  def read_floats(self, count):
    return struct.unpack("<{}f".format(count), self.stream.read(4*count))
  
  def read_double(self):
    return struct.unpack("<d", self.stream.read(8))[0]  

  def read_doubles(self, count):
    return struct.unpack("<{}d".format(count), self.stream.read(8*count))

  def read_format(self, format):
    """Read a struct format from the data"""
    return struct.unpack(format, self.stream.read(struct.calcsize(format)))

  def read_string(self):
    """Read a length-prefixed string from the file"""
    prepos = self.stream.tell()
    length = self.read_uint()
    assert length < 200, "Overly long string length found; {} at {}".format(length, prepos)
    try:
      return self.stream.read(length).decode("UTF-8")
    except UnicodeDecodeError:
      raise RuntimeError("Could not decode string with length {} at position {}".format(length, prepos))

  def read_list(self, reader):
    """Reads a length-prefixed list of something"""
    length = self.read_uint()
    entries = []
    for index in range(length):
      entries.append(reader(self))
    return entries

  # def read_single_type(self):
  #   """Reads a single instance of a name-prefixed type"""
  #   typeName = self.read_string()
  #   reader = get_type_reader(typeName)
  #   return reader(self)
