
try:
  from mathutils import Matrix, Vector, Quaternion
except ImportError:
  # We don't have mathutils. Make some very basic replacements.
  class Vector(tuple):
    def __repr__(self):
      return "Vector({})".format(super(Vector, self).__repr__())
  class Matrix(tuple):
    def transposed(self):
      cols = [[self[j][i] for j in range(len(self))] for i in range(len(self))]
      return Matrix(cols)
    def __repr__(self):
      return "Matrix({})".format(super(Matrix, self).__repr__())

  class Quaternion(tuple):
    def ___repr__(self):
      return "Quaternion({})".format(super(Quaternion, self).__repr__())

def matrix_to_blender(matrix):
  return Matrix([matrix[0], -matrix[2], matrix[1], matrix[3]])

def matrix_to_edm(matrix):
  return Matrix([matrix[0], matrix[2], -matrix[1], matrix[3]])

def vector_to_blender(v):
  return Vector([v[0], -v[2], v[1]])

def vector_to_edm(vector):
  return Vector([v[0], v[2], -v[1]])