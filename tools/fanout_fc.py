#!/usr/bin/env python3
"""Reserve QFN escape paths before autorouting; validate with KiCad afterward."""
import pcbnew as p
from build_fc import OUT, vec, mm
b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
if b.GetTracks():
    raise RuntimeError('Fanout requires a freshly generated, unrouted board')
def escape(ref, number, points, width):
    pad=next(pd for pd in fps[ref].Pads() if pd.GetNumber()==str(number))
    path=[(p.ToMM(pad.GetPosition().x),p.ToMM(pad.GetPosition().y)), *points]
    for a,z in zip(path,path[1:]):
        t=p.PCB_TRACK(b);t.SetStart(vec(*a));t.SetEnd(vec(*z));t.SetWidth(mm(width))
        t.SetLayer(p.F_Cu);t.SetNet(pad.GetNet());t.SetLocked(True);b.Add(t)
    v=p.PCB_VIA(b);v.SetPosition(vec(*path[-1]));v.SetWidth(mm(.6));v.SetDrill(mm(.3))
    v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(pad.GetNet());v.SetLocked(True);b.Add(v)
for number,target in [(8,(98.8,109.35)),(9,(99.6,109.9)),(10,(100.4,109.35)),
                      (12,(101.3,109.9)),(22,(100.2,104.4)),(23,(99.3,104.4)),(24,(98.35,104.4))]:
    pd=next(pd for pd in fps['U2'].Pads() if pd.GetNumber()==str(number))
    x,y=p.ToMM(pd.GetPosition().x),p.ToMM(pd.GetPosition().y)
    escape('U2',number,[(x,y+(.5 if number<13 else -.4)),target],.18)
# 0.25 mm short QFN necks on regulator pins, followed by nominal 0.8 mm routing.
# These are not motor/battery traces; current/thermal review is still required.
for number in (2,4):
    pd=next(pd for pd in fps['U5'].Pads() if pd.GetNumber()==str(number))
    x,y=p.ToMM(pd.GetPosition().x),p.ToMM(pd.GetPosition().y)
    escape('U5',number,[(x-.5,y)],.25)
for number,width in ((1,.4),(4,.18)):
    pd=next(pd for pd in fps['U6'].Pads() if pd.GetNumber()==str(number))
    x,y=p.ToMM(pd.GetPosition().x),p.ToMM(pd.GetPosition().y)
    escape('U6',number,[(x+(.7125 if number==1 else -1),y)],width)
p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
