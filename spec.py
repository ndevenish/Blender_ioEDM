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
inSpec = open("spec.txt").read()
# lexer.input()
# while True:
#     tok = lexer.token()
#     if not tok: 
#         break      # No more input
#     print(tok)

# Define a parser
tokens = SpecLexer.tokens
"""
spec      : spec typedef
          | typedef

typedef   : name DEFINER EOL parts EOL
          | name DEFINER parts EOL

parts     : part EOL parts
          | part
          | empty

part      : def
          | multidef
          | switchdef
          | literal

def       : type name EOL
multidef  : type name '[' expr ']' EOL
switchdef : type '|' switchdef
          | type EOL

literal   : STRING

type      : IDENT
name      : IDENT
expr      : name
          | INTEGER


"""
import pdb

# def p_spec_leading(p):
#   """
#   spec : EOL typedef
#   """
#   # Ignore leading EOL
#   spec = {}
#   spec.update(p[2])
#   p[0] = spec

def p_spec(p):
  """
  spec : spec typedef
       | typedef
  """
  if len(p) == 3:
    spec = p[1]
    spec.update(p[2])
    p[0] = spec
  elif len(p) == 2:
    spec = {}
    spec.update(p[1])
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
  p[0] = "{} = Read{}()".format(p[2], p[1])

def p_multidef(p):
  """
  multidef  : type name '[' expr ']' EOL
  """
  p[0] = "{} = Read{}({})".format(p[2], p[1], p[4])

def p_switchdef(p):
  """
  switchdef : type '|' switchdef
            | type EOL
  """
  if len(p) == 4:
    p[0] = [p[1]] + p[3]
  else:
    p[0] = [p[1]]

def p_name(p):
  "name      : IDENT"
  p[0] = p[1]

def p_type(p):
  "type      : IDENT"
  p[0] = p[1]

def p_literal(p):
  "literal   : STRING EOL"
  p[0] = p[1]

def p_expr(p):
  """
  expr       : name
             | INTEGER
  """
  p[0] = p[1]

def p_error(p):
  print("Syntax error in input!" + str(p))

simpleS = """uint length
char some
"""
parser = yacc.yacc()#start='parts')
# inSpec
result = parser.parse(inSpec, lexer=lexer)
print(result)