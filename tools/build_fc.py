#!/usr/bin/env python3
"""Reproducible KiCad 10 FC prototype. Run with system Python and pcbnew."""
from pathlib import Path
import copy
import shutil
import sys
import csv
import json
import math
import os
import uuid
import subprocess
import xml.etree.ElementTree as ET
import sexpdata as sx
import pcbnew as pcb
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'FC_ESP32'
LIB = ROOT / 'Library' / 'FC_Local'
PRETTY = LIB / 'FC_Local.pretty'
PLUGIN = pcb.PCB_IO_MGR.FindPlugin(pcb.PCB_IO_MGR.KICAD_SEXP)
S = sx.Symbol
def key(a): return str(a[0]) if isinstance(a, list) and a else ''
def children(a, k): return [x for x in a if key(x) == k]
def child(a, k): return next((x for x in a if key(x) == k), None)
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'fc-esp32-v1/' + s))
def q(s): return json.dumps(str(s))
def dump(a): return sx.dumps(a)
def mm(v): return pcb.FromMM(v)
def vec(x, y): return pcb.VECTOR2I(mm(x), mm(y))
def layers(*ids):
    a=pcb.LSET()
    for i in ids:a.AddLayer(i)
    return a

SYMS = {}
SOURCES = {}
def symbol(name, file, original=None):
    data = sx.loads(Path(file).read_text())
    names = {x[1]: x for x in children(data, 'symbol')}
    original = original or next(iter(names))
    a = copy.deepcopy(names[original])
    base = child(a, 'extends')
    if base:
        parent = copy.deepcopy(names[base[1]])
        a.remove(base)
        a.extend(children(parent, 'symbol'))
    a[1] = name
    for sub in children(a, 'symbol'):
        sub[1] = name + '_' + '_'.join(str(sub[1]).split('_')[-2:])
    for prop in children(a, 'property'):
        prop[:] = [x for x in prop if key(x) != 'id']
    SYMS[name] = a
    SOURCES[name] = str(Path(file).relative_to(ROOT)) if str(file).startswith(str(ROOT)) else str(file)
    return name

def rect_symbol(name, pins, prefix='U'):
    # Pins are explicit datasheet numbers, not a guessed connector pin order.
    n = math.ceil(len(pins) / 2)
    h = max(5.08, (n + 1) * 1.27)
    a = [S('symbol'), name, [S('pin_names'), [S('offset'), 0.508]],
         [S('in_bom'), S('yes')], [S('on_board'), S('yes')]]
    for p, val, y in [('Reference', prefix, h+2.54), ('Value', name, -h-2.54)]:
        a.append(sx.loads(f'(property {q(p)} {q(val)} (at 0 {y} 0) (effects (font (size 1.27 1.27))))'))
    sub = [S('symbol'), name+'_0_1', sx.loads(f'(rectangle (start -7.62 {h}) (end 7.62 {-h}) (stroke (width 0.254) (type default)) (fill (type background)))')]
    for i, (num, label, typ) in enumerate(pins):
        side = 0 if i < n else 1
        x = -10.16 if not side else 10.16
        y = (n-1)*1.27 - (i % n)*2.54
        sub.append(sx.loads(f'(pin {typ} line (at {x} {y} {0 if not side else 180}) (length 2.54) (name {q(label)} (effects (font (size 1.0 1.0)))) (number {q(num)} (effects (font (size 1.0 1.0)))))'))
    a.append(sub)
    SYMS[name] = a
    SOURCES[name] = 'Datasheet-derived local symbol'
    return name

def normalize_model(fp, name):
    # Model-only alignment. The electrical footprint and pad numbering stay intact.
    base = Path('/usr/share/kicad/3dmodels')
    mapping = {
        'ESP32': ('RF_Module.3dshapes/ESP32-WROOM-32.step', (0,-2.99,0), (0,0,0)),
        'MPU6500': ('Package_DFN_QFN.3dshapes/QFN-24_3x3mm_P0.4mm.step', (0,0,0), (0,0,0)),
        'CH340C': ('Package_SO.3dshapes/SOIC-16_3.9x9.9mm_P1.27mm.step', (0,0,0), (0,0,0)),
        'AO3400': ('Package_TO_SOT_SMD.3dshapes/SOT-23.step', (0,0,0), (0,0,-90)),
        'MMBT3904': ('Package_TO_SOT_SMD.3dshapes/SOT-23.step', (0,0,0), (0,0,0)),
        'SS16': ('Diode_SMD.3dshapes/D_SMA.step', (0,0,0), (0,0,0)),
        'Texas_DRC0010J': ('Package_SON.3dshapes/VSON-10-1EP_3x3mm_P0.5mm_EP1.65x2.4mm.step', (0,0,0), (0,0,0)),
        # 4x4x1.2 mm visual envelopes only; L2's exact ordering part is unresolved.
        'L_VLF4012': ('Inductor_SMD.3dshapes/L_APV_ANR4012.step', (0,0,0), (0,0,0)),
        'L_4x4': ('Inductor_SMD.3dshapes/L_APV_ANR4012.step', (0,0,0), (0,0,0)),
        'Header_1x04_P2.54mm': ('Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x04_P2.54mm_Vertical.step', (-3.81,0,0), (0,0,-90)),
    }
    if name in mapping:
        source, offset, rotation = mapping[name]
        fp.Models().clear()
        model = pcb.FP_3DMODEL(); model.m_Filename = str(base/source)
        model.m_Offset.x,model.m_Offset.y,model.m_Offset.z = offset
        model.m_Rotation.x,model.m_Rotation.y,model.m_Rotation.z = rotation
        fp.Models().push_back(model)
    models = LIB/'models'; models.mkdir(exist_ok=True)
    for model in fp.Models():
        source = Path(model.m_Filename.replace('${KICAD10_3DMODEL_DIR}', str(base)).replace('${KIPRJMOD}',str(OUT)))
        if not source.exists():
            raise FileNotFoundError(f'Missing model for {name}: {source}')
        dest = models/source.name
        if source.resolve()!=dest.resolve():shutil.copy2(source,dest)
        model.m_Filename = '${KIPRJMOD}/../Library/FC_Local/models/'+dest.name

