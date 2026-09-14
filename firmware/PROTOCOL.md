# ESP-NOW command protocol v1

Use encrypted unicast ESP-NOW on channel 6 (configurable), station interface on
both devices. Configure transmitter MAC without separators, PMK and peer LMK in
`idf.py menuconfig` → FC ESP-NOW receiver. Keys must be 16 bytes represented by
32 hexadecimal digits and match the transmitter. Empty defaults disable radio
initialization; they are not shared production credentials.

Send 50–100 packets/second. Use `fc_command_encode` from `main/fc_command.c` on
the transmitter; never transmit the in-memory C struct. Each packet is 24 bytes:

| Offset | Length | Field |
|---|---|---|
| 0 | 4 | ASCII `FC01` |
| 4 | 4 | Random session ID generated at transmitter boot |
| 8 | 4 | Increasing sequence number, wraps at 2^32 |
| 12 | 2 | Throttle 0–1000 |
| 14 | 2 | Signed roll stick −1000–1000 |
| 16 | 2 | Signed pitch stick −1000–1000 |
| 18 | 2 | Signed yaw stick −1000–1000 |
| 20 | 1 | Arm switch: 0 or 1 |
| 21 | 3 | Reserved, all zero |

Integers are little-endian. Stick axes are normalized inputs, not angles, rates,
or PWM values. Aircraft axis mapping must be defined and bench-checked when the
controller is implemented.

The receiver rejects wrong lengths, magic, reserved bytes, value ranges, source
MAC, broadcast destination, duplicate or backwards sequence numbers. A new
session must first send disarmed with throttle zero. Arming requires a disarmed
zero-throttle packet followed by an armed zero-throttle packet. A high-throttle
arm attempt consumes this permission: switch off and retry at zero throttle.

After 250 ms without a fresh accepted packet the logical gate closes. Continuing
to send arm=1 cannot rearm it: a new disarm/zero-throttle step is required. A new
session also resets the gate. Packet processing runs in the Wi-Fi callback;
control code calls `fc_radio_snapshot` periodically to evaluate link freshness.

The current bring-up task polls at 100 ms. Consequently a future motor control
integration must use its own fast periodic deadline and stop outputs on a false
snapshot; this code does not promise a 250 ms physical motor-stop latency. Motors
are permanently inhibited in the current build.

The MAC filter and sequence checks supplement ESP-NOW, not application-level
cryptographic authentication. Validation so far covers the codec/gate with host
tests and an ESP32 build. Two-device radio, key-mismatch and loss-of-link bench
tests remain required.
