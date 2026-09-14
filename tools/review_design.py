#!/usr/bin/env python3
"""Read-only pin/net and geometry evidence for the datasheet review.

Expected active-pin mappings below were transcribed from manufacturer pin tables
and the requested interface assignments, independently of build_fc.py.
This is connectivity evidence, not a proof of electrical/flight operation.
"""
import collections, csv, hashlib, json, math, re
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/datasheet_audit'
OUT.mkdir(exist_ok=True)
board=p.LoadBoard(str(ROOT/'FC_ESP32/FC_ESP32.kicad_pcb'))
fps={f.GetReference():f for f in board.GetFootprints()}
expected={
 'U1':{1:'GND',2:'+3V3',3:'EN',6:'IMU_INT',7:'VBAT_ADC',8:'UART1_RX',9:'PWM4',10:'PWM1',11:'PWM2',12:'PWM3',13:'UART1_TX',15:'GND',25:'BOOT',26:'I2C_SDA',27:'FLOW_RX',28:'FLOW_TX',30:'SPI_SCK',31:'SPI_MISO',33:'IMU_CS',34:'UART0_RX',35:'UART0_TX',36:'I2C_SCL',37:'SPI_MOSI',38:'GND',39:'GND'},
 'U2':{8:'+3V3_IMU',9:'SPI_MISO',10:'REGOUT',11:'GND',12:'IMU_INT',13:'+3V3_IMU',18:'GND',20:'GND',22:'IMU_CS',23:'SPI_SCK',24:'SPI_MOSI'},
 'U3':{1:'GND',2:'UART0_RX',3:'UART0_TX',4:'+3V3',5:'USB_DP',6:'USB_DM',13:'DTR',14:'RTS',15:'GND',16:'+3V3'},
 'U4':{1:'USB_DM',2:'GND',3:'USB_DP',4:'USB_DP',5:'VBUS',6:'USB_DM'},
 'U5':{1:'+3V3',2:'BUCK_L2',3:'GND',4:'BUCK_L1',5:'VSYS',6:'VSYS',7:'VSYS',8:'VINA',9:'GND',10:'+3V3',11:'GND'},
 'U6':{1:'BOOST_SW',2:'GND',3:'+3V3',4:'BOOST_FB',5:'+5V_FLOW',6:'+3V3'},
 'Q5':{1:'BASE_EN',2:'RTS',3:'EN'},'Q6':{1:'BASE_BOOT',2:'DTR',3:'BOOT'},
 'D5':{1:'VSYS',2:'VBAT'},'D6':{1:'VSYS',2:'VBUS'},
 'J2':{1:'GND',2:'+5V_FLOW',3:'FLOW_TX',4:'FLOW_RX'},
 'J3':{1:'VBAT',2:'GND'},'J8':{1:'+3V3',2:'GND',3:'I2C_SDA',4:'I2C_SCL'},
 'J9':{1:'+3V3',2:'GND',3:'UART1_TX',4:'UART1_RX'},
 'J1':{'A1':'GND','A12':'GND','B1':'GND','B12':'GND','A4':'VBUS','A9':'VBUS','B4':'VBUS','B9':'VBUS','A5':'CC1','B5':'CC2','A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM'},
}
for i in range(1,5):
 expected[f'Q{i}']={1:f'GATE{i}',2:'GND',3:f'M{i}_NEG'}
 expected[f'D{i}']={1:'VBAT',2:f'M{i}_NEG'}
 expected[f'J{i+3}']={1:'VBAT',2:f'M{i}_NEG'}
expected={ref:{str(k):v for k,v in pins.items()} for ref,pins in expected.items()}
tree=ET.parse(OUT/'fresh.net').getroot()
sch={}
for net in tree.findall('./nets/net'):
 for node in net.findall('node'):sch[(node.get('ref'),node.get('pin'))]=(net.get('name'),node.get('pinfunction',''))
design={c['ref']:c for c in json.loads((ROOT/'FC_ESP32/design.json').read_text())}
errors=[];rows=[];checked=0
def normalize(net):return '' if net.startswith('unconnected-') else net
for ref,fp in sorted(fps.items()):
 for pad in fp.Pads():
  num=pad.GetNumber();net=normalize(pad.GetNetname());sn,label=sch.get((ref,num),('',''))
  want=expected.get(ref,{}).get(num)
  if want is not None:
   checked+=1
   if net!=want or normalize(sn)!=want:errors.append([ref,num,'datasheet/request',want,net,sn])
  declared=design.get(ref,{}).get('nets',{}).get(num)
  if declared is not None and (net!=declared or normalize(sn)!=declared):errors.append([ref,num,'design/netlist/PCB',declared,net,sn])
  rows.append([ref,fp.GetValue(),num,label,sn,net,want or '',round(p.ToMM(pad.GetPosition().x),6),round(p.ToMM(pad.GetPosition().y),6),fp.GetOrientationDegrees(),'B' if fp.IsFlipped() else 'F'])
