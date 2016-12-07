

import contextlib, os

@contextlib.contextmanager
def chdir(to):
    original = os.getcwd()
    try: 
      os.chdir(to)
      yield
    finally:
      os.chdir(original)

def get_all_parents(objects):
  """
  Gets a set of all direct ancestors of all objects passed in.
  This will work as long as the objects have a single 'parent' attribute that
  either points to the tree parent, or is None.
  """
  objs = set()
  if not hasattr(objects, "__iter__"):
    objects = [objects]
  for item in objects:
    objs.add(item)
    if item.parent:
      objs.update(_get_all_parents(item.parent))
  return objs

def get_root_object(obj):
  """Given an object, returns the root node.
  Follows 'parent' attribute references until none remain."""
  obj = obj
  while obj.parent:
    obj = obj.parent
  return obj