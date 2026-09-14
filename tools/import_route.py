#!/usr/bin/env python3
"""Import SES, preserving fixed fanout and project rules; replace only on success."""
import sys
import subprocess
import sexpdata as sx
import pcbnew as p
from build_fc import OUT, child, children, vec, mm

def worker():
    board_path=OUT/'FC_ESP32.kicad_pcb'
    b=p.LoadBoard(str(board_path))
    ses=sx.loads((OUT/'FC_ESP32.ses').read_text())
    routes=child(ses,'routes'); resolution=child(routes,'resolution')
    assert str(resolution[1])=='um'
    scale=1000*float(resolution[2])
    for component in children(child(ses,'placement'),'component'):
        for place in children(component,'place'):
            fp=b.FindFootprintByReference(str(place[1]));assert fp
            assert abs(p.ToMM(fp.GetPosition().x)-float(place[2])/scale)<.001
            assert abs(p.ToMM(fp.GetPosition().y)+float(place[3])/scale)<.001
            assert str(place[4])==('back' if fp.IsFlipped() else 'front'), f'SES side mismatch: {place[1]}'
            delta=(fp.GetOrientationDegrees()-float(place[5])+180)%360-180
            assert abs(delta)<.001, f'SES orientation mismatch: {place[1]}'
    # Validate placement before removing any existing copper. Save only on success.
    temporary = board_path.with_name('route_import.tmp.kicad_pcb')
    tree=sx.loads(board_path.read_text())
    tree=[item for item in tree if not (isinstance(item,list) and item and str(item[0]) in ('segment','via','arc')) or child(item,'locked') is not None]
    temporary.write_text(sx.dumps(tree))
    b=p.LoadBoard(str(temporary))
    def point(v):return (round(p.ToMM(v.x),4),round(p.ToMM(v.y),4))
    fixed_segments=set();fixed_vias=set()
    for track in b.GetTracks():
        if isinstance(track,p.PCB_VIA):fixed_vias.add((track.GetNetname(),point(track.GetPosition())))
        else:fixed_segments.add((track.GetNetname(),track.GetLayer(),tuple(sorted((point(track.GetStart()),point(track.GetEnd()))))))
    for net in children(child(routes,'network_out'),'net'):
        if '--last-pair' in sys.argv and str(net[1]) not in ('EN','BOOST_FB'):continue
        if str(net[1])=='VBAT' and '--fixed-battery' in sys.argv:continue
        ni=b.FindNet(str(net[1]));assert ni,str(net[1])
        for wire in children(net,'wire'):
            path=child(wire,'path');ly={'F.Cu':p.F_Cu,'B.Cu':p.B_Cu}[str(path[1])];w=max(1.2 if str(net[1])=='VBAT' else .8 if str(net[1]).startswith('M') and str(net[1]).endswith('_NEG') else .18,float(path[2])/scale)
            pts=[(float(path[i])/scale,-float(path[i+1])/scale) for i in range(3,len(path),2)]
            for a,z in zip(pts,pts[1:]):
                if a==z:continue
                signature=(str(net[1]),ly,tuple(sorted((tuple(round(v,4) for v in a),tuple(round(v,4) for v in z)))))
                if signature in fixed_segments:continue
                t=p.PCB_TRACK(b);t.SetStart(vec(*a));t.SetEnd(vec(*z));t.SetWidth(mm(w));t.SetLayer(ly);t.SetNet(ni);b.Add(t)
        for via in children(net,'via'):
            assert str(via[1])=='Via[0-1]_600:300_um'
            if (str(net[1]),(round(float(via[2])/scale,4),round(-float(via[3])/scale,4))) in fixed_vias:continue
            v=p.PCB_VIA(b);v.SetPosition(vec(float(via[2])/scale,-float(via[3])/scale));v.SetWidth(mm(.6));v.SetDrill(mm(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(ni);b.Add(v)
    p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
    print('Imported session geometry')

if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker()
    else:
        # A temporary PCB load can save default project settings on KiCad exit.
        # Restore the exact project only after that worker has fully exited.
        project_path=OUT/'FC_ESP32.kicad_pro'
        original_project=project_path.read_bytes()
        try:
            result=subprocess.run([sys.executable,__file__,'--worker',*sys.argv[1:]])
        finally:
            project_path.write_bytes(original_project)
        sys.exit(result.returncode)
