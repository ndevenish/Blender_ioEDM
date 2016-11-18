#!/usr/bin/env python3

from edm import EDMFile

edm = EDMFile("Cockpit_Su-25T.EDM")





# import struct
# from collections import namedtuple
# import logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)



# MainIndex = namedtuple("MainIndex", ["name", "position"])

# def _read_index(data):
#   indexCount = data.read_uint()
#   print("index count: {}".format(indexCount))

#   # Read the index entries for this
#   def read_index_entry():
#     name = data.read_string()
#     idata = data.read_uint()
#     return MainIndex(name, idata)

#   index = [read_index_entry() for x in range(indexCount)]
#   return index

# def _print_index(index):
#   length = max(len(x.name) for x in index)
#   return "\n".join(["  {} = {}".format(x.name.ljust(length), x.position) for x in index])



# def read_vd_texturedef(stream):
#   def _read_textureblock(stream):
#     # logger.debug("Starting read at {}".format(stream.tell()))
#     stream.read_constant(struct.pack("<ii",0,-1))
#     name = stream.read_string()
#     stream.read_constant(struct.pack("<iiii", 2, 2, 10, 6))
#     # A matrix
#     matrix = stream.read_format("<16f")
#     return name

#   return stream.read_list(_read_textureblock)

# def read_vertex_definition(data):
#   vdProperties = {
#                 "BLENDING": data.read_uchar,
#                 "CULLING": data.read_uchar,
#                 "DEPTH_BIAS": data.read_uint, 
#                 "VERTEX_FORMAT": lambda : data.read_format("30B"),
#                 "TEXTURE_COORDINATES_CHANNELS": lambda : data.read_format("52B"),
#                 "MATERIAL_NAME": data.read_string,
#                 "NAME": data.read_string,
#                 "SHADOWS": data.read_uchar,
#                 "UNIFORMS": lambda : data.read_list(data.read_single_type),
#                 "ANIMATED_UNIFORMS": lambda : data.read_list(data.read_single_type),
#                 "TEXTURES": lambda : read_vd_texturedef(data),
#                 }

#   def _read_vdp(data):
#     name = data.read_string()
#     # logger.debug("reading {} at pos {}".format(name, data.tell()))
#     assert name in vdProperties
#     return (name, vdProperties[name]())

#   return {a: b for (a, b) in data.read_list(_read_vdp)}


# def _read_ArgPositionNode(data):
#   # print("APN at {}".format(data.tell()))
#   name = data.read_string()
#   # print("  Name: {}".format(name))
#   data.seek(256,1)
#   count = data.read_uint()
#   # print("  Count = {}".format(count))
#   # 32 bytes per entry, plus eight at end
#   data.seek(32*count + 8, 1)
#   # print("Node end at {}".format(data.tell()))
#   return name

# def dump_bytes(stream, length):
#   print("Data at {}".format(stream.tell()))
#   dump = stream.read(length)
#   fData = struct.unpack("<"+str(length//4)+"f", dump)
#   iData = struct.unpack("<"+str(length//4)+"I", dump)
#   for x, (f, i) in enumerate(zip(fData, iData)):
#     print("{:3}  {:25}  {:11}".format(x, f, i))
#   print("End of Data at {}".format(stream.tell()))
  

# def _read_ArgAnimationNode(data):
#   fixlen = {20526: 636, 22409: 596, 39604: 724}
#   # read_named_node(636)
#   name = data.read_string()

#   fullLen = fixlen[data.tell()]

#   # data.seek(107*4,1)
#   # count = data.read_uint()
#   # data.seek(4*(count*10+1), 1)
  
#   print("AAN Data at {}".format(data.tell()))
#   dump_bytes(data, fullLen)
#   # data.seek(fullLen, 1)
#   print("Data end at {}".format(data.tell()))
#   return name

# def _read_ArgRotationNode(data):
#   # fixLen = {17972: 388, 18405: 388, 18831: 388, 19260: 388, 21963: 388, 23031: 588, 23662: 348}
#   pos = data.tell()
#   # assert pos in fixLen
#   name = data.read_string()

#   data.seek(65*4,1)
#   count = data.read_uint()
#   data.seek((count*10 + 1)*4, 1)
#   # print("ARN Data at {} [length={}]".format(data.tell(), fixLen[pos]))
#   # dump_bytes(data, fixLen[pos])

