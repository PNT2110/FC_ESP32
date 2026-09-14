import pcbnew as pcb
b = pcb.BOARD()
fp = pcb.FootprintLoad('/home/pnt/FC_ESP32/Library/FC_Local.pretty', 'motor')
if not fp: print("not found")
b.Add(fp)
fp.SetPosition(pcb.VECTOR2I(0, 0))
fp.SetOrientationDegrees(135)
print("Pad 1:", fp.FindPadByNumber('1').GetPosition())
print("Pad 2:", fp.FindPadByNumber('2').GetPosition())