# Reserved/flash pins must not be repurposed. U2 EP is intentionally unverified.
for ref,numbers in {'U1':[4,5,14,16,17,18,19,20,21,22,23,24,29,32], 'U2':[1,2,3,4,5,6,7,14,15,16,17,19,21], 'U3':[7,8,9,10,11,12]}.items():
 for pad in fps[ref].Pads():
  if pad.GetNumber() in map(str,numbers) and normalize(pad.GetNetname()):errors.append([ref,pad.GetNumber(),'expected unused',pad.GetNetname()])
with (OUT/'pin_audit.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['Reference','Value','Pad','Schematic_pin_name','Schematic_net','PCB_net','Independent_expected_net','X_mm','Y_mm','Footprint_angle_deg','Side']);w.writerows(rows)
totals=collections.defaultdict(float);widths=collections.defaultdict(set)
for track in board.GetTracks():
 if isinstance(track,p.PCB_VIA):continue
 net=track.GetNetname();totals[net]+=p.ToMM(track.GetLength());widths[net].add(p.ToMM(track.GetWidth()))
positions={ref:[p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y)] for ref,f in fps.items()}
geometry={'net_copper':{net:{'total_segment_length_mm':length,'widths_mm':sorted(widths[net])} for net,length in sorted(totals.items())},'component_centers_mm':positions,
 'center_distances_mm':{f'{a}-{z}':math.dist(positions[a],positions[z]) for a,z in [('U5','L1'),('U5','C12'),('U5','C13'),('U6','L2'),('U6','C17'),('U6','R12'),('U6','R13'),('J1','U4')]}}
(OUT/'geometry.json').write_text(json.dumps(geometry,indent=2))
antenna=box(91,77.75,109,84.05)  # U1 footprint's actual antenna rectangle.
hits=[];overlaps=[]
for t in board.GetTracks():
 if isinstance(t,p.PCB_VIA):
  g=Point(p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)).buffer(p.ToMM(t.GetWidth(p.F_Cu))/2)
  layer='F.Cu+B.Cu'
 else:
  g=LineString([(p.ToMM(v.x),p.ToMM(v.y)) for v in (t.GetStart(),t.GetEnd())]).buffer(p.ToMM(t.GetWidth())/2)
  layer=board.GetLayerName(t.GetLayer())
 cut=g.intersection(antenna)
 if cut.area>1e-6:
  overlaps.append(cut);hits.append({'net':t.GetNetname(),'layer':layer,'uuid':t.m_Uuid.AsString(),'intersection_area_mm2':cut.area})
(OUT/'antenna_audit.json').write_text(json.dumps({'passed':not hits,'antenna_bounds_mm':list(antenna.bounds),'overlap_union_area_mm2':unary_union(overlaps).area,'track_via_hits':hits,'note':'Existing U1 rule areas forbid tracks on F.Cu but allow B.Cu tracks; clean DRC does not prove all-layer antenna clearance.'},indent=2))
fw=(ROOT/'firmware/main/main.c').read_text()
pin_macros={'MOTOR1_PIN':25,'MOTOR2_PIN':26,'MOTOR3_PIN':27,'MOTOR4_PIN':33,'MPU_MISO_PIN':19,'MPU_MOSI_PIN':23,'MPU_CLK_PIN':18,'MPU_CS_PIN':21,'MPU_INT_PIN':34,'OPTFLOW_TX_PIN':17,'OPTFLOW_RX_PIN':16,'I2C_MASTER_SDA_IO':4,'I2C_MASTER_SCL_IO':22,'EXP_TX_PIN':14,'EXP_RX_PIN':32}
for name,number in pin_macros.items():
 match=re.search(r'#define\s+'+name+r'\s+(?:GPIO_NUM_)?(\d+)',fw)
 if not match or int(match[1])!=number:errors.append(['firmware',name,number])
sources=[Path(__file__),*ROOT.glob('FC_ESP32/*.kicad_sch'),ROOT/'FC_ESP32/FC_ESP32.kicad_pcb',ROOT/'FC_ESP32/FC_ESP32.kicad_pro',ROOT/'FC_ESP32/design.json',*ROOT.glob('firmware/main/*.[ch]'),ROOT/'firmware/main/Kconfig.projbuild',ROOT/'firmware/sdkconfig.defaults',*ROOT.glob('data_sheet/*.pdf')]
result={'connectivity_pass':not errors,'antenna_pass':not hits,'automated_checks_pass':not errors and not hits,'independently_checked_pad_instances':checked,'all_pad_instances_logged':len(rows),'errors':errors,'explicit_uncertainties':['MPU6500 exposed pad 25 is not a numbered signal in the local datasheet; grounded in design, assembly guidance still required.','Pin connectivity does not prove power integrity, assembly fit, motor current or stable flight.'],'sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}}
(OUT/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='sha256'},indent=2))
raise SystemExit(bool(errors or hits))
