# Firmware bring-up

Current firmware includes MPU-6500 acquisition, gyro calibration, attitude estimation,
PID/mixing, battery monitoring and an ESP-NOW command/arming/failsafe path.
Motor actuation is disabled by default (`CONFIG_FC_ENABLE_MOTORS`); the default
build keeps PWM outputs at zero. Host tests pass for the sensor driver, protocol,
arming/failsafe and controller fault/output limits. These tests do not establish
stable flight: transmitter integration, sensor axes, motor order, control tuning
and battery behavior still require hardware testing.

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
