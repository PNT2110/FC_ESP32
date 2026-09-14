#!/usr/bin/env python3
"""Place ground stitching vias with obstacle/edge checks; KiCad DRC is authoritative."""
from shapely.geometry import Point,box
from shapely.ops import unary_union
import pcbnew as p
from route_remaining import b,items,shape_board,vec,mm,OUT
shape,motors=shape_board()
safe=shape.buffer(-.65).difference(unary_union([Point(c).buffer(4.95) for c in motors])).difference(box(90.5,77,109.5,84.5))
obstacles=unary_union([g for name,layers,g in items() if name!='GND']).buffer(.5)
existing=unary_union([Point(p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)).buffer(.8) for t in b.GetTracks() if isinstance(t,p.PCB_VIA)])
count=0
for ix in range(60,141,2):
 for iy in range(60,141,2):
  point=Point(ix,iy)
  if not safe.contains(point) or obstacles.intersects(point) or existing.intersects(point):continue
  v=p.PCB_VIA(b);v.SetPosition(vec(ix,iy));v.SetWidth(mm(.6));v.SetDrill(mm(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(b.FindNet('GND'));b.Add(v);count+=1
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
print('Added ground stitching vias:',count)
