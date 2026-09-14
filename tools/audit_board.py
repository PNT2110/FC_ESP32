#!/usr/bin/env python3
"""Check design invariants not enforced by ordinary KiCad DRC."""
import json
import math
from pathlib import Path
import pcbnew as p
from build_fc import OUT

def main():
    b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
    fps={f.GetReference():f for f in b.GetFootprints()}
    failures=[]
    def require(condition,message):
        if not condition:failures.append(message)
    def xy(fp):return p.ToMM(fp.GetPosition().x),p.ToMM(fp.GetPosition().y)
    require(abs(p.ToMM(b.GetDesignSettings().GetBoardThickness())-.8)<1e-6,'Board thickness must be 0.8 mm')
    centers=[(66.6,66.6),(133.4,66.6),(133.4,133.4),(66.6,133.4)]
    moved=[]
    for i,center in enumerate(centers,1):
        require(math.dist(xy(fps['H'+str(i)]),center)<.001,f'H{i}: motor center moved')
        old=tuple(72.2 if v<100 else 127.8 for v in center)
        pos=xy(fps['J'+str(i+3)])
        moved.append({'reference':'J'+str(i+3),'position_mm':pos,'inward_shift_mm':math.dist(pos,old)})
        require(abs(math.dist(pos,old)-1.5)<.002,f'J{i+3}: expected 1.5 mm inward shift')
        require(math.dist(pos,(100,100))<math.dist(old,(100,100)),f'J{i+3}: not moved inward')
    require(abs(fps['J2'].GetOrientationDegrees()-90)<.001,'J2 must face the right outside edge (90 degrees)')
    require(abs(fps['C3'].GetOrientationDegrees()-180)<.001,'C3 EN escape orientation must be 180 degrees')
    expected={
        'J2':{'1':'GND','2':'+5V_FLOW','3':'FLOW_TX','4':'FLOW_RX'},
        'U1':{'6':'IMU_INT','7':'VBAT_ADC','8':'UART1_RX','9':'PWM4',
              '10':'PWM1','11':'PWM2','12':'PWM3','13':'UART1_TX','26':'I2C_SDA',
              '27':'FLOW_RX','28':'FLOW_TX','30':'SPI_SCK','31':'SPI_MISO',
              '33':'IMU_CS','36':'I2C_SCL','37':'SPI_MOSI'},
    }
    for ref,pins in expected.items():
        actual={pd.GetNumber():pd.GetNetname() for pd in fps[ref].Pads()}
        for number,net in pins.items():require(actual.get(number)==net,f'{ref}.{number}: expected {net}')
    rules=json.loads((OUT/'FC_ESP32.kicad_pro').read_text())['net_settings']['classes']
    widths={c['name']:c['track_width'] for c in rules}
    for name,width in [('Battery',1.2),('MotorPower',.8),('LogicPower',.4),('Default',.18)]:
        require(abs(widths.get(name,0)-width)<1e-6,f'{name} netclass changed')
    reviewed=set()
    review_path=OUT/'adc_branch_review.json'
    if review_path.exists():
        review=json.loads(review_path.read_text())
        require(review['width_mm']==.4 and review['length_mm']<=review.get('maximum_reviewed_length_mm',3),'Invalid ADC branch exception')
        require(fps['R3'].GetValue()=='100k 1%' and fps['R4'].GetValue()=='100k 1%','ADC branch resistor values changed')
        reviewed=set(review['track_uuids'])
    narrow=[]
    for track in b.GetTracks():
        if isinstance(track,p.PCB_VIA):continue
        net=track.GetNetname();w=p.ToMM(track.GetWidth())
        minimum=1.2 if net=='VBAT' else .8 if net in ('M1_NEG','M2_NEG','M3_NEG','M4_NEG') else .18
        # Explicit, very short regulator/QFN escapes are separately documented.
        if net=='VBAT' and str(track.m_Uuid.AsString()) in reviewed:minimum=.4
        if w+1e-6<minimum:narrow.append({'net':net,'width_mm':w})
    require(not narrow,'Undersized tracks detected')
    result={'passed':not failures,'failures':failures,'motor_pads':moved,
            'j2_orientation_deg':fps['J2'].GetOrientationDegrees(),'netclass_widths_mm':widths,
            'narrow_tracks':narrow}
    (OUT/'invariant_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return int(bool(failures))

if __name__=='__main__':raise SystemExit(main())
