# dxf2gcode-pocketMill

dxf2gcode-20191025.zip + https://sourceforge.net/p/dxf2gcode/sourcecode/ci/cbac98d2f079b0c39a5e9b86d5c320f36fa079b5/

This version generally works.
Some original hammertownhead modifications are still used but most are rewritten completely.
There are many things marked as TODO but it generates quite good g-code output.
This is Beta version - it does work, but is bit buggy.

```
dxf2gcode-pocketMill-Beta$ grep -Hrn '#TODO:' ./
./dxf2gcode/core/pocketmill.py:362:            #TODO: check if shape like this:
./dxf2gcode/core/pocketmill.py:370:            #TODO: joints will propably cause problems
./dxf2gcode/core/pocketmill.py:460:            #TODO: remove?
./dxf2gcode/core/pocketmill.py:483:            #TODO: beans shape:  (____)
./dxf2gcode/core/pocketmill.py:485:            #TODO: "Only lines and <180 angle.
./dxf2gcode/core/pocketmill.py:670:            #TODO: convert it to move based on horizontal and vertical lines only
./dxf2gcode/core/pocketmill.py:735:            #TODO: compensation type 41
./dxf2gcode/core/shape.py:242:                 #TODO: end point will change to zig-zag's end
./dxf2gcode/core/rapidmove.py:96:              #TODO: going Z-up can be done as full speed?
```
