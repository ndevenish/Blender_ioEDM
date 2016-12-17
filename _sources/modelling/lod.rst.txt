Level of Detail
===============

Level of Detail allows the model to define different geometry according to the
distance that the model is viewed from. This means that you can provide a
highly detailed model up close, but a greatly reduced level of detail when 
viewed from hundreds of meters away.

To start, create an Empty object, and set it to be the parent (Select child,
then parent, then hit Ctrl-P) of the different levels of geometry you want to
control. Normally you would want this geometry to overlap spatially - perhaps
using separate layers to keep things clear, but in this screenshot they have
been placed in different positions for clarity:

.. image:: images/lod_parents.png

Once you've set up the Empty parent, go to the data properties panel and 
tick the 'LOD Root' option:

.. image:: images/lod_panel.png

You will then be able to control the LOD visibility ranges for each of the 
direct children of the Empty. This setting will propogate to any further 
children of these objects. You can specify minimum and maximum distances for
each object, or tick  'No Max', in which case the LOD settings will not 
specify a maximum distance (the DCS engine however, may choose to disregard
this furthest setting when drawing far-away objects).