import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.kicad-python'))
import pcbnew as p
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
root=Path(__file__).resolve().parents[1]
b=p.LoadBoard(str(root/'validation/c3_candidate.kicad_pcb'))
def xy(v):return p.ToMM(v.x),p.ToMM(v.y)
parts=[]
for layer in (p.F_Cu,p.B_Cu):
    shapes=[]
    for z in b.Zones():
        if z.GetNetname()!='GND' or not z.IsOnLayer(layer):continue
        poly=z.GetFilledPolysList(layer)
        def ring(o):return [xy(o.CPoint(i)) for i in range(o.PointCount())]
        for i in range(poly.OutlineCount()):shapes.append(Polygon(ring(poly.COutline(i)),[ring(poly.CHole(i,j)) for j in range(poly.HoleCount(i))]))
    for t in b.GetTracks():
        if t.GetNetname()!='GND' or not t.IsOnLayer(layer):continue
        shapes.append(Point(xy(t.GetPosition())).buffer(p.ToMM(t.GetWidth(layer))/2) if isinstance(t,p.PCB_VIA) else LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(p.ToMM(t.GetWidth())/2))
    g=unary_union(shapes).buffer(.001)
    for a in g.geoms if g.geom_type=='MultiPolygon' else [g]:parts.append((layer,a))
groups=[{i} for i in range(len(parts))]
for f in b.GetFootprints():
    for pad in f.Pads():
        if pad.GetNetname()=='GND':
            hits=[i for i,(ly,g) in enumerate(parts) if pad.IsOnLayer(ly) and g.distance(Point(xy(pad.GetPosition())))<.05]
            if f.GetReference()=='C3':print('C3 groups',hits)
for t in b.GetTracks():
    if not isinstance(t,p.PCB_VIA) or t.GetNetname()!='GND':continue
    hits={i for i,(ly,g) in enumerate(parts) if g.intersects(Point(xy(t.GetPosition())))}
    matched=[s for s in groups if s & hits]
    if matched:
        merged=set.union(*matched)
        groups=[s for s in groups if not s & hits]+[merged]
for s in sorted(groups,key=lambda s:sum(parts[i][1].area for i in s)):
    print('GROUP',[(i,parts[i][0],round(parts[i][1].area,3),parts[i][1].bounds) for i in s])
for i,(ly,g) in enumerate(parts):
    if ly!=p.F_Cu or i==11:continue
    overlap=g.buffer(-.3).intersection(parts[20][1].buffer(-.3))
    if not overlap.is_empty:print('VIA CANDIDATE',i,overlap.representative_point().coords[:],overlap.area)
