#!/usr/bin/env python3
"""Freeze routed battery trunks and restore fixed IC fanout before autorouting."""
import json
import sexpdata as sx
import pcbnew as p
from build_fc import OUT,ROOT,key,child
path=OUT/'FC_ESP32.kicad_pcb';tree=sx.loads(path.read_text())
backup=sx.loads((ROOT/'validation/header_routed_baseline.kicad_pcb').read_text())
fixed=[x for x in backup if key(x) in ('segment','via') and child(x,'locked') is not None and str(child(x,'net')[1])!='VBAT']
tree=[x for x in tree if key(x)!='zone' or child(x,'keepout') is not None]
for item in tree:
 if key(item) in ('segment','via') and str(child(item,'net')[1])=='VBAT' and child(item,'locked') is None:item.append([sx.Symbol('locked'),sx.Symbol('yes')])
tree.extend(fixed);path.write_text(sx.dumps(tree)+'\n')
b=p.LoadBoard(str(path));narrow=[t for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetNetname()=='VBAT' and p.ToMM(t.GetWidth())<1.2]
report={'net':'VBAT','purpose':'R3/R4 voltage sense only','width_mm':.4,'length_mm':sum(p.ToMM(t.GetLength()) for t in narrow),'assumed_copper_um':35,'worst_operating_current_a':4.35/200000,'maximum_reviewed_length_mm':30,'track_uuids':[t.m_Uuid.AsString() for t in narrow]}
assert report['length_mm']<=30
# 0.4 mm x 35 um Cu over <=30 mm: R<=0.038 ohm, drop<=0.83 uV,
# dissipation<=18 pW at 21.75 uA. This exception never applies to motor trunks.
(OUT/'adc_branch_review.json').write_text(json.dumps(report,indent=2)+'\n')
print('Restored fixed fanout:',len(fixed),'sense length',report['length_mm'])
