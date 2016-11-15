#!/usr/bin/env/python3


# class BinarySpec(object):
#   def __init__(self, filename):
#     self.filename = filename
#     self._file = open(filename)
#     self._parse()

#   def _parse(self):
#     while not self._file.eof


# reader = BinarySpec("spec.txt")

import ply.lex as lex
import ply.yacc as yacc
import re
import struct
import codecs
from collections import namedtuple, OrderedDict

LiteralReader = namedtuple("LiteralReader", ["data", "name"])
TypeReader = namedtuple("TypeReader", ["type", "name"])
ArrayReader = namedtuple("ArrayReader", ["type", "name", "count"])
OneOfReader = namedtuple("OneOfReader", ["types"])

class SpecLexer(object):
  tokens = (
    "STRING",
    "IDENT",
    "INTEGER",
    "DEFINER",
    "EOL",
  )

  t_IDENT = r'[_A-Za-z][_A-Za-z0-9]*'
  t_DEFINER = r':='

  t_ignore = " \t"

  reString = None

  def t_STRING(self, t):
    r'(|b|uip|z)\"((?:\\.|[^\\"])*)\"'
    # r'([a-z]*)\"((?:\\.|[^\\"])*)\"'
    
    if self.reString is None:
      self.reString = re.compile(self.t_STRING.__doc__)
    prefix, data = self.reString.findall(t.value)[0]

    if not prefix:
      raise NotImplementedError("Unprefixed strings are ambiguous")
    elif prefix == "b":
      asbytes = codecs.escape_decode(bytes(data, "utf-8"))[0]
      t.value = asbytes
    elif prefix == "uip":
      asbytes = data.encode("utf-8") #codecs.escape_decode(bytes(data, "utf-8"))[0]
      # Convert this to byte-prefixed
      t.value = struct.pack("<I{}s".format(len(asbytes)), len(asbytes), asbytes)
    elif prefix == "z":
      raise NotImplementedError("Null-terminated strings not yet implemented")


    return t


  literals = '[]|'

  def t_INTEGER(self, t):
    r'\d+'
    t.value = int(t.value)
    return t

  def t_EOL(self, t):
      r'\n'
      t.lexer.lineno += len(t.value)
      return t

  # Error handling rule
  def t_error(self, t):
      print("Illegal character '%s'" % t.value[0])
      t.lexer.skip(1)

  def t_comment(self, t):
    r'\#[^\n]*\n'


  def lexer(self, **kwargs):
    return lex.lex(module=self, **kwargs)

# Give the lexer some input and tokenize
lexer = SpecLexer().lexer()

# Define a parser
tokens = SpecLexer.tokens

def p_spec(p):
  """
  spec : spec typedef
  """
  spec = p[1]
  typedef = p[2]
  name = list(typedef.keys())[0]
  
  if name in spec:
    raise RuntimeError("Duplicate definition for type {}".format(name))

  spec.update(typedef)
  p[0] = spec
  
def p_start_spec(p):
  """
  spec : typedef
  """
  spec = OrderedDict()
  typedef = p[1]

  spec.update(typedef)
  p[0] = spec

def p_typedef_pre(p):
  """
  typedef : EOL typedef
  """
  p[0] = p[2]

def p_typedef(p):
  """
  typedef   : name DEFINER EOL parts EOL
            | name DEFINER parts EOL
  """
  if len(p) == 6:
    p[0] = {p[1]: p[4]}
  else:
    p[0] = {p[1]: p[3]}


def p_parts(p):
  """
  parts     : parts part
            | part 
  """
  if len(p) == 3:
    p[0] = p[1] + [p[2]]
  else:
    p[0] = [p[1]]

def p_part(p):
  """
  part      : def
            | multidef
            | switchdef
            | literal
  """
  p[0] = p[1]
  # pdb.set_trace()

def p_def(p):
  """
  def       : type name EOL
  """
  # p[0] = "{} = Read{}()".format(p[2], p[1])
  p[0] = TypeReader(type=p[1], name=p[2])

def p_multidef(p):
  """
  multidef  : type name '[' expr ']' EOL
  """
  # p[0] = "{} = Read{}({})".format(p[2], p[1], p[4])
  p[0] = ArrayReader(type=p[1], name=p[2], count=p[4])

