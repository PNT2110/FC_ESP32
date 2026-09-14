#!/usr/bin/env python3
"""Route remaining islands using SciPy shortest paths; KiCad DRC is authoritative."""
import math
import numpy as np
import pcbnew as p
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate
from shapely.ops import unary_union
from shapely import contains_xy
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra,connected_components
from build_fc import OUT,vec,mm,shape_board

b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
step=.05; origin=72.;n=1121
xx,yy=np.meshgrid(origin+np.arange(n)*step,origin+np.arange(n)*step)
ids=np.arange(2*n*n).reshape(2,n,n)
def xy(v):return p.ToMM(v.x),p.ToMM(v.y)
def items():
    result=[]
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            x,y=xy(pd.GetPosition());w,h=xy(pd.GetSize())
            if pd.GetShape()==p.PAD_SHAPE_CIRCLE:g=Point(x,y).buffer(w/2)
            else:g=rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-pd.GetOrientationDegrees(),origin=(x,y))
            ls=[i for i,ly in enumerate([p.F_Cu,p.B_Cu]) if pd.IsOnLayer(ly)]
            result.append((pd.GetNetname(),ls,g))
    for t in b.GetTracks():
        if isinstance(t,p.PCB_VIA):g=Point(xy(t.GetPosition())).buffer(p.ToMM(t.GetWidth(p.F_Cu))/2);ls=[0,1]
        else:g=LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(p.ToMM(t.GetWidth())/2);ls=[0 if t.GetLayer()==p.F_Cu else 1]
        result.append((t.GetNetname(),ls,g))
    return result
def route(net,width):
    data=items();same=[unary_union([g for name,ls,g in data if name==net and i in ls]).buffer(.001) for i in range(2)]
    pieces=[]
    for i,g in enumerate(same):
        for a in ([g] if g.geom_type=='Polygon' else g.geoms):pieces.append((i,a))
    adj=np.eye(len(pieces),dtype=bool)
    for name,ls,g in data:
        if name!=net or len(ls)!=2:continue
        hits=[j for j,(i,a) in enumerate(pieces) if a.intersects(g)]
        for a in hits:
            for c in hits:adj[a,c]=True
    count,labels=connected_components(coo_matrix(adj),directed=False)
    print(net,'islands',count,flush=True)
    if count<=1:return False
    sh,motors=shape_board();safe=sh.buffer(-.25-width/2-.075)
    safe=safe.difference(unary_union([Point(c).buffer(4.3+.25+width/2+.075) for c in motors])).difference(box(90.9,77.5,109.1,84.1))
    inside=contains_xy(safe,xx,yy)
    clear=[];vc=[]
    for i in range(2):
        obs=unary_union([g for name,ls,g in data if name!=net and i in ls])
        clear.append(inside & ~contains_xy(obs.buffer(.15+width/2+.037),xx,yy))
        vc.append(inside & ~contains_xy(obs.buffer(.15+.3+.037),xx,yy))
    clear=np.array(clear);viaok=vc[0]&vc[1]
    masks=[]
    for group in range(count):
        mask=np.zeros((2,n,n),bool)
        for j,(i,g) in enumerate(pieces):
            if labels[j]==group:mask[i]|=contains_xy(g,xx,yy)
        masks.append(mask&clear)
    sizes=[np.count_nonzero(a) for a in masks];main=int(np.argmax(sizes))
    source=ids[masks[main]];target=np.zeros_like(clear)
    for j,m in enumerate(masks):
        if j!=main:target|=m
    if not len(source) or not np.any(target):raise RuntimeError('No accessible copper islands '+net)
    rows=[];cols=[];weights=[]
    for dy,dx in [(0,1),(1,0),(1,1),(1,-1)]:
        ya=slice(max(0,-dy),min(n,n-dy));yb=slice(max(0,dy),min(n,n+dy))
        xa=slice(max(0,-dx),min(n,n-dx));xb=slice(max(0,dx),min(n,n+dx))
        ok=clear[:,ya,xa]&clear[:,yb,xb]
        a=ids[:,ya,xa][ok];c=ids[:,yb,xb][ok]
        rows.extend([a,c]);cols.extend([c,a]);weights.extend([np.full(len(a),math.hypot(dx,dy)*step)]*2)
    a=ids[0][viaok];c=ids[1][viaok]
    rows.extend([a,c]);cols.extend([c,a]);weights.extend([np.full(len(a),3.)]*2)
    graph=coo_matrix((np.concatenate(weights),(np.concatenate(rows),np.concatenate(cols))),shape=(2*n*n,2*n*n)).tocsr()
    dist,pred,_=dijkstra(graph,directed=True,indices=source,min_only=True,return_predecessors=True)
    goals=ids[target];goal=int(goals[np.argmin(dist[goals])])
    if not np.isfinite(dist[goal]):raise RuntimeError('No path '+net)
    chain=[goal]
    while pred[chain[-1]]>=0:chain.append(int(pred[chain[-1]]))
    chain=chain[::-1];points=[]
    for v in chain:
        ly,y,x=np.unravel_index(v,(2,n,n));points.append((int(ly),float(origin+x*step),float(origin+y*step)))
    # Collinear grid steps become one segment; preserve every layer transition.
    compact=[points[0]]
    for i in range(1,len(points)-1):
        a,c,z=points[i-1:i+2]
        if a[0]==c[0]==z[0] and abs((c[1]-a[1])*(z[2]-c[2])-(c[2]-a[2])*(z[1]-c[1]))<1e-8:continue
        compact.append(c)
    compact.append(points[-1])
    for a,c in zip(compact,compact[1:]):
        if a[0]!=c[0]:
            t=p.PCB_VIA(b);t.SetPosition(vec(a[1],a[2]));t.SetWidth(mm(.6));t.SetDrill(mm(.3));t.SetLayerPair(p.F_Cu,p.B_Cu);t.SetViaType(p.VIATYPE_THROUGH)
        else:
            t=p.PCB_TRACK(b);t.SetStart(vec(a[1],a[2]));t.SetEnd(vec(c[1],c[2]));t.SetWidth(mm(width));t.SetLayer([p.F_Cu,p.B_Cu][a[0]])
        t.SetNet(b.FindNet(net));b.Add(t)
    print('Added',len(compact)-1,'segments; cost',dist[goal],flush=True)
    p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
    return True
for net,width in [('IMU_INT',.15),('VBAT',.8)]:
    for _ in range(8):
        if not route(net,width):break
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