def local_fp(name, source, model=None):
    fp = pcb.FootprintLoad(str(Path(source).parent), Path(source).stem)
    if fp is None: raise ValueError(source)
    fp.SetFPID(pcb.LIB_ID('FC_Local', name))
    for pad in fp.Pads():
        pad.SetLocalSolderMaskMargin(mm(0.04))
        if pad.GetAttribute() == pcb.PAD_ATTRIB_NPTH: pad.SetNumber('')
    if model:
        fp.Models().clear()
        m = pcb.FP_3DMODEL()
        m.m_Filename = '${KIPRJMOD}/../' + str(Path(model).relative_to(ROOT))
        # Offsets centre the STEP whose origin is not at footprint centre (measured from STEP bbox)
        off = {
            'MPU6500': (0, -3.01, 0.85),
            'ESP32': (-1.22, 1.23, 0.85),
            'AO3400': (0, -0.625, 0.90),
            'MMBT3904': (0, 0.0, 0.90),
            'SS16': (0, -1.25, 0.70),
            'BUTTON': (0, -1.47, 0.85),
            'CH340C': (0, -0.85, 1.20),
        }.get(name, (0,0,0))
        m.m_Offset.x, m.m_Offset.y, m.m_Offset.z = off
        if name == 'BUTTON':
            m.m_Rotation.x = -90
        if name == 'AO3400':
            m.m_Rotation.z = 90
        fp.Models().push_back(m)
    normalize_model(fp, name)
    finish_fp_artwork(fp)
    PLUGIN.FootprintSave(str(PRETTY), fp)
    return name

def standard_fp(lib, name):
    return local_fp(name, Path('/usr/share/kicad/footprints') / (lib+'.pretty') / (name+'.kicad_mod'))

def make_pad_fp(name, pitch, size, drill=None, pins=2):
    fp = pcb.FOOTPRINT(None)
    fp.SetFPID(pcb.LIB_ID('FC_Local', name))
    for i in range(pins):
        p = pcb.PAD(fp)
        p.SetNumber(str(i+1)); p.SetPosition(vec((i-(pins-1)/2.0)*pitch,0)); p.SetSize(vec(*size))
        p.SetShape(pcb.PAD_SHAPE_ROUNDRECT); p.SetRoundRectRadiusRatio(.2)
        if drill:
            p.SetAttribute(pcb.PAD_ATTRIB_PTH); p.SetDrillSize(vec(drill,drill)); p.SetLayerSet(layers(pcb.F_Cu,pcb.B_Cu,pcb.F_Mask,pcb.B_Mask))
        else:
            p.SetAttribute(pcb.PAD_ATTRIB_SMD); p.SetLayerSet(layers(pcb.F_Cu,pcb.F_Mask))
        fp.Add(p)
    if name=='Header_1x04_P2.54mm':
        # Actual 2.54 mm housing, plus 0.25 mm assembly courtyard.
        hx=(pins-1)*pitch/2+1.27+.25;hy=1.27+.25
        corners=[(-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy),(-hx,-hy)]
        for a,z in zip(corners,corners[1:]):
            g=pcb.PCB_SHAPE();g.SetShape(pcb.SHAPE_T_SEGMENT);g.SetStart(vec(*a));g.SetEnd(vec(*z));g.SetLayer(pcb.F_CrtYd);g.SetWidth(mm(.05));fp.Add(g)
    fp.SetAttributes(pcb.FP_SMD if not drill else pcb.FP_THROUGH_HOLE)
    normalize_model(fp, name)
    finish_fp_artwork(fp)
    PLUGIN.FootprintSave(str(PRETTY), fp)
    return name

COMP = []
def add(ref, sym, fp, nets, xy, side='F', angle=0, page='power', value=None, note=''):
    c = dict(ref=ref,sym=sym,fp=fp,nets={str(k):v for k,v in nets.items()},x=xy[0],y=xy[1],side=side,angle=angle,page=page,value=value or sym,note=note,uuid=uid(ref))
    COMP.append(c)
    return c

