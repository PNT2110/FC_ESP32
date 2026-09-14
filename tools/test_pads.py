import pcbnew as pcb
b = pcb.BOARD()
fp = pcb.FootprintLoad('/usr/share/kicad/footprints/Diode_SMD.pretty', 'D_SMA')
b.Add(fp)
fp.SetPosition(pcb.VECTOR2I(0, 0))
fp.Flip(pcb.VECTOR2I(0,0), pcb.FLIP_DIRECTION_LEFT_RIGHT)
fp.SetOrientationDegrees(135)
print("Pad 1:", fp.FindPadByNumber('1').GetPosition())
print("Pad 2:", fp.FindPadByNumber('2').GetPosition())
