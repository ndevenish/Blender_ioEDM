EDM model files - Blender Import/(Export) Addon
===============================================

This is a **HIGHLY EXPERIMENTAL**, totally **UNOFFICIAL** attempt to build a
blender addon to allow importing/exporting of `.EDM` model files, as used in
the flight simulator DCS world. It has been engineered by careful studying of
the binary file format, intuition, research, much guesswork, and many, many
crashes of the model viewer.

In its current state, it allows simple importing functionality whilst the fine
details of the file structure are worked out, and basic exporting. Much of the
data is reasonably easy to interpret, but translating the concepts to Blender
is still a WIP. Also, there may be advanced modelling features used in DCS
world modules that the author does not own, but a universal importer is less a
goal than understanding the file format well enough to build a simple
exporter.

What Works
----------

- Parsing and reading raw data for every .edm file included in DCS world (this
  is reading only, not importing into blender)
- Basic importing of geometry with diffuse texture layers - textures are
  assumed to be in the same folder or a subfolder named 'textures'
- Importing simple rotation, translation and visibility animations
- Connectors, and UI integration to mark empties as such
- Exporting basic meshes with simple animations and single diffuse textures

What Doesn't Work
-----------------
- Exporting anything in a hierarchy is WIP and really fails badly
- Scale animation, and non-quaternion rotation animation isn't exported
- Bone-based animations are not handled at all
- Multiple argument animations per object - decisions on the best way to 
  represent this in Blender need to be made (NLA? Custom Action attributes?)
- Complex translation of material layers, including specular, bump maps etc
- Not all geometry ends up properly placed when importing

Unanswered Questions about the EDM files
----------------------------------------
- Exactly how are the animation transformations applied, and the purpose of
  the 'second quaternion' in the `ArgAnimationNode` common base data
- The `model::RenderNode` objects have a structure mapping vertex data to
  parent data, via `RNControlNode` objects - but there are situations where
  this is not understood (e.g. single-parent but a value in the second field,
  meaning of third field for multi-parent objects, why single-parent objects are
  not counted as control nodes...)
- The interpretation of the material "TEXTURE_COORDINATES_CHANNELS"
- Lots of other details needed on the occasional unknown datablock

Installation
------------

Simply add `io_EDM` as a Blender addon in the usual way (e.g. adding to an
'addons' subdirectory of your  Preferences->Files->Script path and enabling).
This should not be necessary if debugging with `read.py`.

Developers
==========
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

FAQ (WIP)
=========
### Help! My animations aren't exporting!
- Animations with an argument value of `-1` are not exported. Check that you
  have assigned an argument in the action editor
- Scale animations are currently not understood
- Only simple position/rotation keyframe animations are currently implemented

EDM Modelling tool concepts in Blender
======================================
Here is a rough list of how concepts are mapped from 3DS to blender.

|                    | 3DS Max             |   Blender                             |
|--------------------|---------------------|---------------------------------------|
| Connectors         | Named dummy objects | Named empties with the new object property `Is Connector` checked - not all empties are exported |
| Argument Animation | Controllers         | Actions for an object, with an `Argument` property accesible in the dope-sheet properties. |
| Multiple Animations| Controllers         | Not yet implemented - considering using the NLA sheet |
| EDM materials      | 'Make Cool' button  | Directly integrated to material properties - equivalent settings are ported over |
| Collision Shells   | Object properties   | Object Data -> EDM Tools -> Tick "Collision Shell" |
