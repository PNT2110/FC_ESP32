"""Plot actual nearby copper on both layers for local routing review."""
from pathlib import Path
import pcbnew as p
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle

root=Path(__file__).resolve().parents[1]
b=p.LoadBoard(str(root/'validation/c3_candidate.kicad_pcb'))
def xy(v):return p.ToMM(v.x),p.ToMM(v.y)
fig,axes=plt.subplots(1,2,figsize=(16,9))
colors={'GND':'#aaaaaa','VBAT':'#e8a000','BOOST_FB':'#bf00cf','EN':'#00aaaa','+5V_FLOW':'#f33'}
for ax,layer in zip(axes,[p.F_Cu,p.B_Cu]):
    for zone in b.Zones():
        if zone.GetNetname()!='GND' or not zone.IsOnLayer(layer):continue
        poly=zone.GetFilledPolysList(layer)
        for j in range(poly.OutlineCount()):
            o=poly.COutline(j)
            ax.add_patch(Polygon([xy(o.CPoint(i)) for i in range(o.PointCount())],color='#cccccc',alpha=.5))
            for k in range(poly.HoleCount(j)):
                o=poly.CHole(j,k)
                ax.add_patch(Polygon([xy(o.CPoint(i)) for i in range(o.PointCount())],color='white'))
    for t in b.GetTracks():
        if not t.IsOnLayer(layer):continue
        color=colors.get(t.GetNetname(),'#3577b8')
        if isinstance(t,p.PCB_VIA):ax.add_patch(Circle(xy(t.GetPosition()),p.ToMM(t.GetWidth(layer))/2,color=color))
        else:
            a,z=xy(t.GetStart()),xy(t.GetEnd())
            ax.plot([a[0],z[0]],[a[1],z[1]],color=color,lw=p.ToMM(t.GetWidth())*35,solid_capstyle='round')
    for f in b.GetFootprints():
        x,y=xy(f.GetPosition())
        if 84<x<94 and 88<y<98:
            if layer==p.F_Cu:ax.text(x,y,f.GetReference(),fontsize=9)
            for pd in f.Pads():
                if not pd.IsOnLayer(layer):continue
                poly=pd.GetEffectivePolygon(layer)
                outline=poly.COutline(0)
                ax.add_patch(Polygon([xy(outline.CPoint(i)) for i in range(outline.PointCount())],color=colors.get(pd.GetNetname(),'#3577b8')))
                a,z=xy(pd.GetPosition());ax.text(a,z,pd.GetNumber(),fontsize=7)
    ax.set(xlim=(81,93),ylim=(98,88),aspect='equal',title=b.GetLayerName(layer))
    ax.grid(alpha=.3)
fig.savefig(root/'validation/c3_copper.png',dpi=150)
for f in b.GetFootprints():
    x,y=xy(f.GetPosition())
    if 85<x<92 and 90<y<97:
        print(f.GetReference(),xy(f.GetPosition()),f.GetOrientationDegrees(),[(pd.GetNumber(),pd.GetNetname(),xy(pd.GetPosition())) for pd in f.Pads()])
for t in b.GetTracks():
    if not isinstance(t,p.PCB_VIA) and t.GetNetname()=='VBAT' and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])<90 and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])>87:
        print('VBAT',str(t.m_Uuid.AsString()),b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()),p.ToMM(t.GetWidth()))