def setup():
    OUT.mkdir(exist_ok=True); PRETTY.mkdir(parents=True,exist_ok=True)
    for name, folder, fpn in [
        ('ESP32','ESP32-WROOM-32_8MB_','MODULE_ESP32-WROOM-32_8MB_'),
        ('MPU6500','MPU-6500','QFN40P300X300X95-25N'),
        ('CH340C','CH340C','SOIC127P600X180-16N'),
        ('AO3400','AO3400','SOT23'), ('MMBT3904','MMBT3904','TRANS_MMBT3904'),
        ('SS16','SS16','DIOM4325X250N'), ('USB_C','2345986-1','TE_2345986-1'),
        ('BUTTON','FSM4JSMA','TE_FSM4JSMA')]:
        folder = ROOT/'Library'/folder
        symbol(name,next(folder.glob('*.kicad_sym')))
        models=sorted((path for path in folder.iterdir() if path.suffix.lower()=='.step'),key=lambda path:(len(path.name),path.name))
        if not models:raise FileNotFoundError(f'No STEP model in {folder}')
        local_fp(name,folder/(fpn+'.kicad_mod'),models[0])
    for name, lib, orig in [('R','Device','R'),('C','Device','C'),('L','Device','L'),('D_Schottky','Device','D_Schottky'),('Conn2','Connector_Generic','Conn_01x02'),('Conn4','Connector_Generic','Conn_01x04'),('TPS63001','Regulator_Switching','TPS63001'),('USBLC6','Power_Protection','USBLC6-2SC6')]:
        symbol(name,f'/usr/share/kicad/symbols/{lib}.kicad_sym',orig)
    symbol('PWR_FLAG','/usr/share/kicad/symbols/power.kicad_sym','PWR_FLAG')
    for p in pins('USB_C'):
        n=child(p,'name')
        if n[1] in ('VBUS_A','VBUS_B'):n[1]='VBUS'
        if n[1] in ('GND_A','GND_B'):n[1]='GND'
    symbol('USB_C','/usr/share/kicad/symbols/Connector.kicad_sym','USB_C_Receptacle_USB2.0_16P')
    local_fp('USB_C','/usr/share/kicad/footprints/Connector_USB.pretty/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.kicad_mod')
    for p in pins('SS16'):
        n=child(p,'number');n[1]={'C':'1','A':'2'}[n[1]]
    fp=pcb.FootprintLoad(str(PRETTY),'SS16')
    for p in fp.Pads():p.SetNumber({'C':'1','A':'2'}[p.GetNumber()])
    PLUGIN.FootprintSave(str(PRETTY),fp)
    rect_symbol('TPS61070', [('6','VBAT','power_in'),('3','EN','input'),('2','GND','power_in'),('1','SW','passive'),('5','VOUT','power_out'),('4','FB','input')])
    fps={}
    for alias,lib,name in [
        ('r','Resistor_SMD','R_0402_1005Metric'),('c','Capacitor_SMD','C_0402_1005Metric'),
        ('c0603','Capacitor_SMD','C_0603_1608Metric'),('c0805','Capacitor_SMD','C_0805_2012Metric'),
        ('c1206','Capacitor_SMD','C_1206_3216Metric'),
        ('buck','Package_SON','Texas_DRC0010J'),('boost','Package_TO_SOT_SMD','SOT-23-6'),
        ('sh','Connector_JST','JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal')]:
        fps[alias]=standard_fp(lib,name)
    fps['motor']=make_pad_fp('Motor_Wire_Pads',2.8,(2,2.4))
    fps['battery']=make_pad_fp('Battery_Wire_Pads',4,(3,3))
    fps['header4']=make_pad_fp('Header_1x04_P2.54mm',2.54,(1.8,1.8),drill=1.0,pins=4)
    # TDK VLF4012 recommended land: 4.4 x 3.7, two 1.2 x 3.7 lands.
    fps['l1']=make_pad_fp('L_VLF4012',3.2,(1.2,3.7))
    fps['l2']=make_pad_fp('L_4x4',3.0,(1.5,3.8))
    return fps

