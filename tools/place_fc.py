#!/usr/bin/env python3
"""Place within the mechanical outline, retaining functional neighborhood targets."""
import json
import math
from pathlib import Path
import pcbnew as p
from shapely.geometry import box, Point, MultiPoint
from shapely.affinity import translate, rotate
from shapely.ops import unary_union
from build_fc import OUT, shape_board, vec, mm

def rect(b):
    return box(p.ToMM(b.GetX()),p.ToMM(b.GetY()),p.ToMM(b.GetRight()),p.ToMM(b.GetBottom()))

def geometry(fp):
    pad_shapes=[]
    for pad in fp.Pads():
        x,y=p.ToMM(pad.GetPosition().x),p.ToMM(pad.GetPosition().y)
        w,h=p.ToMM(pad.GetSize().x),p.ToMM(pad.GetSize().y)
        pad_shapes.append(rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-pad.GetOrientationDegrees(),origin=(x,y)))
    pads=unary_union(pad_shapes)
    points=[]
    courtyard=[]
    for g in fp.GraphicalItems():
        if g.GetLayer() in (p.F_CrtYd,p.B_CrtYd):
            if g.GetShape()==p.SHAPE_T_SEGMENT:
                points += [(p.ToMM(v.x),p.ToMM(v.y)) for v in (g.GetStart(),g.GetEnd())]
            else:courtyard.append(rect(g.GetBoundingBox()))
    if points:courtyard.append(MultiPoint(points).convex_hull.buffer(.025))
    if not courtyard:
        courtyard=[rect(g.GetBoundingBox()) for g in fp.GraphicalItems() if g.GetLayer() in (p.F_Fab,p.B_Fab) and isinstance(g,p.PCB_SHAPE)]
    body=unary_union([pads,*courtyard]).convex_hull
    return body,pads

def main():
    b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
    sh,motors=shape_board()
    inside=sh.buffer(-.25)
    holes=unary_union([Point(x,y).buffer(4.4) for x,y in motors])
    antenna=box(90.9,77.5,109.1,84.1)
    fps={f.GetReference():f for f in b.GetFootprints() if not f.GetReference().startswith('H')}
    locked=['U1','J1','U2','J2','J8','J4','J5','J6','J7']
    preferred=locked+['U5','L1','U6','L2','U3','J3','Q1','Q2','Q3','Q4','D1','D2','D3','D4','D5','D6','Q5','Q6','U4']
    preferred += sorted((ref for ref in fps if ref not in preferred),key=lambda r:-geometry(fps[r])[0].area)
    placed={'F':[],'B':[]}; all_th=[]; result={}
    for ref in preferred:
        fp=fps[ref];side='F' if fp.GetLayer()==p.F_Cu else 'B'
        body,pads=geometry(fp)
        x0,y0=p.ToMM(fp.GetPosition().x),p.ToMM(fp.GetPosition().y)
        candidates=[(0,0)]
        if ref not in ('U1','J1','J2','J8','J4','J5','J6','J7'):
            step=.25
            # single-side fallback needs a wider search around the pre-spread guess
            candidates += sorted([(i*step,j*step) for i in range(-64,65) for j in range(-64,65) if i or j], key=lambda ij:ij[0]**2+ij[1]**2)
        for dx,dy in candidates:
            pb=translate(body,dx,dy);pp=translate(pads,dx,dy)
            if not inside.covers(pp):continue
            if pp.intersects(holes):continue
            if ref!='U1' and pb.intersects(antenna):continue
            # Never trade assembly clearance for visual density.
            if any(pb.intersects(old.buffer(.05)) for old in placed[side]):continue
            if any(pp.intersects(old.buffer(.2)) for old in all_th):continue
            # A component body must not straddle a motor opening.
            if pb.intersects(holes):continue
            fp.SetPosition(vec(x0+dx,y0+dy))
            placed[side].append(pb)
            for pad in fp.Pads():
                if pad.GetAttribute() in (p.PAD_ATTRIB_PTH,p.PAD_ATTRIB_NPTH):all_th.append(rect(pad.GetBoundingBox()))
            result[ref]=dict(x=round(x0+dx,3),y=round(y0+dy,3),side=side,offset_mm=round(math.hypot(dx,dy),2))
            break
        else:
            raise RuntimeError('No valid position: '+ref)
    p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
    (OUT/'placement.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Placed',len(result),'components; max move',max(v['offset_mm'] for v in result.values()))

if __name__=='__main__':main()
