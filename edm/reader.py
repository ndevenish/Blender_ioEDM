#!/usr/bin/env python3

import struct
from collections import namedtuple

from .typereader import get_type_reader

import logging
logger = logging.getLogger(__name__)

class Reader(object):
  def __init__(self, filename):
    self.filename = filename
    self.stream = open(filename, "rb")

  def tell(self):
    return self.stream.tell()

  def seek(self, offset, from_what=0):
    self.stream.seek(offset, from_what)

  def read_constant(self, data):
    filedata = self.stream.read(len(data))
    assert data == filedata, "Fixed byte data mismatch"

  def read(self, length):
    return self.stream.read(length)
    
  def read_uchar(self):
    return struct.unpack("B", self.stream.read(1))[0]

  def read_ushort(self):
    return struct.unpack("<H", self.stream.read(2))[0]

  def read_uint(self):
    """Read an unsigned integer from the data"""
    return struct.unpack("<I", self.stream.read(4))[0]

  def read_float(self):
    return struct.unpack("<f", self.stream.read(4))[0]

  def read_format(self, format):
    """Read a struct format from the data"""
    return struct.unpack(format, self.stream.read(struct.calcsize(format)))

  def read_string(self):
    """Read a length-prefixed string from the file"""
    prepos = self.stream.tell()
    length = self.read_uint()
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


  def read_single_type(self, source=None):
    """Reads a single instance of a named type"""
    assert source is self or source is None
    typeName = self.read_string()
    reader = get_type_reader(typeName)
    return reader(self)


  # def read_typed_list(self):
  #   return read_list()
  #   length = self.read_uint()
  #   entries = []
  #   logger.debug("Reading typed list of length {}".format(length))
  #   for index in range(length):
  #     entries.append(self.read_single_type())
  #   return entries

  # 