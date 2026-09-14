#!/usr/bin/env python3
"""Normalize 3D orientation and make the model dependencies portable."""
import shutil
import pcbnew as p
from build_fc import OUT,ROOT,PRETTY,LIB,PLUGIN
models=LIB/'models';models.mkdir(exist_ok=True)
base=__import__('pathlib').Path('/usr/share/kicad/3dmodels')
replacements={
 # Keep project STEP models (build_fc already centred them); only normalize KiCad generic parts.
 'Texas_DRC0010J':('Package_SON.3dshapes/VSON-10-1EP_3x3mm_P0.5mm_EP1.65x2.4mm.step',(0,0,0),(0,0,0)),
}
def update(fp):
    name=str(fp.GetFPID().GetLibItemName())
    if name in replacements:
        src,offset,rotation=replacements[name];src=base/src
        fp.Models().clear();m=p.FP_3DMODEL();m.m_Filename=str(src)
        m.m_Offset.x,m.m_Offset.y,m.m_Offset.z=offset
        m.m_Rotation.x,m.m_Rotation.y,m.m_Rotation.z=rotation
        fp.Models().push_back(m)
    for m in fp.Models():
        if name=='BUTTON':m.m_Rotation.x=-90
        path=m.m_Filename.replace('${KICAD10_3DMODEL_DIR}',str(base)).replace('${KIPRJMOD}',str(OUT))
        src=__import__('pathlib').Path(path)
        if not src.exists():continue
        dest=models/src.name
        if src.resolve()!=dest.resolve():shutil.copy2(src,dest)
        m.m_Filename='${KIPRJMOD}/../Library/FC_Local/models/'+dest.name
for path in PRETTY.glob('*.kicad_mod'):
    fp=p.FootprintLoad(str(PRETTY),path.stem);update(fp);PLUGIN.FootprintSave(str(PRETTY),fp)
b=p.LoadBoard(str(OUT/'FC_ESP32.kicad_pcb'))
for fp in b.GetFootprints():update(fp)
p.SaveBoard(str(OUT/'FC_ESP32.kicad_pcb'),b)
