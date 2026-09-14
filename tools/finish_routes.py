#!/usr/bin/env python3
"""Apply explicit, auditable routing finishing steps; rerun DRC after use."""
import json
import math
import argparse
import sexpdata as sx
import pcbnew as p
from build_fc import OUT, child, key, mm

path=OUT/'FC_ESP32.kicad_pcb'

def adc_branch():
    b=p.LoadBoard(str(path))
    resistor=b.FindFootprintByReference('R3')
    assert resistor.GetValue()=='100k 1%'
    assert b.FindFootprintByReference('R4').GetValue()=='100k 1%'
    pad=next(pd for pd in resistor.Pads() if pd.GetNumber()=='1')
    assert pad.GetNetname()=='VBAT'
    def xy(v):return (round(p.ToMM(v.x),6),round(p.ToMM(v.y),6))
    edges={};tracks=[];vias=set()
    for t in b.GetTracks():
        if t.GetNetname()!='VBAT':continue
        if isinstance(t,p.PCB_VIA):vias.add(xy(t.GetPosition()));continue
        if t.GetLayer()!=p.F_Cu:continue
        i=len(tracks);tracks.append(t)
        for v in (t.GetStart(),t.GetEnd()):edges.setdefault(xy(v),[]).append(i)
    position=xy(pad.GetPosition());visited=[]
    while position not in vias:
        choices=[i for i in edges.get(position,[]) if i not in visited]
        assert len(choices)==1,'ADC neck is not an isolated branch'
        i=choices[0];visited.append(i);t=tracks[i]
        a,z=xy(t.GetStart()),xy(t.GetEnd());position=z if position==a else a
        assert len(visited)<20,'ADC branch unexpectedly long'
    length=sum(p.ToMM(tracks[i].GetLength()) for i in visited)
    assert length<3,'ADC branch exceeds reviewed 3 mm length'
    for i in visited:tracks[i].SetWidth(mm(.4))
    # At 4.35 V, 100k+100k draws 21.75 uA. 35 um Cu, 0.4 mm x <=3 mm:
    # R <=3.75 mOhm, drop <=0.082 uV, heating <=1.78 pW.
    report={'net':'VBAT','purpose':'R3/R4 battery ADC sense branch only',
        'width_mm':.4,'length_mm':length,'assumed_copper_um':35,
        'worst_operating_current_a':4.35/200000,'maximum_reviewed_length_mm':3,
        'track_uuids':[str(tracks[i].m_Uuid.AsString()) for i in visited]}
    p.SaveBoard(str(path),b)
    (OUT/'adc_branch_review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

def remove_bad_power():
    report=json.loads((OUT/'drc_current.json').read_text())
    bad=set()
    for violation in report['violations']:
        if violation['type'] not in ('clearance','shorting_items'):continue
        for item in violation['items']:
            if item['description'].startswith('Track [VBAT]'):bad.add(item['uuid'])
    tree=sx.loads(path.read_text())
    tree=[item for item in tree if key(item)!='segment' or str(child(item,'uuid')[1]) not in bad]
    path.write_text(sx.dumps(tree)+'\n')
    print('Removed conflicting VBAT segments:',len(bad))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['adc-branch','remove-bad-power'])
    args=parser.parse_args()
    if args.action=='adc-branch':adc_branch()
    else:remove_bad_power()
