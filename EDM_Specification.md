EDM Specification
=================

This document defines what is known about the structure of the EDM files and
the data contained therein. Not everything is known, and some of it is
guesswork, which will usually be noted. Luckily, the structure is rather
simple - almost everything has a count prepended, object names are stored as
character strings, and there are no pointer-references, so everything can be
read sequentially.


Reading Type definitions
------------------------

C-like struct notation is relatively common for defining binary files, but can
be misleading by e.g. giving the impression that it describes a fixed-size
length of data, which would be incorrect in the case of this file format. 
Therefore, in this document we will use a list-based description with roughly
c-style names; in order to define a type, we present it's name and then a 
list of fields to be read in order - which may be simple or complex - of
fixed size or no. For example, the definition of the string type used is
duplicated here as:

    string :=
      uint  count;
      char  data[count];

indicating that an unsigned int is to be read, followed by a sequence of 
characters - of length determined by the previously read number. The size of
the array could be simple or an expression based on calculation - as in the
vertex counts of the render nodes.

Additionally, there may occasionally require reading of exact constants;
these are indicated by specifying `const` followed by either literal python 
bytestrings (in ASCII) e.g. `const b'EDM'`, or typed declarations, without
names e.g. `const uint = -1`, `const uint = [0,0]` which would require reading 
one (two) unsigned integers and comparing them.

It should also be noted that C++ style template syntax will also be used - both
to represent general instances (in which case `T` will usually be used), and
specific instances - to match exact type names. Improvements for clarity of 
notation are welcome.

Although progress was initially made describing this as a formal language
(in the history of the repository the EDM file was actually parsed as such)
there are exceptions where it may be easier just to describe what is going on.
This should be reasonably obvious from the context.

Basic types and Structures
--------------------------
The .EDM files are all written little-endian, and use the common sizes for the
basic types in both signed and unsigned variants; indicated by a prefix of `u`.
The most common type in the files are probably `unsigned integers`, or
'`uint`'. The lengths are listed here for completeness:

| Type Name   | Size (bytes) |
|-------------|--------------|
| char        | 1            |
| short       | 2            |
| int         | 4            |
| float       | 4            |
| double      | 8            |

In addition to the basic types, there are several fundamental structures that
are repeated throughout the file, starting with `string`. These are length-
prefixed strings, *without* trailing null character:

    string :=
      unsigned_int count
      char         data[count];

And the character data is encoded in **windows-1251** encoding. Strings are
particularly important in understanding one of the most common patterns in EDM
files, the `named_type`:

    named_type :=
      string    typeName;
      typeName  value;

e.g. a string should be read, which tells you the type of the object that needs
to be read next. Usually there is some subset of types that this can be, but
that is entirely dependent on the context.

Lists of some kind are also very common which, here using C++ template syntax
can be seen to be length-prefixed:

    list<T> := 
      uint count;
      T    data[count];

and can be used with `named_type` to represent a generic list of any named
object - and each entry in the list could potentially be a different type.
Related, is the mapping/dictionary type, which is written in the file as a
list of paired keys and values:

    map<T,Q> :=
      List<Pair<T,Q>>

    pair<T,Q> :=
      T key
      Q value

### Math Types

Before moving on to the primary structure of the file, it's helpful to look at
some of the compound math types that are used. The EDM math types are based on
the OpenSceneGraph library, and named accordingly.

Vector types encode both the count and type of the data into their name:

    osg::Vec2f := 
      float a, b;
    
    osg::Vec2d := 
      double a, b;

    osg::Vec3f := 
      float x, y, z;

    osg::Vec3d :=
      double x, y, z;

And matrix types also used in the file:

    osg:Matrixf :=
      float data[16]

    osg::Matrixd :=
      double data[16]

Matrices are written in column-major order, for OpenGL, so may need to be
transposed if desired in row-major. Finally, Quaternions might need to be
read, and the components are in this order:

    osg:Quaternion :=
      float x, y, z, w;

