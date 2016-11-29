EDM model files - Blender Import/(Export) Addon
===============================================

This is a **HIGHLY EXPERIMENTAL**, totally **UNOFFICIAL** attempt to build a
blender addon to allow importing/exporting of `.EDM` model files, as used in
the flight simulator DCS world. It has been engineered by careful studying of
the binary file format, intuition, research and much guesswork.

In its current state, it allows limited importing whilst the fine details of
the file structure are worked out. Much of the data is reasonably easy to
interpret, but translating the concepts to Blender is still a WIP. Also, there
may be advanced modelling features used in DCS world modules that the author
does not own, but a universal importer is less a goal than understanding the
file format well enough to build a simple exporter.

What Works
----------
- Parsing and reading data for every .edm file included in DCS world
- Importing of basic geometry with diffuse texturing
- Simple rotation, translation and visibility animations
- Simple texture materials, IF the textures are in the same directory
  or a subdirectory called "textures"
- Connectors, and UI integration to mark empties as such

What Doesn't Work
-----------------
- Exporting
- Bone-based animations are not handled at all
- Multiple argument animations per object - decisions on the best way to 
  represent this in Blender need to be made (NLA? Custom Action attributes?)
- Complex translation of material settings, including specular, bump maps etc
- Not all the sub-object transformations are completely understood, or the
  object-splitting process. This means when importing, some objects are
  incorrectly placed.

Unanswered Questions about the EDM files
----------------------------------------
- How are the transformations for e.g. the SU-25t foot pedals applied - the 
  transformation data attached to the root render node does not seem sufficient
  for proper positioning
- Exactly how are the animation transformations applied, and the purpose of
  the 'second quaternion' in the `ArgAnimationNode` common base data
- The meaning of the mysterious data block directly before the
  `CONNECTORS`/`RENDER_NODES` section (after the `RootNode` and `-1` data)
- What is `model::RNControlNode` (the only index count object not understood)
- The `model::RenderNode` have a structure mapping vertex data to parent
  objects - however sometimes this is a paired entry and the purpose of the
  second value is currently unknown
- Lots of other details needed on e.g. the first 12 bytes of `BaseNode`, the
  occasional 

Installation
------------
Simply add `io_EDM` as a Blender addon in the usual way (e.g. adding to your 
Preferences->Files->Addon path and enabling). This should not be necessary
if debugging with `read.py`.

Developers
==========
- There is a `read.py` file that can be used to launch blender with an instant
  import, to be used e.g. `blender --python read.py -- edmfile.EDM`. This makes
  the cycle of change/debug/rewrite more manageable
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

EDM Modelling tool concepts in Blender
======================================
Blender obviously differs from 3DS, and so not everything can be implemented
in exactly the same way. Here is a quick summary of the differences - some of
which are only partially implemented.

|                    | 3DS Max             |   Blender                             |
|--------------------|---------------------|---------------------------------------|
| Connectors         | Named dummy objects | Named empties with the new object property `Is Connector` checked - not all empties are exported |
| Argument Animation | Controllers         | Actions for an object, with an `Argument` property accesible in the dope-sheet properties. |
| Multiple Animations| Controllers         | Not yet implemented - considering using the NLA sheet |
| EDM materials      | 'Make Cool' button  | Directly integrated to material properties - currently only basis material is translated, however. |