def circuit(f):
    def r(ref,val,a,b,x,y,side='F',angle=0,page='power'):
        return add(ref,'R',f['r'],{1:a,2:b},(x,y),side,angle,page,val)
    def c(ref,val,a,b,x,y,side='F',angle=0,page='power',pkg='c'):
        return add(ref,'C',f[pkg],{1:a,2:b},(x,y),side,angle,page,val)
    add('U1','ESP32','ESP32',{1:'GND',15:'GND',38:'GND',39:'GND',2:'+3V3',3:'EN',6:'IMU_INT',7:'VBAT_ADC',8:'UART1_RX',9:'PWM4',10:'PWM1',11:'PWM2',12:'PWM3',13:'UART1_TX',25:'BOOT',26:'I2C_SDA',27:'FLOW_RX',28:'FLOW_TX',30:'SPI_SCK',31:'SPI_MISO',33:'IMU_CS',36:'I2C_SCL',37:'SPI_MOSI',34:'UART0_RX',35:'UART0_TX'},(100,90.5),page='mcu',value='ESP32-WROOM-32 (8MB)')
    c('C1','22uF 10V X5R','+3V3','GND',88.5,87.2,pkg='c0805',page='mcu')
    c('C2','100nF','+3V3','GND',88.7,85.4,page='mcu')
    r('R1','10k','+3V3','EN',88.3,90.5,page='mcu')
    c('C3','1uF','EN','GND',88.3,92,angle=180,page='mcu',pkg='c0603')
    r('R2','10k','+3V3','BOOT',112.0,102,page='mcu')
    r('R3','100k 1%','VBAT','VBAT_ADC',88.4,94.1,page='mcu')
    r('R4','100k 1%','VBAT_ADC','GND',88.4,95.4,page='mcu')
    c('C4','100nF','VBAT_ADC','GND',88.4,96.7,page='mcu')
    add('U2','MPU6500','MPU6500',{8:'+3V3_IMU',9:'SPI_MISO',10:'REGOUT',11:'GND',12:'IMU_INT',13:'+3V3_IMU',18:'GND',20:'GND',22:'IMU_CS',23:'SPI_SCK',24:'SPI_MOSI',25:'GND'},(100,107),page='imu',value='MPU-6500')
    r('R5','10R','+3V3','+3V3_IMU',103.3,105.7,page='imu')
    c('C5','100nF','+3V3_IMU','GND',102.8,107.2,page='imu')
    c('C6','10nF','+3V3_IMU','GND',97.2,106,page='imu')
    c('C7','100nF','REGOUT','GND',97.2,107.4,page='imu')
    c('C8','1uF','+3V3_IMU','GND',97.2,104.0,page='imu')
    r('R6','10k','+3V3_IMU','IMU_CS',104.5,104.3,page='imu')
    add('J1','USB_C','USB_C',{**{x:'GND' for x in ['A1','A12','B1','B12','SH','S1']},**{x:'VBUS' for x in ['A4','A9','B4','B9']},'A5':'CC1','B5':'CC2','A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM'},(100,116),page='usb',value='USB4105-GF-A')
    add('U3','CH340C','CH340C',{1:'GND',2:'UART0_RX',3:'UART0_TX',4:'+3V3',5:'USB_DP',6:'USB_DM',13:'DTR',14:'RTS',15:'GND',16:'+3V3'},(100,97),'B',0,'usb')
    c('C9','100nF','+3V3','GND',104.7,93.5,'B',page='usb')
    r('R7','5.1k 1%','CC1','GND',97.3,113.5,'B',page='usb')
    r('R8','5.1k 1%','CC2','GND',102.8,113.5,'B',page='usb')
    add('U4','USBLC6',f['boost'],{1:'USB_DM',2:'GND',3:'USB_DP',4:'USB_DP',5:'VBUS',6:'USB_DM'},(100,111.8),'B',0,'usb','USBLC6-2SC6')
    c('C11','1uF 10V','VBUS','GND',105.4,111.5,'B',page='usb',pkg='c0603')
    # Espressif cross-coupled auto-download circuit: DTR=RTS leaves both off.
    add('Q5','MMBT3904','MMBT3904',{1:'BASE_EN',2:'RTS',3:'EN'},(111.8,98),'B',0,'usb')
    add('Q6','MMBT3904','MMBT3904',{1:'BASE_BOOT',2:'DTR',3:'BOOT'},(111.8,102.2),'B',0,'usb')
    r('R9','10k','DTR','BASE_EN',108.4,98,'B',90,'usb')
    r('R10','10k','RTS','BASE_BOOT',108.4,102.2,'B',90,'usb')
    add('J2','Conn4',f['sh'],{1:'GND',2:'+5V_FLOW',3:'FLOW_TX',4:'FLOW_RX'},(113.95,106.8),'F',90,'imu','MTF-01P SH1.0', 'Pin 3 to sensor Rx; pin 4 to sensor Tx. Verify cable orientation.')
    add('J8','Conn4',f['header4'],{1:'+3V3',2:'GND',3:'I2C_SDA',4:'I2C_SCL'},(116,98),'F',90,'mcu','I2C')
    add('J9','Conn4',f['header4'],{1:'+3V3',2:'GND',3:'UART1_TX',4:'UART1_RX'},(76,100),'F',90,'mcu','UART1')
    r('R23','4.7k','+3V3','I2C_SDA',116,92,'F',0,'mcu')
    r('R24','4.7k','+3V3','I2C_SCL',116,94,'F',0,'mcu')
    add('J3','Conn2',f['battery'],{1:'VBAT',2:'GND'},(110.5,112.2),'F',0,'power','BAT 1S')
    add('D5','SS16','SS16',{1:'VSYS',2:'VBAT'},(92,112),'F',90,'power')
    add('D6','SS16','SS16',{1:'VSYS',2:'VBUS'},(92,112),'B',90,'power')
    add('U5','TPS63001',f['buck'],{1:'+3V3',2:'BUCK_L2',3:'GND',4:'BUCK_L1',5:'VSYS',6:'VSYS',7:'VSYS',8:'VINA',9:'GND',10:'+3V3',11:'GND'},(108,90.5),'B',0,'power','TPS63001DRCR')
    add('L1','L',f['l1'],{1:'BUCK_L1',2:'BUCK_L2'},(112.7,90.5),'B',90,'power','2.2uH VLF4012-2R2M1R5')
    c('C12','10uF 10V X5R','VSYS','GND',108,94,'B',pkg='c0805')
    c('C13','10uF 10V X5R','+3V3','GND',108,87.2,'B',pkg='c0805')
    r('R11','100R','VSYS','VINA',104.8,93.1,'B')
    c('C15','100nF','VINA','GND',104.8,91.5,'B')
    add('U6','TPS61070',f['boost'],{1:'BOOST_SW',2:'GND',3:'+3V3',4:'BOOST_FB',5:'+5V_FLOW',6:'+3V3'},(92,90.5),'B',180,'power','TPS61070DDCR')
    add('L2','L',f['l2'],{1:'+3V3',2:'BOOST_SW'},(87.5,90.5),'B',90,'power','4.7uH >=1A shielded', '4x4 land; choose matching inductor before ordering')
    c('C17','22uF 10V X5R','+5V_FLOW','GND',92,94,'B',pkg='c0805')
    r('R12','1.8M 1%','+5V_FLOW','BOOST_FB',95.2,92.2,'B')
    r('R13','200k 1%','BOOST_FB','GND',95.2,90.7,'B')
    c('C18','100nF','+5V_FLOW','GND',109,106.8,page='imu')
    c('C19','47uF 10V X5R','VBAT','GND',111.2,115.7,pkg='c1206')
    # Redundant caps removed (C20)
    # Motors track the extended arm geometry from shape_board (+1.75cm radially)
    for i,(x,y,quadrant) in enumerate([(73.7,73.7,1),(126.3,73.7,2),(126.3,126.3,3),(73.7,126.3,4)],1):
        nx=f'M{i}_NEG'; g=f'GATE{i}'; pwm=f'PWM{i}'
        orth_ang = 90 if quadrant in (1,3) else 0
        dx=-1 if x<100 else 1; dy=-1 if y<100 else 1
        add('Q'+str(i),'AO3400','AO3400',{1:g,2:'GND',3:nx},(x,y),'F',orth_ang,'motors')
        add('D'+str(i),'SS16','SS16',{1:'VBAT',2:nx},(x+dx*3.2,y+dy*3.2),'F',orth_ang,'motors')
        add('J'+str(i+3),'Conn2',f['motor'],{1:'VBAT',2:nx},(x+dx*(1.5-1.5/math.sqrt(2)),y+dy*(1.5-1.5/math.sqrt(2))),'F',orth_ang,'motors',f'M{i} + / -')
        r('R'+str(13+i*2),'100R',pwm,g,x-dx*1.0,y-dy*3.1,'F',orth_ang,'motors')
        r('R'+str(14+i*2),'100k',g,'GND',x-dx*1.5,y-dy*3.1,'F',orth_ang,'motors')
        c('C'+str(20+i),'100nF 10V','VBAT',nx,x-dx*5.2,y-dy*1.2,'F',orth_ang,'motors',pkg='c0603')
    # Single-side request: keep everything on F. Initial spots for ex-B parts are
    # pre-spread so place_fc starts from a feasible guess.
    _spread = {
        'U3': (88,102), 'C9': (94,96), 'R7': (94,113.5), 'R8': (106,113.5),
        'U4': (100,109.5), 'C11': (106.5,111.5),
        'Q5': (113.5,98), 'Q6': (113.5,102.5), 'R9': (110,98), 'R10': (110,102.5),
        'D6': (95.5,112), 'U5': (112,90.5), 'L1': (116.5,90.5),
        'C12': (112,94), 'C13': (112,87), 'R11': (108.5,93.5), 'C15': (108.5,91.5),
        'U6': (86,90.5), 'L2': (82.5,90.5), 'C17': (86,94),
        'R12': (90,92.5), 'R13': (90,90.5),
        'D1': (69.5,69.5), 'D2': (130.5,69.5), 'D3': (130.5,130.5), 'D4': (69.5,130.5),
        'C21': (77.5,71.5), 'C22': (122.5,71.5), 'C23': (122.5,128.5), 'C24': (77.5,128.5),
        'J8': (115,96.85), 'J9': (86,100),
    }
    for cc in COMP:
        if cc['ref'] in _spread:
            cc['x'], cc['y'] = _spread[cc['ref']]
        if cc['side'] == 'B':
            cc['side'] = 'F'