### Properties

Finally, another relatively common meta-pattern is that of properties:

    model::Property<T> :=
      string name
      T      value

They function in a similar way to the `map` structure `pair`, except that
being named types can hold values for anything. Related, as a parent structure
very similar in purpose to a `map` is the `PropertiesSet`:

    model::PropertiesSet := List<named_type>

Where the `named_type` is restricted to instances of `model::Property<T>`
(and that includes subtypes e.g. `model::AnimatedProperty`). This type is
tracked separately as a 'named' type in the main file index.

Animated properties are similar, but hold keyframe data for a specific 
animation number (`argument`):

    model::AnimatedProperty<T> :=
      string        name;
      uint          argument;
      uint          count;
      model::Key<T> keyFrames[count];

    model::Key<T> :=
      double   frame;
      T        value;

The keyframe type, as appears in the main file index, does not
directly correspond to the exact type name. The translation is relatively
simple, however:

| Animated Property Type | Keyframe Type |
|------------------------|---------------|
| `float`                | `key::FLOAT`  |
| `osg::Vec2f`           | `key::VEC2F`  |
| `osc::Vec3f`           | `key::VEC3F`  |

So e.g. an `model::AnimatedProperty<osg::Vec2f>` contains a type of 
`model::Key<key::VEC2F>`.

File-level Structure
--------------------

We now know enough to parse the EDM file, following type definitions. Let's look at what the structure is:

    EDMFile :=
      const b'EDM'
      ushort              version;    # 8 in all current EDM files
      map<string, uint>   indexA;
      map<string, uint>   indexB;
      named_type          rootNode;   # Always model::RootNode
      uint                nodeCount;
      named_type          nodes[nodeCount];
      uint                nodeParents[nodeCount];
      map<string,list<named_type>>   renderItems;

followed by an EOF. Let's start by looking at the two string-uint indexes.

They translate as a lookup table of (almost entirely) typename-to-count values
and seem to act as a crosscheck for the file. `indexA` seems to function as a
tracking index exclusively for direct children of the `rootNode` and render
items (e.g. types that only appear as members of the `model::RootNode`, or in
the `renderItems` map). Here is an example of the contents of this index, in
python dictionary form:

```python
{
  'model::ArgAnimationNode': 216,
  'model::RenderNode':       200,
  'model::RootNode':           1,
  'model::ArgVisibilityNode':168, 
  'model::Connector':         28,
  'model::TransformNode':     28, 
  'model::Node':               1
}
```

The second index seems to function in a similar way, except listing named
types that appear elsewhere, as members of the node objects:

```python
{'__gi_bytes': 906501,
 '__gv_bytes': 5599044,
 'model::AnimatedProperty<float>': 6,
 'model::ArgAnimationNode::Position': 111,
 'model::ArgAnimationNode::Rotation': 118,
 'model::ArgVisibilityNode::Arg': 169,
 'model::ArgVisibilityNode::Range': 169,
 'model::Key<key::FLOAT>': 12,
 'model::Key<key::POSITION>': 322,
 'model::Key<key::ROTATION>': 601,
 'model::PropertiesSet': 23,
 'model::Property<float>': 107,
 'model::Property<osg::Vec2f>': 23,
 'model::Property<osg::Vec3f>': 6,
 'model::Property<unsigned int>': 1,
 'model::RNControlNode': 203}
```

With the addition of the first two fields; `__gi_bytes`, which is a count of
the number of raw bytes of vertex indexing data, and `__gv_bytes` which is
the number of raw vertex data bytes. Presumably this is used as a quick
evaluation of how much video memory is required to load the model.

These can be useful whilst parsing the data, because they provide a cross-
check that you have properly read objects, and also provided clues as to how
certain objects were broken down. Presumably building them is critically
important for writing new EDM files.

### The Root Node

