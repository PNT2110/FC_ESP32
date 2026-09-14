import sexpdata as sx
from build_fc import OUT,child,key
path=OUT/'FC_ESP32.kicad_pcb';a=sx.loads(path.read_text())
ground='GND'
a=[x for x in a if not (key(x)=='segment' and child(x,'net')[1]==ground)]
path.write_text(sx.dumps(a)+'\n')
