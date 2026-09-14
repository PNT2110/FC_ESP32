#!/usr/bin/env python3
"""Refresh KiCad checks and record source hashes. Nonzero means not ready."""
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'FC_ESP32'

def main():
    commands = [
        ['kicad-cli', 'sch', 'erc', str(OUT/'FC_ESP32.kicad_sch'),
         '--format', 'json', '-o', str(OUT/'erc_current.json')],
        ['kicad-cli', 'pcb', 'drc', str(OUT/'FC_ESP32.kicad_pcb'),
         '--refill-zones', '--schematic-parity', '--format', 'json',
         '-o', str(OUT/'drc_current.json')],
    ]
    for command in commands:
        subprocess.run(command, check=True, cwd=ROOT)
    erc = json.loads((OUT/'erc_current.json').read_text())
    drc = json.loads((OUT/'drc_current.json').read_text())
    ev = [v for sheet in erc['sheets'] for v in sheet.get('violations', [])]
    dv = drc['violations'] + drc['unconnected_items'] + drc['schematic_parity']
    errors = sum(v['severity'] == 'error' for v in ev + dv)
    sources = [*OUT.glob('*.kicad_sch'), OUT/'FC_ESP32.kicad_pcb',
               OUT/'FC_ESP32.kicad_pro', ROOT/'tools/build_fc.py', ROOT/'tools/place_fc.py']
    summary = {
        'kicad_version': drc['kicad_version'], 'date': drc['date'],
        'erc_violations': len(ev), 'drc_violations': len(drc['violations']),
        'unconnected_items': len(drc['unconnected_items']),
        'schematic_parity_issues': len(drc['schematic_parity']),
        'errors': errors,
        'counts_by_type': dict(collections.Counter(v['type'] for v in ev + dv)),
        'electrical_checks_pass': errors == 0,
        'manufacturing_release': False,
        'note': 'DRC/ERC alone do not validate component ratings, current capacity, sensor cable orientation or flight behavior.',
        'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)},
    }
    (OUT/'validation_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k != 'sha256'}, indent=2))
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
