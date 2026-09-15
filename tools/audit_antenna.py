#!/usr/bin/env python3
"""Check nominal copper geometry inside the fixed ESP32 antenna envelope."""
from pathlib import Path
import json,sys,hashlib
import pcbnew as p
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union
from build_fc import OUT

def polygons(poly):
    def ring(c):return [(p.ToMM(c.CPoint(i).x),p.ToMM(c.CPoint(i).y)) for i in range(c.PointCount())]
    return [Polygon(ring(poly.COutline(i)),[ring(poly.CHole(i,j)) for j in range(poly.HoleCount(i))]) for i in range(poly.OutlineCount())]

def audit(path):
    b=p.LoadBoard(str(path));area=box(91,77.75,109,84.05);hits=[]
    def check(kind,label,g):
        overlap=g.intersection(area).area
        if overlap>1e-6:hits.append({'kind':kind,'item':label,'overlap_mm2':overlap})
    for t in b.GetTracks():
        if isinstance(t,p.PCB_VIA):g=Point(p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)).buffer(p.ToMM(t.GetWidth(p.F_Cu))/2)
        else:g=LineString([(p.ToMM(v.x),p.ToMM(v.y)) for v in (t.GetStart(),t.GetEnd())]).buffer(p.ToMM(t.GetWidth())/2)
        check('track/via',t.GetNetname()+':'+t.m_Uuid.AsString(),g)
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute()==p.PAD_ATTRIB_NPTH:continue
            for layer in (p.F_Cu,p.B_Cu):
                if pad.IsOnLayer(layer):check('pad',fp.GetReference()+'.'+pad.GetNumber(),unary_union(polygons(pad.GetEffectivePolygon(layer))))
    for z in b.Zones():
        if z.GetIsRuleArea():continue
        for layer in (p.F_Cu,p.B_Cu):
            if z.IsOnLayer(layer):check('zone',z.GetNetname()+':'+b.GetLayerName(layer),unary_union(polygons(z.GetFilledPolysList(layer))))
    zones=[z for z in b.Zones() if z.GetZoneName()=='ESP32_ANTENNA_ALL_COPPER']
    enforced=len(zones)==1 and all(zones[0].IsOnLayer(l) for l in (p.F_Cu,p.B_Cu)) and all([zones[0].GetDoNotAllowTracks(),zones[0].GetDoNotAllowVias(),zones[0].GetDoNotAllowPads(),zones[0].GetDoNotAllowZoneFills()])
    return {'pcb_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'passed':not hits and enforced,'keepout_enforced_both_layers':enforced,'antenna_bounds_mm':list(area.bounds),'copper_hits':hits,'scope':'Nominal copper envelope check, not RF range or antenna tuning validation.'}
if __name__=='__main__':
    result=audit(Path(sys.argv[1]) if len(sys.argv)>1 else OUT/'FC_ESP32.kicad_pcb')
    print(json.dumps(result,indent=2));raise SystemExit(not result['passed'])
