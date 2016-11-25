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
- Rough parsing of the entire binary file structure
- Importing of the SU-27t cockpit, without getting everything perfectly
- Geometry import, with normals and UV textures
- Simple rotation, translation and visibility animations
- Simple texture materials, IF the textures are in the same directory
  or a subdirectory called "textures"
- Connectors, and UI integration to mark empties as such

What Doesn't Work
-----------------
- Exporting
- Currently only tested with a limited range of EDM files, so e.g. bone-based
  animation is currently not handled and files using it, and any other
  unrecognised nodes will not work.
- Multiple argument animations per object - decisions on the best way to 
  represent this in Blender need to be made (NLA? Custom Action attributes?)
- Complex translation of material settings, including specular, bump maps etc
- Not all the sub-object positions are currently correct

Unanswered Questions
--------------------
- How are the transformations for e.g. the SU-27t foot pedals applied - the 
  transformation data attached to the root render node does not seem sufficient
  for proper positioning
- Exactly how are the animation transformations applied, and the purpose of
  the 'second quaternion' in the `ArgAnimationNode` common base data
- What is the mysterious data block directly before the CONNECTORS/RENDER_NODES
- What is model::RNControlNode (the only index count object not understood)

Installation
============

EDM Modelling tool concepts in Blender
======================================