The next entry is a `named_type` - but is always a named instance of 
`model::RootNode`.

### Transformation Nodes

There is then a list of named transformation and animation nodes, always
starting with an empty `model::Node`. The types of node that appear in this
list are:

- `model::Node`
- `model::TransformNode`
- `model::Bone`
- `model::LodNode`
- `model::BillboardNode`
- `model::ArgAnimationNode`
- `model::ArgScaleNode`
- `model::ArgRotationNode`
- `model::ArgPositionNode`
- `model::ArgAnimatedBone`
- `model::ArgVisibilityNode`

Following this list is a rather opaque block of data - on the surface it 
appears to be a `-1` followed by a large block of mostly zeros, with only
occasional data. This block is simply an array of transformation node
references - each `uint` holds the transformation node index of the parent
in it's transformation chain, with `-1` indicating that the node has no
parent - the reason most of the data is zero is that mostly there is no 
need for a complex chain of parent transformation. 

This tree of parenting allows for complex animations and skeletal structures
that allow multiple animations to be applied to each render item.

### Render Items

Finally, after the unknown data block comes the world-placed objects - a string
identifier followed by a typed list. This can have up to four entries, though
any (or all) may be missing:

| String         | Node types                                |
|----------------|-------------------------------------------|
| `CONNECTORS`   | `model::Connector`                        |
| `RENDER_NODES` | `model::RenderNode`, `model::SkinNode`, `model::FakeOmniLightsNode`, `model::FakeSpotLightsNode` |
| `SHELL_NODES`  | `model::ShellNode`, `model::SegmentsNode` |
| `LIGHT_NODES`  | `model::LightNode`                        |

with the contents described in the sections for those types.

It is at this point that the file should have reached it's end - with `0`
bytes left to read, and being fully completed all final cross-checks and 
cross-links can be made, ready for interpretation however one wishes.

Named Types
-----------
At this point 'all that is left' is to define specific types, and allow the
chain to be followed. Let's start with the first major node we are interested
in reading, the root node.

## `model::RootNode`

The `RootNode` object holds information about all of the materials in the
scene, and a chunk of vector data that is not well understood.

    model::RootNode :=
      string            name;
      uint              version;      # Asssumed
      model::PropertiesSet properties;
      uchar             unknownA;     # Either 0, 1 or 2
      osg::Vec3d        boundingBoxMin;
      osg::Vec3d        boundingBoxMax;
      osg::Vec3d        unknownB[4];
      list<Material>    materials;
      uint              unknownC[2];

The object begins like all other `Node`-derived objects, with the name, class
version and properties dictionary. Although the properties are often empty
for `Node`-derived objects, in the `RootNode` this always has the contents
`{"__VERSION__": 2}` - a value which appears to be important
when writing (it changes the layout of the unknown areas of the class?)

