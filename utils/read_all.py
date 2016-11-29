#!/usr/bin/env python3

"""Reads all .edm files in a sub folder and saves data to a dump file.

Usage:
  read_all [<start> [<end>]]
"""
from io_EDM.edm import EDMFile

import itertools
import glob
import sys, os
import pickle
from docopt import docopt
args = docopt(__doc__)

all_files = sorted([x for x in glob.glob("all_edms/*") if x[-3:].lower() == "edm"])

print("Found {} .edm files".format(len(all_files)))

start = int(args.get("<start>") or 0)
end = int(args.get("<end>") or len(all_files))

all_files = all_files[start:end]
if args["<start>"] or args["<end>"]:
  print("Processing files {} to {}".format(start, end))


all_data = {}
for i, filename in enumerate(all_files):
  print("\nReading {}: {}".format(i+start, filename))
  edm = EDMFile(filename)
  # Delete all vertex and index data
  for node in itertools.chain(edm.renderNodes, edm.shellNodes):
    if hasattr(node, "vertexData"):
      node.vertexData = (len(node.vertexData), len(node.vertexData[0]))
    if hasattr(node, "indexData"):
      node.indexData = len(node.indexData)
  all_data[os.path.basename(filename)] = edm

print("Writing to dump file")
with open("dump.dat", "wb") as f:
  pickle.dump(all_data, f)