def pins(sym):
    return [p for sub in children(SYMS[sym],'symbol') for p in children(sub,'pin')]

def save_symbols():
    for name,a in SYMS.items():
        for prop in children(a,'property'):
            if prop[1]=='Footprint': prop[2]='FC_Local:'+name
    lib=[S('kicad_symbol_lib'),[S('version'),20241209],[S('generator'),S('kicad_symbol_editor')],*SYMS.values()]
    (LIB/'FC_Local.kicad_sym').write_text(dump(lib)+'\n')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "FC_Local") (type "KiCad") (uri "${KIPRJMOD}/../Library/FC_Local/FC_Local.kicad_sym") (options "") (descr "Project-local verified sources")))\n')
    (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "FC_Local") (type "KiCad") (uri "${KIPRJMOD}/../Library/FC_Local/FC_Local.pretty") (options "") (descr "Project-local footprints")))\n')

def schematic():
    # Single-page schematic: all components on the root sheet FC_ESP32.kicad_sch.
    # Net connectivity, references, values, footprints and UUIDs are unchanged;
    # only the previous 5-sheet hierarchy is removed. Spatial blocks preserve
    # the old grouping for readability on a single large sheet.
    rootid=uid('root')
    # Grid-aligned, non-overlapping single-page blocks. All offsets are
    # multiples of 1.27 mm so ERC stays off-grid clean like the old pages.
    blocks={'mcu':(0,40.64),'imu':(431.8,40.64),'usb':(863.6,40.64),'power':(0,431.8),'motors':(431.8,431.8)}
    used=sorted({c['sym'] for c in COMP}); used.append('PWR_FLAG')
    defs=[]
    for name in used:
        a=copy.deepcopy(SYMS[name]); a[1]='FC_Local:'+name; defs.append(dump(a))
    out=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {rootid}) (paper "A0") (title_block (title "FC ESP32 - 1S brushed quad") (rev "A-prototype")) (lib_symbols '+ '\n'.join(defs)+')']
    counters={}
    for c in COMP:
        page=c['page']; j=counters.get(page,0); counters[page]=j+1
        cols,dx,dy=(3,111.76,63.5) if page in ('mcu','imu') else (4,93.98,40.64 if page=='motors' else 55.88)
        ox,oy=blocks[page]
        x=ox+50.8+(j%cols)*dx; y=oy+50.8+(j//cols)*dy
        pp=pins(c['sym']); maxy=max(float(child(p,'at')[2]) for p in pp)
        top=y-maxy-7
        tx,ty,just=(x+3.81,y-1.27,'(justify left)') if c['sym'] in ('R','C','L') else (x,top,'')
        out.append(f'(symbol (lib_id "FC_Local:{c["sym"]}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {c["uuid"]}) (property "Reference" {q(c["ref"])} (at {tx} {ty} 0) (effects (font (size 1.27 1.27)) {just})) (property "Value" {q(c["value"])} (at {tx} {ty+2.54} 0) (effects (font (size 1.0 1.0)) {just})) (property "Footprint" "FC_Local:{c["fp"]}" (at {x} {y} 0) (effects (font (size 1 1)) hide)) (instances (project "FC_ESP32" (path "/{rootid}" (reference {q(c["ref"])}) (unit 1)))))')
        seen={}
        for p in pp:
            num=str(child(p,'number')[1]); at=child(p,'at'); px=x+float(at[1]); py=y-float(at[2]); a=float(at[3]); net=c['nets'].get(num)
            pos=(px,py)
            if pos in seen:
                if seen[pos]!=net: raise ValueError((c['ref'],num,'stacked pin conflict'))
                continue
            seen[pos]=net
            if net:
                rad=math.radians(a); ex=round(px-5.08*math.cos(rad),6); ey=round(py+5.08*math.sin(rad),6)
                la=int(a)%360
                justify='right' if la==0 else 'left'
                out.append(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid {uid(c["ref"]+num+"wire")}))')
                out.append(f'(global_label {q(net)} (shape input) (at {ex} {ey} {la}) (effects (font (size 0.9 0.9)) (justify {justify})) (uuid {uid(c["ref"]+num+"label")}))')
            else:
                out.append(f'(no_connect (at {px} {py}) (uuid {uid(c["ref"]+num+"nc")}))')
    for k,net in enumerate(['GND','VBUS','VSYS','VINA','+3V3_IMU','VBAT']):
        x=25.4+k*203.2;y=12.7; ref='#FLG0'+str(k+1)
        out.append(f'(symbol (lib_id "FC_Local:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board yes) (uuid {uid(ref)}) (property "Reference" {q(ref)} (at {x} {y} 0) (effects (font (size 1 1)) hide)) (property "Value" "PWR_FLAG" (at {x} {y-5.08} 0) (effects (font (size 1 1)))) (instances (project "FC_ESP32" (path "/{rootid}" (reference {q(ref)}) (unit 1)))))')
        out.append(f'(global_label {q(net)} (shape input) (at {x} {y} 0) (effects (font (size 1 1)) (justify right)) (uuid {uid(ref+"label")}))')
    # Readability-only section titles. Plain (text) nodes verified to load in
    # kicad-cli netlist export; gr_text/gr_line break this schema version.
    titles=[('POWER RAILS',25.4,5.08),('MCU / BATTERY SENSE',25.4,30.48),('IMU + FLOW (MPU6500 / J2)',457.2,30.48),('USB / CH340C + AUTO-RESET',889,30.48),('POWER 1S (TPS63001 / TPS61070)',25.4,421.64),('MOTORS x4 (AO3400 + SS16)',457.2,421.64)]
    for title,x,y in titles:
        out.append(f'(text {q(title)} (at {x} {y} 0) (effects (font (size 4 4))))')
    out.append('(sheet_instances (path "/" (page "1"))) (embedded_fonts no))')
    (OUT/'FC_ESP32.kicad_sch').write_text('\n'.join(out)+'\n')
    for legacy in ('mcu','imu','usb','power','motors'):
        p=OUT/(legacy+'.kicad_sch')
        if p.exists(): p.unlink()

