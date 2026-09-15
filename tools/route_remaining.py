#!/usr/bin/env python3
"""Route remaining islands using SciPy shortest paths; KiCad DRC is authoritative."""
import math
import numpy as np
import pcbnew as p
from shapely.geometry import Point,LineString,Polygon,box
from shapely.affinity import rotate
from shapely.ops import unary_union
from shapely import contains_xy
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.ndimage import distance_transform_edt
import heapq
import argparse
from build_fc import OUT,vec,mm,shape_board

b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
step=.025; origin=59.;n=3281
xx,yy=np.meshgrid(origin+np.arange(n)*step,origin+np.arange(n)*step)
ids=np.arange(2*n*n).reshape(2,n,n)
def xy(v):return p.ToMM(v.x),p.ToMM(v.y)
def items():
    result=[]
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            x,y=xy(pd.GetPosition());w,h=xy(pd.GetSize())
            if pd.GetShape()==p.PAD_SHAPE_CIRCLE:g=Point(x,y).buffer(w/2)
            else:
                r=p.ToMM(pd.GetRoundRectCornerRadius()) if pd.GetShape()==p.PAD_SHAPE_ROUNDRECT else 0
                g=box(x-w/2+r,y-h/2+r,x+w/2-r,y+h/2-r).buffer(r) if r else box(x-w/2,y-h/2,x+w/2,y+h/2)
                g=rotate(g,-pd.GetOrientationDegrees(),origin=(x,y))
            ls=[i for i,ly in enumerate([p.F_Cu,p.B_Cu]) if pd.IsOnLayer(ly)]
            result.append((pd.GetNetname(),ls,g))
    for t in b.GetTracks():
        if isinstance(t,p.PCB_VIA):g=Point(xy(t.GetPosition())).buffer(p.ToMM(t.GetWidth(p.F_Cu))/2);ls=[0,1]
        else:g=LineString([xy(t.GetStart()),xy(t.GetEnd())]).buffer(p.ToMM(t.GetWidth())/2);ls=[0 if t.GetLayer()==p.F_Cu else 1]
        result.append((t.GetNetname(),ls,g))
    return result
