#!/usr/bin/env python3
import json
import pcbnew as p
from build_fc import OUT

b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
for n in list(b.GetNetsByNetcode().values()):
    if n.GetNetname().startswith('unconnected-') and '/' in n.GetNetname():
        n.SetNetname(n.GetNetname().replace('/','{slash}'))
for fp in b.GetFootprints():
    if fp.GetReference()=='J1':
        for pad in fp.Pads():
            if pad.GetNumber()=='SH':pad.SetNet(b.FindNet('GND'))
p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
cfg=json.loads((OUT/'FC_ESP32.kicad_pro').read_text())
cfg['board']['design_settings']['rules']['min_hole_clearance']=.15
(OUT/'FC_ESP32.kicad_pro').write_text(json.dumps(cfg,indent=2)+'\n')
b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
assert p.ExportSpecctraDSN(b,str(OUT/'FC_ESP32.dsn'))
print('DSN exported')
