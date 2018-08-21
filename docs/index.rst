Welcome to Blender_ioEDM
========================

This is a **HIGHLY EXPERIMENTAL**, totally **UNOFFICIAL** attempt to build a
blender addon to allow importing/exporting of `.EDM` model files, as used in
the flight simulator DCS world. It has been engineered by careful studying of
the binary file format, intuition, research, much guesswork, and many, many
crashes of the model viewer.

Firstly, an important note:

    **This tool may only be used for private purposes and may in no way be used
    for extracting models which may directly or indirectly be used for commercial
    gain or promotion of any commercial product i.a games, films, media, or artwork.**

e.g. it should be obvious that this is for modding for DCS world and any
intellectual property of ED remains the intellectual property of ED.

In its current state, it allows simple importing functionality whilst the fine
details of the file structure are worked out, and basic exporting. Much of the
raw ``.edm`` .data is reasonably easy to interpret, but translating the
concepts to Blender is still a WIP. Also, there may be advanced modelling
features used in DCS world modules that the author does not own, but a
universal importer is less a goal than understanding the file format well
enough to build a simple exporter.

What Works
----------

- Parsing and reading raw data for every .edm file included in DCS world (this
  is reading only, not importing into blender)
- Basic importing of geometry with diffuse texture layers - textures are
  assumed to be in the same folder or a subfolder named 'textures'
- Importing simple rotation, translation and visibility animations
- Connectors, and UI integration to mark empties as such
- Exporting basic meshes with simple animations and single diffuse textures
- Exporting collision shells 

What Doesn't Work
-----------------
- Exporting anything in a hierarchy is WIP and really fails badly
- Scale animation, and non-quaternion rotation animation isn't exported
- Bone-based animations are not handled at all
- Multiple argument animations per object
- Complex translation of material layers, including specular, bump maps etc
- Not all geometry ends up properly placed when importing

.. FAQ (WIP)
.. =========
.. ### Help! My animations aren't exporting!
.. - Animations with an argument value of `-1` are not exported. Check that you
..   have assigned an argument in the action editor
.. - Scale animations are currently not understood
.. - Only simple position/rotation keyframe animations are currently implemented

.. EDM Modelling tool concepts in Blender
.. ======================================
.. Here is a rough list of how concepts are mapped from 3DS to blender.

.. |                    | 3DS Max             |   Blender                             |
.. | Connectors         | Named dummy objects | Named empties with the new object property `Is Connector` checked - not all empties are exported |
.. | Argument Animation | Controllers         | Actions for an object, with an `Argument` property accesible in the dope-sheet properties. |
.. | Multiple Animations| Controllers         | Not yet implemented - considering using the NLA sheet |
.. | EDM materials      | 'Make Cool' button  | Directly integrated to material properties - equivalent settings are ported over |
.. | Collision Shells   | Object properties   | Object Data -> EDM Tools -> Tick "Collision Shell" |


.. toctree::
  :maxdepth: 2
  
  installation.rst
  modelling.rst
  developers.rst

  



.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