def route(net,width):
    data=items()
    if net=='GND' and not getattr(args,'ignore_zones',False):
        p.ZONE_FILLER(b).Fill(b.Zones())
        for zone in b.Zones():
            if zone.GetNetname()!=net:continue
            for i,ly in enumerate((p.F_Cu,p.B_Cu)):
                if not zone.IsOnLayer(ly):continue
                polys=zone.GetFilledPolysList(ly)
                def ring(outline):return [xy(outline.CPoint(j)) for j in range(outline.PointCount())]
                for j in range(polys.OutlineCount()):
                    g=Polygon(ring(polys.COutline(j)),[ring(polys.CHole(j,k)) for k in range(polys.HoleCount(j))])
                    data.append((net,[i],g))
    same=[unary_union([g for name,ls,g in data if name==net and i in ls]).buffer(.001) for i in range(2)]
    pieces=[]
    for i,g in enumerate(same):
        if g.is_empty:continue
        for a in ([g] if g.geom_type=='Polygon' else g.geoms):pieces.append((i,a))
    adj=np.eye(len(pieces),dtype=bool)
    for name,ls,g in data:
        if name!=net or len(ls)!=2:continue
        hits=[j for j,(i,a) in enumerate(pieces) if a.intersects(g)]
        for a in hits:
            for c in hits:adj[a,c]=True
    count,labels=connected_components(coo_matrix(adj),directed=False)
    print(net,'islands',count,flush=True)
    print('Copper bounds:',[(int(labels[j]),i,tuple(round(v,3) for v in g.bounds)) for j,(i,g) in enumerate(pieces)],flush=True)
    if count<=1:return False
    sh,motors=shape_board();safe=sh.buffer(-.25-width/2-.075)
    safe=safe.difference(unary_union([Point(c).buffer(4.3+.25+width/2+.075) for c in motors])).difference(box(91,77.75,109,84.05).buffer(width/2+.05))
    inside=contains_xy(safe,xx,yy)
    clear=[];vc=[]
    for i in range(2):
        obs=unary_union([g for name,ls,g in data if name!=net and i in ls])
        clear.append(inside & ~contains_xy(obs.buffer(.15+width/2+.018),xx,yy))
        vc.append(inside & ~contains_xy(obs.buffer(.15+.3+.018),xx,yy))
    clear=np.array(clear);viaok=vc[0]&vc[1] & ~contains_xy(box(91,77.75,109,84.05).buffer(.35),xx,yy)
    access=clear | np.array([viaok & clear[1],viaok & clear[0]])
    masks=[]
    for group in range(count):
        mask=np.zeros((2,n,n),bool)
        for j,(i,g) in enumerate(pieces):
            if labels[j]==group:mask[i]|=contains_xy(g,xx,yy)
        masks.append(mask&access)
    sizes=[np.count_nonzero(a) for a in masks];print('Accessible grid points:',sizes,flush=True);main=int(np.argmax(sizes))
    if getattr(args,'source_group',None) is not None:main=args.source_group
    if getattr(args,'source_ref',None):
        fp=b.FindFootprintByReference(args.source_ref)
        pad=next(pd for pd in fp.Pads() if pd.GetNetname()==net)
        point=Point(xy(pad.GetPosition()))
        main=next(int(labels[j]) for j,(i,g) in enumerate(pieces) if g.intersects(point) and pad.IsOnLayer((p.F_Cu,p.B_Cu)[i]))
    source=ids[masks[main]];target=np.zeros_like(clear)
    for j,m in enumerate(masks):
        if j!=main:target|=m
    if not len(source) or not np.any(target):raise RuntimeError('No accessible copper islands '+net)
    # Sparse A*: only visit reachable grid points, rather than allocating a
    # graph with millions of edges for the enlarged arms.
    heuristic=distance_transform_edt(~np.any(target,axis=0))*step
    distance={int(v):0.0 for v in source};pred={};queue=[]
    for v in source:
        ly,y,x=np.unravel_index(v,(2,n,n))
        heapq.heappush(queue,(float(heuristic[y,x]),0.0,int(v)))
    goal=None;visited=0
    while queue:
        _,cost,v=heapq.heappop(queue)
        if cost>distance.get(v,float('inf')):continue
        ly,y,x=np.unravel_index(v,(2,n,n))
        if target[ly,y,x]:goal=v;break
        visited+=1
        if visited>2000000:raise RuntimeError('Search budget exceeded '+net)
        neighbors=[]
        for dy,dx in ((0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
            if not clear[ly,y,x]:continue
            ny,nx=y+dy,x+dx
            if not (0<=ny<n and 0<=nx<n) or not clear[ly,ny,nx]:continue
            if dy and dx and (not clear[ly,y,nx] or not clear[ly,ny,x]):continue
            neighbors.append((int(ids[ly,ny,nx]),ny,nx,math.hypot(dx,dy)*step))
        if viaok[y,x]:neighbors.append((int(ids[1-ly,y,x]),y,x,3.0))
        for nv,ny,nx,weight in neighbors:
            new=cost+weight
            if new>=distance.get(nv,float('inf')):continue
            distance[nv]=new;pred[nv]=v
            heapq.heappush(queue,(new+float(heuristic[ny,nx]),new,nv))
    if goal is None:
        np.savez_compressed(OUT/'route_debug.npz',clear=clear,viaok=viaok,source=masks[main],target=target)
        raise RuntimeError('No path '+net)
    chain=[goal]
    while chain[-1] in pred:chain.append(pred[chain[-1]])
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
    print('Added',len(compact)-1,'segments; cost',distance[goal],flush=True)
    p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
    return True
if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('net')
    parser.add_argument('--width',type=float,default=.18)
    parser.add_argument('--source-group',type=int)
    parser.add_argument('--source-ref')
    parser.add_argument('--ignore-zones',action='store_true')
    parser.add_argument('--sense-branch',action='store_true')
    args=parser.parse_args()
    if args.net=='VBAT' and args.width<1.2 and not (args.sense_branch and args.width>=.4 and args.source_group is not None):parser.error('VBAT requires 1.2 mm')
    if args.net.startswith('M') and args.net.endswith('_NEG') and args.width<.8:parser.error('Motor return requires 0.8 mm')
    for _ in range(1 if args.sense_branch else 12):
        if not route(args.net,args.width):break
    p.ZONE_FILLER(b).Fill(b.Zones())
    p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
