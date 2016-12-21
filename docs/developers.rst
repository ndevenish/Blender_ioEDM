
Developers
==========

This section is information about the Addon and ``.edm`` file format that you
only need if you want to work directly in some way with the addon code or 
interpreting the file yourself.

Source code is available on Github, at https://github.com/ndevenish/Blender_ioEDM.
Current development may be on ``master``, or may be on a specific working branch, 
depending on what is currently in progress.

Notes on development:

- There is a `read.py` file that can be used to launch blender with an instant
  import, to be used e.g. `blender --python read.py -- edmfile.EDM`. This makes
  the cycle of change/debug/rewrite more manageable
- There is also a `write.py`. Use as 
  `blender <filename>.blend --python write.py` and the writer will be run on
  the contents of the loaded blender file.
- Several useful scripts in `utils`. `read_all.py` reads every .edm file in an
  `all_edms/` subdirectory (useful itself as a verification), removes the raw
  vertex and index data, and pickles the entire result into `dump.dat`. The 
  script `read_dump.py` opens this file, defines some useful functions and
  then opens an interpreter (with the local variable `data`). This allows 
  inspection of a large subset (or every single .edm file) simultaneously.
- All of the file->Blender conversion is done in io_EDM.reader, and most of
  the actual functionality is currently in one large function,
  `create_object`
- All parsing of the binary data is done in the `io_EDM.edm` sub-package, and
  is at time of writing separate from Blenders API - although if the API is
  available, the `bpy.mathutils` module is used for 
  `Vector`/`Matrix`/`Quaternion` representations. Most of the edm-specific
  reading is done in `io_EDM.edm.types` module, starting with the `EDMFile`
  class `__init__`.
- A summary of the knowledge gained about the `.EDM` file format can be found
  in the `EDM_Specification.md` file also located in this repository.


In addition, there are several unanswered questions regarding the contents of
the edm file, including:

- Exactly how are the animation transformations applied, and the purpose of
  the 'second quaternion' in the `ArgAnimationNode` common base data
- The interpretation of the material "TEXTURE_COORDINATES_CHANNELS"
- Lots of other details needed on the occasional unknown datablock


.. toctree::
  :maxdepth: 2
  
  EDM_Specification