After a single char which is not understood, We then have two `Vector3d`
objects. These define the bounding box of the model - the first being the
lower corner of the box, the second the upper corner. In the model viewer, 
this defines the range that the axes are displayed (e.g. the X axis is shown
from `boundingBoxMin.x` to `boundingBoxMax.x`.

After this is another chunk of unknown double data, `unknownB`.

The list of materials contains the bulk of the contents of the class - in 
an easy-to-read list format. After these, there is a small
unknown block - that seems to always consist of a single `uint = 0`, followed
by another number.

## `Material`

Material objects are entirely constructed as a single `map`:
  
    Material :=
      map<string, X>

However, the type, labelled `X` of the value corresponding to the string
depends on that string e.g. if the string is `UNIFORMS` then `X` is a 
`model::PropertiesSet`. If the string is `BLENDING` then `X` is a single 
`uchar`.

The possible entries in the material map are:

| Key `string`         | Entry type              | Interpretation            |
|----------------------|-------------------------|---------------------------|
| BLENDING             | `uchar`                 | Opacity mode enum         |
| CULLING              | `uchar`                 | *Unknown* (0 or 1)        |
| DEPTH_BIAS           | `uint`                  | *Unknown* (0 or 1)        |
| MATERIAL_NAME        | `string`                | The base edm Material     |
| NAME                 | `string`                | Material name             |
| SHADOWS              | `uchar`                 | *Unknown* (0, 2 or 3)     |
| TEXTURES             | See Below               |                           |
| TEXTURE_COORDINATE_CHANNELS | `uint count` + `count` ints | *Unknown* (10, 11 or 12 counts) |
| UNIFORMS             | `model::PropertiesSet`  | Shader uniform parameters |
| ANIMATED_UNIFORMS    | `model::PropertiesSet`  | Animated shader parameters|
| VERTEX_FORMAT        | `uint count` + `count` bytes | Layout of vertex data     |

### Blending

This describes the opacity mode.

| Value | Mode setting                    |
|-------|---------------------------------|
| 0     | None                            |
| 1     | Blend                           |
| 2     | Alpha Test                      |
| 3     | Sum. Blending                   |
| 4     | Z Written Blending (Unverified, and unused in any .edm file) |

### Material Name

This is the internal renderer material that should be used, and modified by
the material settings saved in the file. It corresponds to the 3DS edm tools
'Material' option, and should expect a unique value for each of those
settings; the observed values are:

| value                 | 3DS Material     | Meaning                         |
|-----------------------|------------------|---------------------------------|
| `additive_self_illum_material`           |                                 |
| `bano_material`       |                  |                                 |
| `building_material`   |                  |                                 |
| `chrome_material`     |                  |                                 |
| `color_material`      |                  |                                 |
| `def_material`        | Default          | Basic, diffuse, textured material |
| `fake_omni_lights`    |                  |                                 |
| `fake_spot_lights`    |                  |                                 |
| `forest_material`     |                  |                                 |
| `glass_material`      | Glass            | ?(mostly transparent material with gloss) |
| `lines_material`      |                  |                                 |
| `mirror_material`     |                  |                                 |
| `self_illum_material` | Self-illuminated | Things like panels that need to be lit when there is no light |
| `transparent_self_illum_material` | Transparent Self-illuminated | Used for e.g. indicator bulbs |

### Uniforms

Literally the shader `uniform` values, these values effectively control the
parameters of the material. Two sets are present in the file; `UNIFORMS` are
the basic, fixed properties, and `ANIMATED_UNIFORMS` are `AnimatedProperty`
types including argument and keyframe information - but applied to the same
uniform names. A list of all materials/uniforms observed in all `.edm` files
included in DCS World:

| Base Material Name               | Uniforms                                 |
|----------------------------------|------------------------------------------|
| `additive_self_illum_material`   | `diffuseShift`, `multiplyDiffuse`, `phosphor`, `reflectionValue`, `selfIlluminationColor`, `selfIlluminationValue`, `specFactor`, `specMapValue`, `specPower` |
| `bano_material`                  | `banoDistCoefs`, `diffuseValue` |
| `building_material`              | `diffuseValue`, `reflectionValue`, `selfIlluminationValue`, `specFactor`, `specPower` |
| `chrome_material`                | `diffuseShift`, `diffuseValue`, `normalMapValue`, `reflectionValue`, `specFactor`, `specMapValue`, `specPower` |
| `color_material`                 | `color`, `diffuseValue`, `reflectionValue`, `selfIlluminationValue`, `specPower` |
| `def_material`                   | `diffuseShift`, `diffuseValue`, `reflectionValue`, `specFactor`, `specMapValue`, `specPower` |
| `fake_omni_lights`               | `shiftToCamera`, `sizeFactors` |
| `fake_spot_lights`               | `coneSetup`, `sizeFactors` |
| `forest_material`                | `diffuseValue`, `reflectionValue`, `selfIlluminationValue`, `specFactor`, `specPower` |
| `glass_material`                 | `diffuseValue`, `reflectionValue`, `specFactor`, `specPower` |
| `lines_material`                 | `color`, `selfIlluminationValue` |
| `mirror_material`                | `diffuseShift`, `diffuseValue`, `reflectionValue`, `specFactor`, `specPower` |
| `self_illum_material`            | `diffuseShift`, `multiplyDiffuse`, `phosphor`, `reflectionValue`, `selfIlluminationColor`, `selfIlluminationValue`, `specFactor`, `specPower` |
| `transparent_self_illum_material`|`diffuseShift`, `selfIlluminationValue` |


### Textures and Texture Coordinate Channels

The `TEXTURES` entry holds a list of actual texture files used in the model
as a simple `uint`-prefixed list. The full interpretation needs more work to
be understood. The structure is:

    TEXTURES := list<textureDEF>

    textureDEF := 
      int           index;
      int           unknown;     # ALWAYS -1
      string        filename;
      uint          unknown2[4]  # Some data - ALWAYS [2, 2, 10, 6]
      osg::Matrixf  unknown3;    # Assume is a texture transformation matrix. 
                                 # Almost always identity - very rare to not

Index seems to indicate the type of texture; this is derived from observation 
of the associated filenames - this possibly affects which UV map/set of vertex
data is used to map the texture:

| Index | Role       | Typical texture name examples                         |
|-------|------------|-------------------------------------------------------|
| 0     | Diffuse    | Wide variety, as would be expected                    |
| 1     | Normals    | Names tend to include `_normal` or `_nm`, or sometimes `_bump` |
| 2     | Specular   | `_spec`, `_specular` makes this also relatively obvious |
| 3     | Numerals   | `bf-109k-4_bort_number`, `mi_8_bort_number`, `su-27_numbers` |
| 4     | Glass Dirt | `tf51d-cpt_glassdirt`, `mig-29_cpt_glassdirt` (only two exist) |
| 5     | Damage     | `bulle_dam`, `f86f_damage`, `tu22m3_damage_konsol_l`  |
| 8     | ?          | Lots of `Flame_*`, `BANO`, `_light` - possible emittance? |
| 9     | ?          | `mi_8_tex_1_ao` (only example in all .edm files)      |
| 10    | Damage Normals | `mi_8_damage_normal`, `f-86f_glass_damage_nm`     |
| 11    | ?          | `tu-22m3_glass_color_spec`, `kab_glass_spec_color` (only two) |
| 12    | ?          | `f-86f_chrom`, `sa342_int_cpit_glass_reflect`, `chromic_blur` (only three) |

The `TEXTURE_COORDINATE_CHANNELS` field is defined as:

    TEXTURE_COORDINATE_CHANNELS :=
      uint count;
      uint channels[count];

And remains a mystery for now. There is usually 10, 11 or 12 channels, and
most of the channels are filled with `-1` (e.g. `0xFFFFFFFF`). Best guess is
that it is some kind of mask - an error in writing resulted in one of the
channels being written with value `1`, which led to the model viewer error
`Empty Channel`. Writing zero for the first channel (by guesswork and
inspection of other .edm files) seems to work for the simple one-texture case.

### Vertex Format
Specifies the format of the vertex data; The render nodes store the total
count and stride, but is otherwise an opaque block of float values. This
defines how those floats are used:

    VERTEX_FORMAT :=
      uint    count;
      uchar   channels[count];

Most entries have a count of 26 - however a few (possibly older?) models have
an entry of 24 - so it is not always safe to assume the length. Each of the 
channels counts has a fixed meaning, and observed lengths:

| Channel | Length | Represents                                              |
|---------|--------|---------------------------------------------------------|
| 0       | 4      | Position data. The last of these appears to relate to vertex group for parenting purposes |
| 1       | 3      | Normals data                                            |
| 2       | 3      |                                                         |
| 3       | 3      |                                                         |
| 4       | 2      | Texture UV                                              |
| 5       | 2      |                                                         |
| 6       | 2      |                                                         |
| 7       | 2      |                                                         |
| 8       | 2      |                                                         |
| 20      | 3      |                                                         |
| 21      | 4      | Bone data related - number of bone references? (appears to be x2 entries in vertex data) |
| 24      | 3      |                                                         |
| 25      | 3      |                                                         |

## Nodes

### `model::Node`

The `Node` node is used both as an empty node, and also is the basis for many
of the other nodes - which all share the identical starting layout:

    model::Node :=
      string        name;
      uint          version;
      propertiesset props;

As with `RootNode` (which we can also see matches this exact layout) we have
assumed that the `uint` field is representative of class version - this seems
to have no other meaning, and makes a lot of sense in terms of allowing the
schema to evolve over time.

### `model::TransformNode`

    model::TransformNode :=
      model::Node   base;
      osg::Matrixd  transform;

### `model::LodNode`

    model::LodNode :=
      model::Node             base;
      uint                    count;
      model::LodNode::Level   levels[count];

    model::LodNode::Level :=
      float data[4];

The exact interpretation of the level data is unknown.

### `model::Bone`

    model::Bone :=
      model::Node   base;
      osg::Matrixd  m1;
      osg::Matrixd  m2;

### `model::BillboardNode`

Not much is understood about this node other than the size:

    model::BillboardNode :=
      model::Node   base;
      uchar         unknown[154];

## Animation Nodes

### `model::ArgAnimationNode`, Position, Rotation and Scale

This is a special node, as the nodes `model::ArgPositionNode`,
`model::ArgRotationNode`, and `model::ArgScaleNode` are all parsed exactly the
same way - but just appear to be written when the animation only has a single
(position, rotation, scale) channel of animation:

    model::ArgRotationNode := model::ArgAnimationNode
    model::ArgPositionNode := model::ArgAnimationNode
    model::ArgScaleNode    := model::ArgAnimationNode

The actual `ArgAnimationNode` contains quite a lot of data:

    model::ArgAnimationNode := 
      osg::Matrixd      tf_Matrix;
      osg::Vec3d        tf_Position;
      osg::Quaternion   tf_Quat1;
      osg::Quaternion   tf_Quat2;
      osg::Vec3d        tf_Scale;

      list<model::ArgAnimationNode::Position>  positionData;
      list<model::ArgAnimationNode::Rotation>  rotationData;
      list<model::ArgAnimationNode::Scale>     scaleData;

The set of transformation `tf_` values are assumed to describe the chain of
transformation in order to properly process the vertex data (in a `RenderNode`
object referencing this node as it's parent). The exact application is currently
unknown; at the moment a working best-guess is something along the lines of:

    Transform = tf_Matrix * tf_Position * tf_Quat1 * keyRotation * tf_Scale

Where each of the objects has obviously been transformed to be compatible with
the other (e.g. so you can apply a matrix to a quaternion...). The entry
`keyRotation` is the current best guess for where the keyframe rotation value
is applied.

In addition, the matrix `tf_Matrix` seems to have the extra role of swapping
axis - animation vertex data seems to be kept in the original 3DS coordinate
system. This is an area of active research.

The position and rotation entries are relatively similar; just an animation
argument value followed by a list of keys:

    model::ArgAnimationNode::Position :=
      uint                              argument;
      list<model::Key<key::POSITION>>   keys;

    model::ArgAnimationNode::Rotation :=
      uint                              argument;
      list<model::Key<key::ROTATION>>   keys;

    model::Key<key::POSITION> := 
      double          frame;
      osg::Vector3d   value;

    model::Key<key::ROTATION> :=
      double            frame;
      osg::Quaternion   value;

However, scale appears to be handled slightly differently, and appears to
contain two sets of keys, of currently unknown interpretation - one set
of four doubles, and one of three:

    model::ArgAnimationNode::Scale :=
      uint argument;
      list<ScaleKeyA>   keys;
      list<ScaleKeyB>   keys2;

    ScaleKeyA :=
      double      frame;
      osg::Vec4f  value;

    ScaleKeyB :=
      double      frame;
      osg::Vec3f  value;


### `model::ArgAnimatedBone`

The bone animation node is the same as the `ArgAnimationNode`, but with the
addition of an extra transfomation matrix:

    model::ArgAnimatedBone :=
      model::ArgAnimationNode   base;
      osg::Matrixd              xf_Bone;

The application of this extra transformation is also currently unknown,
because at time-of-writing skeletal animation/skinning in the EDM files has
not been investigated.

### `model::ArgVisibilityNode`

Not containing a transformation - only a list of toggles for on/off visibility,
this is a much simpler node:

    model::ArgVisibilityNode :=
      model::Node   base;
      list<model::ArgVisibilityNode::Arg>   visibilityData;

    model::ArgVisibilityNode::Arg :=
      uint                                    argument;
      list<model::ArgVisibilityNode::Range>   keys;

    model::ArgVisibilityNode::Range :=
      double frameStart;
      double frameEnd;

Where the two key entries are the start and end ranges of visibility. Note that
in cases where the object 'becomes visible' and stays that way, over the range
of the animation argument, the `frameEnd` value will often be very high - 
values of `1e300` are not uncommon.

## Object Nodes

### Connector

Connectors are a very simple named connection to a parent transformation node:

    model::Connector :=
      model::BaseNode   base;
      uint              parent;
      uint              unknown;

And will always have a `name` entry in the base node reading. The parent field
is the index of the parent transformation node - that is, the index in the
`RootNode.nodes` list that was read earlier in the file. The last entry
remains unknown - all known examples of .edm files have this field zero, so
does not appear to be important. The parent is simply the index

### Render Nodes

`RenderNode` objects generally contain very large amounts of vertex and index
data, the actual renderable geometry of the edm file:

    model::RenderNode :=
      model::BaseNode   base;
      uint              unknown;   # Always zero in known files
      uint              materialId;
      PARENTDATA        parentData;
      VERTEXDATA        vertexData;
      INDEXDATA         indexData;

The `materialId` is the index of the material to be applied to this data -
the index in the `RootNode.materials` list. The `VERTEXDATA` and `INDEXDATA`
types are shared with the `model::ShellNode` and `model::SkinNode` types.

Let's start with the par§ent data, which is slightly unusual - the exact layout
depends on the value of the first count entry:

    PARENTDATA :=
      const uint count = 1;
      uint  parent;
      int   unknown;

Or, if `count` > 1:

    PARENTDATA :=
      uint          count;
      PARENT_ENTRY  parents[count];

    PARENT_ENTRY :=
      uint  parent;
      int   unknownA;
      int   unknownB;

Along with the parent reference ID, which refers to the index in the
`RenderNode.nodes` array, the exact interpretation of the unknown fields is
not completely unknown, we do have some idea - the unknown fields *appear* to
relate to sections of the vertex data in the node.

However, the vertex data itself has four entries for it's 'position' field -
and the fourth entry definitely refers to the index in this
`PARENTDATA.parents` array. Thus, having range information here would appear
to be redundant.

This layout is required because, for efficiency reasons; many separate objects
with identical materials are often merged into a single `RenderNode`, and the
associated data used for separation.

This structure also appears to be related to the index count of
`model::RNControlNode`. In particular: there appears to be one `RNControlNode`
in the index for each *additional* parent data entry - that is, the sum of
`model::RNControlNode` = `PARENTDATA.count - 1` for every `model::RenderNode` 
in the .edm file.

This link was derived by observing numeric correlation and testing the
hypothesis on every existing .edm file. It appears to be correct.

Let's move away from this unhappy state of affairs and examine the vertex
data:

    VERTEXDATA :=
      uint    count;
      uint    stride;
      float   data[count*stride];

Where the data array could also be interpreted identically as:

    VERTEXDATA :=
      uint    count;
      uint    stride;
      VERTEX   data[count];

    VERTEX :=
      float   data[stride];

e.g. an array of `float` vertex data, where each set of `stride` values
corresponds to a single vertex. The exact value of `stride`, and the meaning
of each of the vertex entries - corresponds to the vertex format specified in
the associated material. The amount of data in this array - e.g.  `count *
stride * sizeof(float)` is counted towards the index bytes counter -
`__gv_bytes` for `model::RenderNode`.

With vertex data we also need a way to represent faces; that is where the
index array comes in:

    INDEXDATA :=
      uchar         data_type;
      uint          entries;
      uint          unknown;
      INDEXVALUE    data[entries];

Where the INDEXVALUE type depends on the value of the `data_type` field:

| `data_type`  | Type of each entry |
|--------------|--------------------|
| 0            | `uchar`            |
| 1            | `ushort`           |
| 2            | `uint`             |

and each entry refers to the index of a single vertex in the `vertexData` 
array. Allowing the data type to be varied allows saving of space because the
number of vertices in a single object can - sometimes - run up to the hundreds
of thousands, but would be a complete waste of space for the majority of
models with, say, less than 60k vertices.

The `unknown` field is either 0, 1 or 5 - most commonly 5. What *is* known is
that the count of the index data is not always a multiple of three - but this
does not appear to correlate with the value of the unknown field (which is
what would be expected if, say, the unknown field represented face type).

The physical data read in the index array - `entries * sizeof(data_type)` is
counted towards the index bytes counter `__gi_bytes`, for `model::RenderNode`.

#### `model::SkinNode`

`SkinNode` describes a set of vertex data designed to be layered over `Bone`
nodes. It is relatively similar to `RenderNode` except instead of parent 
transforms it explicitly lists a set of bones:

    model::SkinNode :=
      model::Node   base;
      uint          material;
      list<uint>    bones;
      uint          unknown;

      VERTEXDATA    vertexData;
      INDEXDATA     indexData;

Where the `bones` refer to offset indexes in the `RootNode.nodes` array. The
vertex data for such nodes will have bone index/weight data in - the indices
for which can be extracted by inspecting the material vertex format. Because it
is rendered data, the vertex and index data for these nodes contribute to the
`__gv_bytes` and `__gi_bytes` index counts.

#### `model::FakeOmniLightsNode`

    model::FakeOmniLightsNode :=
      model::Node   base;
      uint          unknown[5]
      uint          count;
      double        data[count*6];

#### `model::FakeSpotLightsNode`

    model::FakeSpotLightsNode :=
      model::Node   base;
      uchar         unknown[101];

### Light Nodes

The general interpretation of the `model::LightNode` is unknown, however it
does contain a properties set of light properties - which does _not_ count
towards the general index count of `propertiesset`:

    model::LightNode :=
      model::Node     base;
      uint            unknownA;
      uchar           unknownB;
      propertiesset   lightProperties;
      uchar           unknownC;

### Shell Nodes

Shell nodes appear to define the collision shells for models; as such, they do
not appear to have a material reference. They do, however, embed their own 
vertex format:

    model::ShellNode :=
      model::Node     base;
      uint            unknown;
      VERTEX_FORMAT   vertex_format;
      VERTEXDATA      vertexData;
      INDEXDATA       indexData;

Where the vertex and index raw data read for these nodes contribute to the
`__cv_bytes` and `__ci_bytes` index counters.

#### `model:SegmentsNode`

Only the layout is known for these nodes:

    model::SegmentsNode :=
      model::Node     base;
      uint            unknown;
      list<model::SegmentsNode::Segments>   segments;

    model::SegmentsNode::Segments :=
      float   data[6];
