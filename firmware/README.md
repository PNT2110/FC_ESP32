# Firmware bring-up

Current firmware initializes peripherals and logs MPU-6500 acceleration and angular
rates at 10 Hz. All four motor PWM outputs start and remain at zero. The old mock
attitude/throttle loop has been removed. This is not flight firmware: estimator, calibration, tuned control, battery cutoff and transmitter hardware
integration are still required before powered flight. The ESP-NOW receiver and
logical arming/failsafe gate are implemented and tested; the gate is intentionally
not connected to motor actuation during bring-up.

Verified build: ESP-IDF 5.4.2, ESP32 target. Uses `driver/i2c_master.h` and `esp_adc/adc_oneshot.h`:

```sh
idf.py set-target esp32
idf.py build
```

Run from this directory after sourcing the ESP-IDF `export.sh`. The current validation SDK is `/tmp/fc-esp-idf` and its tool installation is
`/tmp/fc-idf-tools` (`IDF_TOOLS_PATH`). These temporary paths do not survive cleanup.
Host SPI regression tests (from repository root):

```sh
bash firmware/tests/run.sh
```

They verify SPI byte alignment, signed conversion, sensor range configuration,
identity rejection and transfer failure handling. They do not emulate electrical
hardware or replace an ESP32 build/bench test.

Driver references:
- https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6500-Register-Map2.pdf
- https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/spi_master.html
