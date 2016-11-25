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

Strings are particularly important in understanding one of the most common
patterns in EDM files, the `named_type`:

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

File-level Structure
--------------------

We now know enough to parse the EDM file, following type definitions. Let's look at what the structure is:

    EDMFile :=
      const b'EDM'
      ushort              version;    # Assumed - 8 in test files
      map<string, uint>   indexA;
      map<string, uint>   indexB;
      named_type          rootNode;   # Practically, model::RootNode
      const int = -1;                 # Always observed thusfar
      unknown_type        unknown;    # See below
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

The next entry is a `named_type` '`rootNode`'. This has always been observed
to be an instance of `model::RootNode`, and is described 

### Unknown data block

Before the object list is an unknown data block. This is the only area of the
EDM file that remains a complete mystery - there does not even appear to be
any kind of size indicator, and it only ever appears to be preceeded by an 
integer value of `-1`. 

The only method of parsing that is currently known is to scan the bytestream 
for the start of the render items section - a `uint` followed by either a 
`string` "CONNECTORS" or "RENDER_NODES" and backtracking the appropriate
amount.

### Render Items

Finally, after the unknown data block comes the world-placed items - a string
identifier followed by a typed list. In practice, this map is observed thusfar
to have a maximum of two entries, though both not need be present:

| String         | Node type           |
|----------------|---------------------|
| `CONNECTORS`   | `model::Connector`  |
| `RENDER_NODES` | `model::RenderNode` |

and the contents are better described in the sections for those types.

It is at this point that the file should have reached it's end - with `0`
bytes left to read, and being fully completed all final cross-checks and 
cross-links can be made, ready for interpretation however one wishes.

Named Types
-----------
At this point 'all that is left' is to define specific types, and allow the
chain to be followed. Let's start with the first major node we are interested
in reading, the root node.

## `model::RootNode`

The `RootNode` object holds information about all of the transformation
nodes and materials used in the model file.

    model::RootNode :=
      string            name;
      uint              unknownA;      
      model::PropertiesSet properties;
      uchar             unknownB[145];
      list<Material>    materials;
      uchar             unknownC[8];
      list<named_type>  nodes;

After the name ("Scene Root") and unknown single integer (Possibly class
version?) comes a properties set - whose only observed contents at time of
writing is `{"__VERSION__": 2}`.

After this is a relatively large section of unknown data, `unknownB`; by inspecting the 
bytes manually it *appears* to be of a structure including a chunk of at least
12 doubles:

    uchar   field1;
    double  field2[12];   
    uchar   unknown[48];

With the first field having values on order of ~2, and the last section 
filled with data that does not appear to have a sensible-looking direct
numerical value.

After the list of materials, which are of a predictable type, the list of
nodes appears to be parent transforms for renderable objects - and includes
simple animation data. Observed types of these nodes are:

- `model::Node`
- `model::TransformNode`
- `model::ArgVisibilityNode`
- `model::ArgAnimationNode`
- `model::ArgScaleNode`
- `model::ArgRotationNode`
- `model::ArgPositionNode`

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
| CULLING              | `uchar`                 | *Unknown*                 |
| DEPTH_BIAS           | `uint`                  | *Unknown*                 |
| MATERIAL_NAME        | `string`                | The base edm Material     |
| NAME                 | `string`                | Material name             |
| SHADOWS              | `uchar`                 | *Unknown*                 |
| TEXTURES             | See Below               |                           |
| TEXTURE_COORDINATE_CHANNELS | 52 bytes         | *Unknown*                 |
| UNIFORMS             | `model::PropertiesSet`  | Shader uniform parameters |
| ANIMATED_UNIFORMS    | `model::PropertiesSet`  | Animated shader parameters|
| VERTEX_FORMAT        | `uint count` + `count` bytes | Layout of vertex data     |

### Blending

This describes the opacity mode.

| Value | Mode setting     |              |
|-------|---------------------------------|
| 0     | None                            |
| 1     | Blend                           |
| 2     | Alpha Test                      |
| 3     | Sum. Blending                   |
| 4     | Z Written Blending (Unverified) |

### Material Name

This is the internal renderer material that should be used, and modified by
the material settings saved in the file. It corresponds to the 3DS edm tools
'Material' option, and should expect a unique value for each of those
settings; the observed values are:

| value                 | edm Material     | Meaning                                  |
|-----------------------|------------------|------------------------------------------|
| `def_material`        | Default          | Basic, diffuse, textured material        |
| `glass_material`      | Glass            | ?(mostly transparent material with gloss)|
| `self_illum_material` | Self-illuminated | Things like panels that need to be lit when there is no light |
| `transparent_self_illum_material` | Transparent Self-illuminated | Used for e.g. indicator bulbs |

### Uniforms

Literally the shader `uniform` values, these values effectively control the
parameters of the material. Two sets are present in the file; `UNIFORMS` are
the basic, fixed properties, and `ANIMATED_UNIFORMS` are `AnimatedProperty`
types including argument and keyframe information - but applied to the same
uniform names. The exact list is currently unknown - perhaps study of the
shaders or more edm examples is required. An example of defined uniforms with
the base material name, taken from a parsed SU-25t cockpit:

```python
{
 'def_material':        {'diffuseShift',
                         'diffuseValue',
                         'reflectionBlurring',
                         'reflectionValue',
                         'specFactor',
                         'specPower'},
 'glass_material':      {'diffuseShift',
                         'diffuseValue',
                         'reflectionBlurring',
                         'reflectionValue',
                         'specFactor',
                         'specPower'},
 'self_illum_material': {'diffuseShift',
                         'multiplyDiffuse',
                         'phosphor',
                         'reflectionValue',
                         'selfIlluminationColor',
                         'specFactor',
                         'specPower'},
 'transparent_self_illum_material': 
                        {'selfIlluminationValue',
                         'diffuseShift'}
}
 ```

### Textures and Texture Coordinate Channels

The `TEXTURES` entry holds a list of actual texture files used in the model
as a simple `uint`-prefixed list. The actual entries include data which is 
unknown but has not been observed 

    TEXTURES := list<textureDEF>

    textureDEF := 
      int           unknown[2];  # Usually seems to be [0, -1]
      string        filename;
      uchar         unknown2[16] # Some data, but not sure what it corresponds to
      osg::Matrixf  unknown3;    # Assume is a texture transformation matrix. Also
                                 # have only observed as identity



### Vertex Format

