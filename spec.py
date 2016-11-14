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
  t_STRING =   r'[a-z]?\"(\\.|[^\\"])*\"'

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

def p_spec(p):
  """
  spec : spec typedef
       | typedef
  """
  pdb.set_trace()

def p_typedef(p):
  """
  typedef   : name DEFINER EOL parts EOL
            | name DEFINER parts EOL
  """
  pdb.set_trace()

def p_parts(p):
  """
  parts     : parts part
            | part
  """
  pdb.set_trace()

def p_part(p):
  """
  part      : def EOL
            | multidef EOL
            | switchdef EOL
            | literal EOL
  """
  p[0] = p[1]

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
  "literal   : STRING"
  p[0] = p[1]

def p_expr(p):
  """
  expr       : name
             | INTEGER
  """
  p[0] = p[1]

def p_err2(p):
  "spec : error"
  pdb.set_trace()

def p_error(p):
  print("Syntax error in input!" + str(p))

simpleS = """uint length
char name
"""
parser = yacc.yacc(start='parts')
# inSpec
result = parser.parse(simpleS, lexer=lexer)
print(result)