#   return name

# def _read_ArgVisibilityNode(data):
#   name = data.read_string()
#   data.seek(36,1)
#   return name

# def read_named_node(length):
#   def _readNode(stream):
#     name = stream.read_string()
#     stream.seek(length,1)
#     return name
#   return _readNode

# def read_node(data):
#   FIXED_NODE_LENGTHS = {"model::Node": 12, "model::TransformNode": 140}
#   OTHER_NODE_LENGTHS = {
#     "model::ArgRotationNode": _read_ArgRotationNode, 
#     "model::ArgPositionNode": _read_ArgPositionNode,
#     "model::ArgAnimationNode": _read_ArgAnimationNode,
#     "model::ArgVisibilityNode": _read_ArgVisibilityNode}

#   position = data.tell()
#   nodetype = data.read_string()
#   print("Reading {} at {}".format(nodetype, position))
#   if nodetype in FIXED_NODE_LENGTHS:
#     data.seek(FIXED_NODE_LENGTHS[nodetype], 1)
#     return nodetype
#   elif nodetype in OTHER_NODE_LENGTHS:
#     nodeData = OTHER_NODE_LENGTHS[nodetype](data)
#     return (nodetype, nodeData)
#   else:
#     raise KeyError("Unknown node type at {}: {}".format(data.tell(), nodetype))


# @reads_type("model::RootNode")
# def read_root_node(data):
#   logger.debug("Reading RootNode")
#   description = data.read_string()
#   # Unknown 4-byte value; version? Is zero in known instance
#   data.seek(4, 1)
#   properties = data.read_list(data.read_single_type)

#   # BIGa chunk of unknown data here - of unknown length
#   data.seek(145,1)

#   # # Now an array of what looks like... vertex array information?
#   # matRefCount = data.read_uint()
#   # for x in range()
#   vertexDefs = data.read_list(read_vertex_definition)
#   logger.debug("Read {} vertex definition sets".format(len(vertexDefs)))

#   # Now, read what appears to be a node list.
#   # Next ints are 0 602 417 which could be counts. Assume first two are unrelated
#   # stream.seek(8,1)
#   # nodes = read_nodelist(stream)

#   # 0 602 417
#   # Node 0 0 0 [12]
#   # TransformNode [140]
#   data.seek(8,1)
#   nodes = data.read_list(read_node)





# class EDMFile(object):
#   def __init__(self, filename):
#     self.data = Reader(filename)
#     self.data.read_constant(b"EDM")
#     self.version = self.data.read_ushort()
#     logger.debug("Opened EDM file {}, version {}".format(filename, self.version))
#     # Read the basic file indices
#     self.index_A = _read_index(self.data)
#     self.index_B = _read_index(self.data)
#     logger.debug("First Index:\n{}".format(_print_index(self.index_A)))
#     logger.debug("Second Index:\n{}".format(_print_index(self.index_B)))

# file = EDMFile("Cockpit_Su-25T.EDM")

# nodeStart = file.data.tell()
# firstNode = file.data.read_single_type()
# # nodes = [x for x in file.data.read_single_type()]

# logger.debug("Length so far for node: {}".format(file.data.tell()-nodeStart))
# logger.info("End of reading; file position: {}".format(file.data.tell()))



# # def read_named_node(length):
# #   def _readNode(stream):
# #     name = read_str(stream)
# #     stream.seek(length,1)
# #     return name
# #   return _readNode

# # def read_nodelist(stream):
# #   # We don't know exactly how to interpret. Just store the (common? Lengths now)
# #   NODE_LENGTHS = {
# #     "model::Node": 12, "model::TransformNode": 140, "model::ArgRotationNode": read_named_node(388),
# #     "model::ArgPositionNode": read_named_node(364), "model::ArgAnimationNode": read_named_node(636),
# #     "model::ArgVisibilityNode:": read_named_node(36)
# #   }
# #   count = read_ui(stream)
# #   nodes = []
# #   for i in range(count):
# #     nodeType = read_str(stream)
# #     print("Reading node {} at {}".format(nodeType, stream.tell()))
# #     length = NODE_LENGTHS[nodeType]
# #     if callable(length):
# #       nodes.append({"type": nodeType, "data": length(stream)})
# #     else:
# #       stream.seek(length, 1)
# #       nodes.append(nodeType)

