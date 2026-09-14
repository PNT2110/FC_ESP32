#!/usr/bin/env python3
"""Remove specified copper nets before rerouting them in priority order."""
import sys
import sexpdata as sx
from build_fc import OUT,child,key
path=OUT/'FC_ESP32.kicad_pcb';tree=sx.loads(path.read_text())
nets=set(sys.argv[1:])
assert nets and 'VBAT' not in nets,'Do not rip up the protected battery trunk with this helper'
kept=[];removed=0
for item in tree:
    if key(item) in ('segment','via','arc') and str(child(item,'net')[1]) in nets:
        removed+=1
    else:kept.append(item)
path.write_text(sx.dumps(kept)+'\n')
print('Removed',removed,'tracks/vias for',sorted(nets))
