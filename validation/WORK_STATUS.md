# Motor-pad inset and routing

Requested change: J4–J7 move 1.5 mm radially inward, keeping motor centers at
(66.6,66.6), (133.4,66.6), (133.4,133.4), (66.6,133.4) mm. J2 remains at
90 degrees facing the right edge. Generator and placement enforce these choices.

J8 moved to the upper right central board to avoid blocking the lower-right arm.
The custom expansion headers now include their housing courtyards.

Current placement invariants: `FC_ESP32/invariant_audit.json`.
Current schematic ERC: `FC_ESP32/erc_current.json`.
Autorouting completed: `validation/routing_header.log`. Subsequent repair joined UART1_RX and lower-arm battery branches. Current authoritative remaining errors: `FC_ESP32/drc_current.json`. Upper battery branches and ground still require finishing. No routing process remains live.
Do not use older DRC summaries to certify this regenerated layout.

Persistent local runtime:
- `/usr/bin/python3`, KiCad 10 pcbnew
- `PYTHONPATH=/home/pnt/miniconda3/lib/python3.14/site-packages`
- Freerouting: `/home/pnt/.cache/fc_esp32/toolchain/freerouting-2.4.1-linux-x64/bin/freerouting`

After routing: import SES (retains locked fanout and restores project rules),
fill copper, run `tools/validate_fc.py` and `tools/audit_board.py`. Review the
physical track widths, not only netclass defaults. The R3/R4 voltage sense branch
has a separately calculated low-current exception in `tools/finish_routes.py`;
its UUID review must be recreated after every import.

Power-priority pass: all VBAT pads now connected (KiCad DRC verified before routing other nets). R3/R4 sense branch is 13.004 mm at 0.4 mm, reviewed in adc_branch_review.json. BOOST_SW fixed fanout removed due to overlap with new sense via; it must be rerouted. Live autorouter log: validation/routing_power_priority.log. Main PCB currently contains locked battery routing and fixed IC escapes; remaining nets are being routed.
