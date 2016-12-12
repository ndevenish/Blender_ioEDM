#!/usr/bin/env bash

blender() {
  '/Applications/blender.app/Contents/MacOS/blender' $*
}

render() {
  blender $1 --python ./render_iso.py -- $2
}

export() {
 blender $1 -b --python ../utils/write.py -- $2
}

importandrender() {
  blender --python ./readrender.py -- $1 $2
}

testinout() {
  render $1 $2.png
  export $1 $2.edm
  importandrender $2.edm $2e.png
}

#testinout Axis.blend Axis_0
#testinout Axis_SingleFrame.blend Axis_1
testinout DoorAlignment.blend DoorAlign0
testinout DoorAlignment_nokeys.blend DoorAlign1
testinout DoorAlignment_nokeys_noscale.blend DoorAlign2
testinout DoorAlignment_noscale.blend DoorAlign2

