#!/usr/bin/env python3
"""Fill ground over the actual board outline, retaining footprint keepouts."""
import pcbnew as p
from build_fc import OUT, mm, shape_board

def main():
    b = p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
    # Idempotent: replace only generated ground zones.
    for zone in list(b.Zones()):
        if not zone.GetIsRuleArea() and zone.GetNetname() == 'GND':
            b.Remove(zone)
    outline, _ = shape_board()
    for layer in (p.F_Cu, p.B_Cu):
        zone = p.ZONE(b)
        zone.SetLayer(layer)
        zone.SetNet(b.FindNet('GND'))
        zone.SetLocalClearance(mm(.2))
        zone.SetMinThickness(mm(.2))
        zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
        poly = zone.Outline()
        poly.NewOutline()
        for x, y in list(outline.exterior.coords)[:-1]:
            poly.Append(mm(x), mm(y))
        b.Add(zone)
    # Routing widths are never silently changed here.
    p.ZONE_FILLER(b).Fill(b.Zones())
    p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'), b)

if __name__ == '__main__':
    main()