def shape_board():
    # Extended arms +1.75cm per requested (1.5-2cm): motors pushed radially outward from center
    motor=[(66.6,66.6),(133.4,66.6),(133.4,133.4),(66.6,133.4)]
    parts=[box(83,85,117,120),box(90,77.5,110,90)]
    for x,y in motor:
        parts += [Point(x,y).buffer(6.5,quad_segs=24),LineString([(x,y),(100,100)]).buffer(4.1,quad_segs=12)]
    sh=unary_union(parts).buffer(1.5,quad_segs=8).buffer(-1.5,quad_segs=8)
    return sh,motor

def finish_fp_artwork(fp):
    if str(fp.GetFPID().GetLibItemName()) in ('CH340C','MMBT3904','SS16'):
        for item in fp.GraphicalItems():
            if isinstance(item,pcb.PCB_SHAPE) and item.GetLayer()==pcb.F_SilkS and item.GetShape()==pcb.SHAPE_T_CIRCLE:
                item.SetLayer(pcb.F_Fab)

def finish_artwork(b):
    for item in list(b.GetDrawings()):
        if isinstance(item,pcb.PCB_TEXT) and item.GetText() == 'FC ESP32 / A':
            item.SetText('PNT')
            item.SetTextSize(vec(2,2))
            item.SetTextThickness(mm(.3))
            item.SetLayer(pcb.B_SilkS)
            item.SetMirrored(True)
    for fp in b.GetFootprints():
        finish_fp_artwork(fp)
        for field in fp.GetFields():
            if field.GetLayer()==pcb.B_SilkS:field.SetVisible(False)
        for item in list(fp.GraphicalItems()):
            if isinstance(item,pcb.PCB_TEXT) and item.GetLayer()==pcb.B_SilkS:fp.Remove(item)

