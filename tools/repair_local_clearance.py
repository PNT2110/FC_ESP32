#!/usr/bin/env python3
"""Rip conflicting M1 segments and local ground tracks for routing repair."""
import json
import sexpdata as sx
from build_fc import OUT,key,child
path=OUT/'FC_ESP32.kicad_pcb';tree=sx.loads(path.read_text());report=json.loads((OUT/'drc_current.json').read_text())
bad={i['uuid'] for v in report['violations'] if v['type'] in ('clearance','shorting_items','solder_mask_bridge') for i in v['items'] if i['description'].startswith('Track [M1_NEG]')}
removed=[];keep=[]
for item in tree:
 drop=False
 if key(item)=='segment':
  net=str(child(item,'net')[1]);a=child(item,'start')[1:];z=child(item,'end')[1:]
  drop=str(child(item,'uuid')[1]) in bad
  if net=='GND':
   for x,y in (a,z):
    if (85<x<94 and 89<y<97) or (69<x<81 and 69<y<80) or (69<x<81 and 120<y<130):drop=True
 if drop:removed.append(str(child(item,'uuid')[1]))
 else:keep.append(item)
path.write_text(sx.dumps(keep)+'\n');print('Removed segments',len(removed))
