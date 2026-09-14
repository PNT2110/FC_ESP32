import pcbnew as pcb
b = pcb.BOARD()
fp = pcb.FOOTPRINT(b)
b.Add(fp)
fp.SetPosition(pcb.VECTOR2I(0, 0))
fp.SetOrientationDegrees(90)
print(f"Before flip: {fp.GetOrientationDegrees()}")
fp.Flip(pcb.VECTOR2I(0,0), False)
print(f"After flip: {fp.GetOrientationDegrees()}")
