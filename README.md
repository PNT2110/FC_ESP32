# FC_ESP32 Flight Controller

An ESP32-WROOM-32 based flight controller designed for 1S brushed quadcopters.

## Features
- **MCU**: ESP32-WROOM-32 (8MB Flash)
- **IMU**: MPU-6500 (SPI interface)
- **Motor Drivers**: 4x AO3400 MOSFETs for brushed motors
- **Optical Flow**: UART interface for MTF-01P sensor (JST SH1.0 4-pin)
- **Power**: 1S LiPo input, TPS63001 Buck-Boost for 3.3V, TPS61070 Boost for 5V (USB/Optical flow)
- **USB**: USB-C connector with CH340C USB-to-UART bridge
- **Expansion**: I2C and UART1 breakout headers (2.54mm pitch)
- **Battery Monitor**: Built-in voltage divider for telemetry

## Hardware Setup & Pinout
- **Motors**: J4, J5, J6, J7 pads (AO3400 driven)
- **Optical Flow (J2)**: pin 1 GND, pin 2 +5V_FLOW, pin 3 ESP32 TX (GPIO17 → sensor RX), pin 4 ESP32 RX (GPIO16 ← sensor TX). Verify the actual sensor cable orientation.
- **I2C Expansion (J8)**: VCC, GND, SDA (GPIO4), SCL (GPIO22)
- **UART1 Expansion (J9)**: VCC, GND, TX (GPIO14), RX (GPIO32)
- **Programming**: CH340C DTR/RTS auto-download circuit; no physical Boot/Reset buttons are present in the generated BOM.

## Current status

Work in progress; not released for manufacturing or flight. Motor pitch is
66.8 mm, prop diameter 40 mm, board thickness 0.8 mm. Components are on the front;
copper routing uses both layers. Firmware currently provides sensor bring-up with
all motors stopped; see `firmware/README.md`.

## Reproducible hardware workflow

Use system Python with KiCad 10 `pcbnew`, `sexpdata` and Shapely installed.
The generator replaces the working PCB and therefore discards its routing.
Back up a routed board before regenerating.

```sh
/usr/bin/python3 tools/build_fc.py
/usr/bin/python3 tools/prepare_route.py
# Route the new FC_ESP32/FC_ESP32.dsn with Freerouting and save FC_ESP32.ses.
/usr/bin/python3 tools/import_route.py
/usr/bin/python3 tools/finish_copper.py
python3 tools/validate_fc.py
```

`build_fc.py` now includes clearance-preserving placement and updates the BOM and
design coordinates. Session import validates placement before replacing copper.
The legacy `critical_routes.py` and `repair_connections.py` contain assumptions
from the older layout and are not part of this workflow.

On the current machine the Python add-ons are under `/tmp/fc-pylibs`; prefix
system-Python commands with `PYTHONPATH=/tmp/fc-pylibs`. That temporary directory
is environment-specific and should be replaced with a persistent installation.

Open `FC_ESP32/FC_ESP32.kicad_pro` for review. Validation records current ERC,
DRC, netlist parity and source hashes in `FC_ESP32/validation_summary.json` and
returns nonzero on errors. Reports do not replace current/thermal analysis or
bench testing. `gerbers/` contains stale outputs, not an approved release.
