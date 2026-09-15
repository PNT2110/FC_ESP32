#!/usr/bin/env python3
"""Remove only copper intersecting the antenna; reroute affected nets afterwards."""
import json
import sexpdata as sx
import pcbnew as p
from shapely.geometry import Point,LineString,box
from build_fc import OUT,key,child
path=OUT/'FC_ESP32.kicad_pcb';b=p.LoadBoard(str(path));area=box(91,77.75,109,84.05)
remove=[]
for t in b.GetTracks():
    if isinstance(t,p.PCB_VIA):g=Point(p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)).buffer(p.ToMM(t.GetWidth(p.F_Cu))/2)
    else:g=LineString([(p.ToMM(v.x),p.ToMM(v.y)) for v in (t.GetStart(),t.GetEnd())]).buffer(p.ToMM(t.GetWidth())/2)
    if g.intersection(area).area>1e-6:remove.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname()})
ids={v['uuid'] for v in remove};tree=sx.loads(path.read_text())
tree=[v for v in tree if not (key(v) in ('segment','via','arc') and str(child(v,'uuid')[1]) in ids)]
path.write_text(sx.dumps(tree)+'\n');print(json.dumps(remove,indent=2))
