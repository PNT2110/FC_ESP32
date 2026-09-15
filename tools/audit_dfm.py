#!/usr/bin/env python3
"""Geometry audit for mask dams; measurements are nominal, not fab approval."""
import json,sys
from pathlib import Path
import pcbnew as pcb
from shapely.geometry import Polygon
from shapely.ops import unary_union

def polygon(pad,layer):
    ps=pad.GetEffectivePolygon(layer);polys=[]
    for i in range(ps.OutlineCount()):
        c=ps.COutline(i)
        polys.append(Polygon([(pcb.ToMM(c.CPoint(j).x),pcb.ToMM(c.CPoint(j).y)) for j in range(c.PointCount())]))
    return unary_union(polys)

def audit(path):
    b=pcb.LoadBoard(str(path));pads=[];bridges=[]
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(pcb.F_Mask) and p.GetAttribute()!=pcb.PAD_ATTRIB_NPTH:
                copper=polygon(p,pcb.F_Cu)
                pads.append((fp.GetReference()+'.'+p.GetNumber(),p.GetNetname(),copper.buffer(pcb.ToMM(p.GetSolderMaskExpansion(pcb.F_Mask))),copper))
    for i,(ref,net,g,c) in enumerate(pads):
        for ref2,net2,g2,c2 in pads[i+1:]:
            if c.intersects(c2) and net==net2:continue # coincident logical USB contacts
            distance=g.distance(g2)
            if distance <.099:
                bridges.append(dict(a=ref,b=ref2,mask_gap_mm=round(distance,6),copper_gap_mm=round(c.distance(c2),6),same_net=net==net2))
    return dict(board=str(path),mask_dams_below_0_1mm=bridges,back_silk_texts=[t.GetText() for t in b.GetDrawings() if isinstance(t,pcb.PCB_TEXT) and t.GetLayer()==pcb.B_SilkS],track_count=len(list(b.GetTracks())),footprints=len(list(b.GetFootprints())))
if __name__=='__main__':
    result=audit(sys.argv[1]);print(json.dumps(result,indent=2))
