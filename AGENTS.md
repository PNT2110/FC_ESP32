# Agent Notes

## Scope and source of truth

- This is a KiCad 10 ESP32-WROOM-32 flight controller for a 1S brushed quad; the project files live in `FC_ESP32/`, local symbols/footprints in `Library/`, firmware in `firmware/`, and PCB automation in `tools/`.
- `tools/build_fc.py` is the reproducible generator for the schematic pages, PCB, project settings, BOM, and `design.json`; edit the generator when changing generated hardware, then regenerate rather than hand-editing generated outputs.
- `FC_ESP32/drc_report.txt` is a historical report and currently records 16 unconnected-pad errors plus warnings; rerun DRC after every routing or generator change and do not treat a visually plausible board as electrically complete.

## KiCad workflow

- Run the generator with the system Python/KiCad Python environment because it imports `pcbnew`, `sexpdata`, and Shapely: `python3 tools/build_fc.py`.
- KiCad CLI is also required by the generator for netlist export; missing `pcbnew`, Python packages, or `kicad-cli` means generation cannot be trusted.
- Open `FC_ESP32/FC_ESP32.kicad_pro` in KiCad. Verify schematic-to-footprint pin numbering, connector orientation (especially J2 optical-flow pins 3/4), then run schematic ERC and PCB DRC before manufacturing.
- Use `kicad-cli sch export netlist FC_ESP32/FC_ESP32.kicad_sch -o FC_ESP32/FC_ESP32.net --format kicadxml` when a netlist is needed outside the generator; export Gerbers/position files only from the verified PCB.
- Preserve the explicit net classes: Battery 1.2 mm, MotorPower 0.8 mm, LogicPower 0.4 mm, Default 0.18 mm. Do not reduce motor/battery widths to save parts or area without checking current, heating, and voltage drop.

## Hardware review constraints

- Firmware pin assignments in `firmware/main/main.c` must agree with the generated schematic: PWM GPIO25/26/27/33, MPU SPI 19/23/18/21 and INT34, optical-flow UART2 17/16, I2C 4/22, UART1 14/32, battery ADC GPIO35.
- “Fewer components” is not automatically an improvement: retain regulator input/output/bypass, gate pulldown, USB ESD/CC, battery filtering, and motor flyback/protection parts unless datasheet calculations and DRC justify removal.
- For aerodynamic/mechanical review, treat the four motor centers, 40 mm prop diameter, 66.8 mm nearest pitch (confirmed by user on 2026-09-14), 0.8 mm board thickness, and the antenna keepout in `FC_ESP32/FC_ESP32.kicad_pcb` as design constraints; PCB optimization must not intrude into propeller discs, motor holes, antenna clearance, or shift mass far from the center.
- Validate electrical changes against datasheets and the 1S operating range; this repository contains prototype/mock control code, so firmware behavior is not evidence that the power or motor hardware is safe.

## Manufacturing files

- `BOM_JLCPCB.csv` and `gerbers/` may be stale relative to generated files. Regenerate/inspect outputs and compare references, values, footprints, and sides before sending an order.
- Local footprint and 3D-model sources are under `Library/`; do not silently substitute footprints with different pad numbering or thermal/current capability.
