#ifndef MPU6500_H
#define MPU6500_H

#include <stdint.h>
#include "fc_control.h"
#include "esp_err.h"
#include "driver/spi_master.h"

#define MPU6500_WHO_AM_I 0x75
#define MPU6500_PWR_MGMT_1 0x6B
#define MPU6500_ACCEL_XOUT_H 0x3B
#define MPU6500_GYRO_XOUT_H 0x43

esp_err_t mpu6500_init(spi_device_handle_t device);
esp_err_t mpu6500_read_sample(fc_imu_t *sample);
esp_err_t mpu6500_read_accel(float *x, float *y, float *z);
esp_err_t mpu6500_read_gyro(float *x, float *y, float *z);

#endif
