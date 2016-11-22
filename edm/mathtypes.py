
try:
  from mathutils import Matrix, Vector
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
