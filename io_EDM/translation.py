"""
translation.py

Holds the translation tree that we use to step to/from blender/edm forms
"""


class TranslateNode(object):
  """Holds a triple of blender object, render node and transform nodes.
  Each TranslateNode maps to maximum ONE blender object maximum ONE renderNode
  and maximum ONE transform node. It may map to more than one type, in cases
  where they are directly equatable.
  """
  blender = None
  render = None
  transform = None

  @property
  def name(self):
    if self.blender:
      return "bl:" + self.blender.name
    elif self.transform and self.transform.name:
      return "tf:" + self.transform.name
    elif self.render and self.render.name:
      return "rn:" + self.render.name
    else:
      parts = []
      if self.blender:
        parts.append("bobj")
      if self.render:
        parts.append("rendernode")
      if self.transform:
        parts.append("transform")
      return "Unnamed" + (" " if parts else "")+ "/".join(parts)

  def __init__(self, blender=None, render=None, transform=None):
    self.blender = blender
    self.render = render
    self.transform = transform
    self.parent = None
    self.children = []

  @property
  def type(self):
    "Easy test to see if we are a simple node"
    if self.blender and not self.render and not self.transform:
      return "BLEND"
    if not self.blender and self.render and not self.transform:
      return "RENDER"
    if not self.blender and not self.render and self.transform:
      return "TRANSFORM"
    if any([self.blender, self.render, self.transform]):
      return "MIXED"
    else:
      return None

class RootTranslateNode(object):
  """Acts as the root node of a translation graph"""
  def __init__(self):
    self.transform = None
    self.render = None
    self.blender = None
    self.children = []
    self.parent = None
  @property
  def name(self):
    return "<ROOT>"

class TranslateGraph(object):
  def __init__(self):
    self.nodes = [RootTranslateNode()]
    self.root = self.nodes[0]

  def print_tree(self):
    def _printNode(node, prefix=None, last=True):
      if prefix is None:
        firstPre = ""
        prefix = ""
      else:
        firstPre = prefix + (" `-" if last else " |-")
        prefix = prefix + ("   " if last else " | ")
      print(firstPre + node.name.ljust(30-len(firstPre)) + " Render: " + str(node.render).ljust(30) + " Trans: " + str(node.transform))
      for child in node.children:
        _printNode(child, prefix, child is node.children[-1])

    if self.root:
      _printNode(self.root)

  def walk_tree(self, walker, include_root=False):
    """Accepts a function, and calls it for every node in the tree depth first.
    The parent is guaranteed to be initialised before the child. Any changes
    to the collection of children of the active node are respected"""
    def _walk_node(node):
      walker(node)
      for child in node.children:
        _walk_node(child)
    if include_root:
      _walk_node(self.root)
    else:
      for root in self.root.children:
        _walk_node(root)

  def attach_node(self, node, parent):
    """Adds a new child to a parent node"""
    assert parent in self.nodes, "Parent must exist in node graph"
    assert not node in self.nodes, "Attempting to reattach child already in graph"

    assert not node.children, "New child must not have chilren"

    self.nodes.append(node)
    parent.children.append(node)
    node.parent = parent

  def remove_node(self, node):
    assert node in self.nodes, "Node not in graph"
    assert node.parent, "Invalid node: No parent. Cannot remove root node."
    node.parent.children.remove(node)
    node.parent = None
    self.nodes.remove(node)
