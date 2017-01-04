#!/usr/bin/env python3

"""Reads all .edm files in a sub folder and saves data to a dump file.

Usage:
  read_all [<start> [<end>]]
"""
from io_EDM.edm import EDMFile
from traceback import print_exc

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

errors = []
all_data = {}
for i, filename in enumerate(all_files):
  print("\nReading {}: {}".format(i+start, filename))
  try:
    edm = EDMFile(filename)
    # Delete all vertex and index data
    for node in itertools.chain(edm.renderNodes, edm.shellNodes):
      if hasattr(node, "vertexData"):
        node.vertexData = (len(node.vertexData), len(node.vertexData[0]))
      if hasattr(node, "indexData"):
        node.indexData = len(node.indexData)
    all_data[os.path.basename(filename)] = edm
  except KeyboardInterrupt:
    raise
  except Exception as e:
    print("Error processing file;")
    print_exc()
    errors.append((filename, str(e)))

print("Writing to dump file")
with open("dump.dat", "wb") as f:
  dataset = {"data": all_data, "errors": errors}
  pickle.dump(dataset, f)

if errors:
  print("{} Errors occured:".format(len(errors)))
  maxLen = max(len(x[0]) for x in errors)
  for error in errors:
    print("{}    {}".format(error[0].ljust(maxLen), error[1]))