def pcb_board():
    b=pcb.BOARD(); b.SetCopperLayerCount(2); b.GetDesignSettings().SetBoardThickness(mm(.8))
    subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'FC_ESP32.kicad_sch'),'-o',str(OUT/'FC_ESP32.net'), '--format','kicadxml'],check=True,capture_output=True)
    xml=ET.parse(OUT/'FC_ESP32.net').getroot()
    pin_nets={(p.get('ref'),p.get('pin')):n.get('name') for n in xml.find('nets') for p in n}
    nets={n:pcb.NETINFO_ITEM(b,n) for n in sorted(set(pin_nets.values()))}
    for n in nets.values(): b.Add(n)
    for c in COMP:
        fp=pcb.FootprintLoad(str(PRETTY),c['fp']); fp.SetReference(c['ref']); fp.SetValue(c['value']); fp.SetUuid(pcb.KIID(c['uuid']))
        fp.SetFPID(pcb.LIB_ID('FC_Local',c['fp']))
        fp.SetPath(pcb.KIID_PATH('/'+uid('root')+'/'+c['uuid']))
        b.Add(fp)
        fp.SetPosition(vec(c['x'],c['y'])); fp.SetOrientationDegrees(c['angle'])
        if c['side']=='B': fp.Flip(fp.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT)
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        for pad in fp.Pads():
            num=pad.GetNumber()
            if c['ref']=='J1' and num=='SH':num='S1'
            net=pin_nets.get((c['ref'],num))
            if net: pad.SetNet(nets[net])
    sh,motors=shape_board()
    coords=list(sh.exterior.coords)
    for p1,p2 in zip(coords,coords[1:]):
        line=pcb.PCB_SHAPE();line.SetShape(pcb.SHAPE_T_SEGMENT);line.SetStart(vec(*p1));line.SetEnd(vec(*p2));line.SetLayer(pcb.Edge_Cuts);line.SetWidth(mm(.05));b.Add(line)
    for i,(x,y) in enumerate(motors,1):
        h=pcb.FOOTPRINT(b);h.SetReference('H'+str(i));h.SetPosition(vec(x,y));h.SetAttributes(pcb.FP_BOARD_ONLY|pcb.FP_EXCLUDE_FROM_BOM|pcb.FP_EXCLUDE_FROM_POS_FILES)
        p=pcb.PAD(h);p.SetAttribute(pcb.PAD_ATTRIB_NPTH);p.SetShape(pcb.PAD_SHAPE_CIRCLE);p.SetSize(vec(8.6,8.6));p.SetDrillSize(vec(8.6,8.6));p.SetPosition(vec(x,y));p.SetLayerSet(layers(pcb.F_Cu,pcb.B_Cu,pcb.F_Mask,pcb.B_Mask));h.Add(p);h.Reference().SetVisible(False);h.Value().SetVisible(False);b.Add(h)
        circle=pcb.PCB_SHAPE();circle.SetShape(pcb.SHAPE_T_CIRCLE);circle.SetCenter(vec(x,y));circle.SetEnd(vec(x+20,y));circle.SetLayer(pcb.Dwgs_User);circle.SetWidth(mm(.1));b.Add(circle)
    for text,x,y,size in [('PNT',100,111,.8),('1S ONLY',110.5,110,.65),('BAT+  BAT-',110.5,114,.65),('USB',100,117,.65)]:
        t=pcb.PCB_TEXT(b);t.SetText(text);t.SetPosition(vec(x,y));t.SetTextSize(vec(size,size));t.SetTextThickness(mm(.12));t.SetLayer(pcb.F_SilkS);b.Add(t)
    finish_artwork(b)
    # No ground pour until after routing. Antenna keepout comes from the supplied footprint.
    pcb.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
    # Dynamic pitch from new motor positions
    import math as _m
    d = _m.hypot(motors[0][0]-motors[1][0], motors[0][1]-motors[1][1])
    (OUT/'mechanical.json').write_text(json.dumps(dict(outline_mm=coords,motors_mm=motors,hole_diameter_mm=8.6,prop_diameter_mm=40,nearest_pitch_mm=round(d,1),thickness_mm=.8,fr4_area_mm2=sh.area-4*math.pi*4.3**2,estimated_fr4_g=(sh.area-4*math.pi*4.3**2)*.8*.00185),indent=2)+'\n')

