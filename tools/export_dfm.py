#!/usr/bin/env python3
"""Export a complete package for DFM recheck, not manufacturing approval."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'FC_ESP32'; DEST=OUT/'dfm_recheck'; LOG=ROOT/'validation/dfm_20260915'
def run(*args):subprocess.run(args,cwd=ROOT,check=True)
def main():
    run('python3',str(ROOT/'tools/validate_fc.py'))
    result=json.loads((OUT/'validation_summary.json').read_text())
    if any(result[k] for k in ('erc_violations','drc_violations','unconnected_items','schematic_parity_issues')):
        raise SystemExit('Resolve KiCad findings before DFM export.')
    antenna_path=ROOT/'validation/antenna_fix/antenna_geometry.json'
    if not antenna_path.exists():raise SystemExit('Run tools/audit_antenna.py and save antenna_geometry.json before export.')
    antenna=json.loads(antenna_path.read_text())
    pcb_hash=hashlib.sha256((OUT/'FC_ESP32.kicad_pcb').read_bytes()).hexdigest()
    if not antenna.get('passed') or antenna.get('pcb_sha256')!=pcb_hash:
        raise SystemExit('Antenna audit failed or is stale; re-run it for this PCB.')
    DEST.mkdir(exist_ok=True);LOG.mkdir(exist_ok=True)
    run('kicad-cli','pcb','export','gerbers',str(OUT/'FC_ESP32.kicad_pcb'),'-o',str(DEST)+'/',
        '--layers','F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,Edge.Cuts',
        '--subtract-soldermask','--exclude-refdes','--exclude-value','--check-zones')
    run('kicad-cli','pcb','export','drill',str(OUT/'FC_ESP32.kicad_pcb'),'-o',str(DEST)+'/',
        '--excellon-separate-th','--excellon-oval-format','route','--generate-report',
        '--report-path',str(LOG/'drill_report.txt'))
    names=['FC_ESP32-'+x for x in ['F_Cu.gtl','B_Cu.gbl','F_Mask.gts','B_Mask.gbs',
        'F_Silkscreen.gto','B_Silkscreen.gbo','F_Paste.gtp','Edge_Cuts.gm1','PTH.drl','NPTH.drl']]
    files=[DEST/n for n in names]
    for p in files:
        if not p.exists() or p.stat().st_size==0:raise SystemExit('Missing output: '+str(p))
    archive=OUT/'FC_ESP32_DFM_RECHECK.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.name)
    manifest={'purpose':'DFM recheck only; not manufacturing release','pcb_sha256':hashlib.sha256((OUT/'FC_ESP32.kicad_pcb').read_bytes()).hexdigest(),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (LOG/'package_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(archive)
if __name__=='__main__':main()
