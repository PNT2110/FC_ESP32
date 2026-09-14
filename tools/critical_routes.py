#!/usr/bin/env python3
"""Short switch-node connections and QFN escape routes, before general routing."""
import pcbnew as p
import sexpdata as sx
import sys
from build_fc import OUT, vec, mm, key
if '--append' not in sys.argv:
    a=sx.loads((OUT/'FC_ESP32.kicad_pcb').read_text())
    a=[x for x in a if key(x) not in ('segment','via','arc')]
    (OUT/'FC_ESP32.kicad_pcb').write_text(sx.dumps(a)+'\n')
b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
def pad(ref,num):return next(t for t in fps[ref].Pads() if t.GetNumber()==str(num))
def xy(pad):return (p.ToMM(pad.GetPosition().x),p.ToMM(pad.GetPosition().y))
def route(net,points,width,layer):
    for a,z in zip(points,points[1:]):
        if a==z:continue
        t=p.PCB_TRACK(b);t.SetStart(vec(*a));t.SetEnd(vec(*z));t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
def via(net,at):
    v=p.PCB_VIA(b);v.SetPosition(vec(*at));v.SetWidth(mm(.6));v.SetDrill(mm(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v)
for n,target in [(8,(98.8,109.35)),(9,(99.6,109.9)),(10,(100.4,109.35)),(12,(101.3,109.9)),(22,(100.2,104.4)),(23,(99.3,104.4)),(24,(98.35,104.4))]:
    pd=pad('U2',n);start=xy(pd);net=pd.GetNetname()
    mid=(start[0],start[1]+(.4 if n<13 else -.4))
    route(net,[start,mid,target],.15,p.F_Cu);via(net,target)
for num,net,target in [(2,'BUCK_L2',2),(4,'BUCK_L1',1)]:
    start=xy(pad('U5',num)); end=xy(pad('L1',target))
    escape=(start[0]+.75,start[1])
    route(net,[start,escape],.25,p.B_Cu)
    route(net,[escape,(end[0]-.5,end[1]),end],.7,p.B_Cu)
start=xy(pad('U6',1));end=xy(pad('L2',2))
route('BOOST_SW',[start,(start[0]-.8,start[1]),(end[0]+.6,end[1]),end],.4,p.B_Cu)
p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
print('Critical routes added')