def project():
    classes=[]
    for name,width in [('Default',.18),('LogicPower',.4),('MotorPower',.8),('Battery',1.2)]:
        classes.append(dict(name=name,clearance=.15,track_width=width,via_diameter=.6,via_drill=.3,microvia_diameter=.3,microvia_drill=.1,diff_pair_width=.18,diff_pair_gap=.18,diff_pair_via_gap=.25))
    patterns=[dict(netclass='Battery',pattern='VBAT'),dict(netclass='MotorPower',pattern='M*_NEG'),dict(netclass='MotorPower',pattern='BUCK_L*'),dict(netclass='LogicPower',pattern='+*'),dict(netclass='LogicPower',pattern='VSYS'),dict(netclass='LogicPower',pattern='BOOST_SW'),dict(netclass='LogicPower',pattern='VBUS')]
    data=dict(meta=dict(filename='FC_ESP32.kicad_pro',version=1),board=dict(design_settings=dict(rules=dict(min_clearance=.15,min_track_width=.15,min_via_diameter=.55,min_through_hole_diameter=.3,min_copper_edge_clearance=.25,min_hole_clearance=.25,min_silk_clearance=.1,min_silk_text_height=.6,min_silk_text_thickness=.1,min_solder_mask_sliver=.075))),net_settings=dict(classes=classes,netclass_patterns=patterns,meta=dict(version=4)))
    (OUT/'FC_ESP32.kicad_pro').write_text(json.dumps(data,indent=2)+'\n')

def bom():
    (OUT/'design.json').write_text(json.dumps(COMP,indent=2)+'\n')
    with (OUT/'BOM.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Reference','Value','Footprint','Side','Notes'])
        for c in COMP:w.writerow([c['ref'],c['value'],'FC_Local:'+c['fp'],c['side'],c['note']])
    with (ROOT/'BOM_JLCPCB.csv').open('w',newline='') as f:
        w=csv.writer(f); w.writerow(['Comment','Designator','Footprint'])
        for c in COMP:w.writerow([c['value'],c['ref'],'FC_Local:'+c['fp']])
    (LIB/'sources.json').write_text(json.dumps(SOURCES,indent=2)+'\n')

if __name__=='__main__':
    if '--finish-artwork' in sys.argv:
        for path in PRETTY.glob('*.kicad_mod'):
            footprint=pcb.FootprintLoad(str(PRETTY),path.stem)
            finish_fp_artwork(footprint)
            PLUGIN.FootprintSave(str(PRETTY),footprint)
        board=pcb.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
        finish_artwork(board)
        pcb.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),board)
        sys.exit(0)
    f=setup(); circuit(f); save_symbols(); schematic(); pcb_board(); project()
    # Placement is part of generation, so the BOM/design coordinates match PCB.
    from place_fc import main as place_components
    place_components()
    placement = json.loads((OUT/'placement.json').read_text())
    for component in COMP:
        for field in ('x', 'y', 'side'):
            component[field] = placement[component['ref']][field]
    project()  # pcbnew may save cached defaults while placing; write rules last.
    bom()
    print(f'Created {len(COMP)} components on one schematic sheet in {OUT}')