def p_switchdef(p):
  """
  switchdef : type '|' switchdef
            | type EOL
  """
  if len(p) == 4:
    p[0] = OneOfReader(types=[p[1]] + p[3].types)
  else:
    p[0] = OneOfReader(types=[p[1]])

def p_name(p):
  "name      : IDENT"
  p[0] = p[1]

def p_type(p):
  "type      : IDENT"
  p[0] = p[1]

def p_literal(p):
  """
  literal   : STRING EOL
            | STRING name EOL
  """
  name = None if len(p) == 3 else p[2]
  p[0] = LiteralReader(data=p[1], name=name)

def p_expr(p):
  """
  expr       : name
             | INTEGER
  """
  p[0] = p[1]

def p_error(p):
  print("Syntax error in input!" + str(p))

parser = yacc.yacc()#start='parts')


def parse_spec(filename):
  return parser.parse(open(filename).read(), lexer=lexer)

spec = parse_spec("spec.txt")
print(spec)


def read_uint_string(s):
  length = struct.unpack("<I", s.read(4))[0]
  return s.read(length).decode("UTF-8")

internal_types = {
  'uint': lambda s: struct.unpack("<I", s.read(4))[0],
  'float': lambda s: struct.unpack("<f", s.read(4))[0],
  'ushort': lambda s: struct.unpack("<H", s.read(2))[0],
  'uchar': lambda s: struct.unpack("B", s.read(1))[0],
  'byte': lambda s: struct.unpack("B", s.read(1))[0],
  'uint_string': read_uint_string,
}

class SpecReader(object):
  """Reads a file according to the spec"""
  def __init__(self, filename):
    self.specfile = filename
    self.spec = parse_spec(filename)

  def readfile(self, filename):
    """Reads a binary file according to the spec"""
    file = open(filename, 'br')
    # Get the name of the first spec rule
    firstRule = list(self.spec.keys())[0]
    return self._read_type(file, firstRule)

  def _read_type(self, file, typename, depth=0):
    print(depth*"  " + "Reading {} at {}".format(typename, file.tell()))
    # If in our simple internal lookup table, then use that
    if typename in internal_types:
      return internal_types[typename](file)
    if not typename in self.spec:
      raise IndexError("Type named {} not recognised in spec table".format(typename))
    spec = self.spec[typename]
    # Properties read for this type
    props = {"_type": typename}
    # Read each spec entry
    for entry in spec:
      if isinstance(entry, LiteralReader):
        # Raw bytes object. Read the length and compare
        data = file.read(len(entry.data))
        print("  "*depth + "  Reading literal data " + repr(entry.data) + " [{}]".format(len(entry.data)))
        if not data == entry.data:
          raise IOError("Fixed byte constants do not match for definition of {}".format(typename))
        if entry.name:
          props[entry.name] = data
      elif isinstance(entry, TypeReader):
        props[entry.name] = self._read_type(file, entry.type, depth+1)
      elif isinstance(entry, ArrayReader):
        # Step 1: Resolve 'count' into an actual number
        count = entry.count
        if not isinstance(count, int):
          if count in props:
            count = props[count]
            if not isinstance(count, int):
              raise RuntimeError("Could not resolve count expression to integer")
          else:
            raise NotImplementedError("Expression-based lengths not yet implemented")
        props[entry.name] = [self._read_type(file, entry.type, depth+1) for x in range(count)]
      elif isinstance(entry, OneOfReader):

        readpoint = file.tell()
        result = None
        for tryType in entry.types:
          try:
            result = self._read_type(file, tryType, depth+1)
            break
          except IOError:
            print("  "*(depth+1) + "Could not read")
            file.seek(readpoint)
        if result is None:
          raise IOError("Could not read any of types [{}]".format(str(entry.types)))
        assert len(spec) == 1, "No naming of alternate-option parsing blocks at the moment"
        return result
      else:
        raise NotImplementedError("No implementation for {}".format(str(entry)))

    print("  "*depth + str(props))
    return props

reader = SpecReader("spec.txt")
binfile = reader.readfile("Cockpit_Su-25T.EDM")

#       TypeReader = namedtuple("TypeReader", ["type", "name"])
# ArrayReader = namedtuple("ArrayReader", ["type", "name", "count"])
# OneOfReader = namedtuple("OneOfReader", ["types"])

