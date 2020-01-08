# dxf2gcode-pocketMill

dxf2gcode-20191025.zip + https://sourceforge.net/p/dxf2gcode/sourcecode/ci/cbac98d2f079b0c39a5e9b86d5c320f36fa079b5/

This version generally works - conception seems to be ok.
Original hammertownhead modifications are still used in many places but some are removed, some are modified and "reused".

There are many things marked as TODO but it generates quite good g-code output.
This is Alpha version as it does work, but is buggy!

```
grep -Hrn '#TODO:' ./
./dxf2gcode/core/pocketmill.py:505:                    #TODO: check if shape like this will cause problems:
./dxf2gcode/core/pocketmill.py:506:                    #TODO:  \____
./dxf2gcode/core/pocketmill.py:507:                    #TODO:       \
./dxf2gcode/core/pocketmill.py:509:                    #TODO: joints will propably cause problems while calculating
./dxf2gcode/core/pocketmill.py:510:                    #TODO: if we are inside or outside shape
./dxf2gcode/core/pocketmill.py:598:                    #TODO: tweak? yeah, whole circle part
./dxf2gcode/core/pocketmill.py:626:            #TODO: beans shape
./dxf2gcode/core/pocketmill.py:661:            #TODO: rewrite whole rectangle pocket            
./dxf2gcode/core/pocketmill.py:911:            #TODO: is this doing what desribed? remove self.stmove.shape.OffsetXY
./dxf2gcode/core/shape.py:242:        #TODO: end point will change to zig-zag's end
./dxf2gcode/core/shape.py:489:            #TODO: check is this back-to-start still needed
./dxf2gcode/core/rapidmove.py:96:        #TODO: going Z-up can be done as full speed?
```
