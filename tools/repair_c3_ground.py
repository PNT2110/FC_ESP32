"""Deterministic copper repair on a candidate; CLI fills and validates zones."""
from pathlib import Path
import sys, uuid, shutil
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'.kicad-python'))
import sexpdata as sx
S=sx.Symbol
source=root/'validation/only_c3_ground_remaining.kicad_pcb'
data=sx.loads(source.read_text(encoding='utf-8'))
def key(a):return str(a[0]) if isinstance(a,list) and a else ''
def child(a,k):return next((i for i in a if key(i)==k),None)
removed=[]
for a in list(data):
    if key(a)!='segment' or child(a,'net')[1]!='VBAT' or child(a,'layer')[1]!='B.Cu':continue
    if all(86.99<=x<=88.26 and 91.74<=y<=95.31 for x,y in (child(a,'start')[1:],child(a,'end')[1:])):
        removed.append(child(a,'uuid')[1]);data.remove(a)
assert len(removed)==49,'Unexpected source routing'
redundant={'d8e2fb7a-5617-448c-93e9-237aa831e7fa','9f8c3304-a46e-4b4f-bae9-fd37970d1ce5','967103fe-5804-4f50-af1b-61ea943022e7'}
data=[a for a in data if not (key(a)=='via' and child(a,'uuid')[1] in redundant)]
for a in data:
    if key(a)=='segment' and child(a,'net')[1]=='+5V_FLOW' and child(a,'layer')[1]=='F.Cu':
        for name in ('start','end'):
            point=child(a,name)
            if point[1:] in ([84.6579,93.0244],[85.5397,93.0244]):point[2]=92.89
def uid(label):return str(uuid.uuid5(uuid.NAMESPACE_URL,'fc-c3-repair/'+label))
def track(net,points,width,layer):
    for i,(start,end) in enumerate(zip(points,points[1:])):
        data.append([S('segment'),[S('start'),*start],[S('end'),*end],[S('width'),width],[S('layer'),layer],[S('net'),net],[S('uuid'),uid(net+layer+str(start)+str(i))]])
track('VBAT',[(87,95.3),(88.6,93.25),(88.6,92.1),(88.25,91.75)],1.2,'B.Cu')
track('GND',[(87.775,93.25),(87.10,93.38)],.4,'F.Cu')
track('GND',[(85.10,93.55),(84.0,93.80)],.4,'F.Cu')
track('GND',[(87.10,93.38),(85.10,93.55)],.4,'B.Cu')
for i,pos in enumerate([(87.10,93.38),(85.10,93.55)]):
    data.append([S('via'),[S('at'),*pos],[S('size'),.6],[S('drill'),.3],[S('layers'),'F.Cu','B.Cu'],[S('net'),'GND'],[S('uuid'),uid('via'+str(i))]])
out=root/'validation/c3_candidate.kicad_pcb'
out.write_text(sx.dumps(data),encoding='utf-8')
shutil.copy2(root/'FC_ESP32/FC_ESP32.kicad_pro',out.with_suffix('.kicad_pro'))
print(out,'replaced segments:',len(removed))
