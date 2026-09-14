#include "mpu6500.h"
#include "driver/spi_master.h"
#include "esp_log.h"
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static spi_device_handle_t spi_mpu;
static const char *TAG = "MPU6500";

static esp_err_t mpu_write_byte(uint8_t reg, uint8_t data) {
    spi_transaction_t t = {
        .length = 16,
        .tx_data = {reg, data},
        .flags = SPI_TRANS_USE_TXDATA,
    };
    return spi_device_transmit(spi_mpu, &t);
}

static esp_err_t mpu_read_bytes(uint8_t reg, uint8_t *data, size_t len) {
    if (!spi_mpu || !data || len == 0 || len > 14) return ESP_ERR_INVALID_ARG;
    // Full-duplex SPI clocks one address byte followed by the payload.
    uint8_t tx[15] = {reg | 0x80};
    uint8_t rx[15] = {0};
    spi_transaction_t t = {
        .length = (len + 1) * 8,
        .tx_buffer = tx,
        .rx_buffer = rx,
    };
    esp_err_t err = spi_device_transmit(spi_mpu, &t);
    if (err == ESP_OK) memcpy(data, rx + 1, len);
    return err;
}

esp_err_t mpu6500_init(spi_device_handle_t device) {
    spi_mpu = device;
    if (!device) return ESP_ERR_INVALID_ARG;
    esp_err_t err = mpu_write_byte(MPU6500_PWR_MGMT_1, 0x80);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(100));
    uint8_t whoami = 0;
    err = mpu_read_bytes(MPU6500_WHO_AM_I, &whoami, 1);
    if (err != ESP_OK) return err;
    if (whoami != 0x70) {
        ESP_LOGE(TAG, "MPU6500 NOT FOUND! WHO_AM_I = 0x%02X", whoami);
        return ESP_ERR_NOT_FOUND;
    }
    // Register map RM-MPU-6500A-00: PLL clock, all axes on, SPI-only,
    // 1 kHz sample rate (read by the 500 Hz control loop); +/-2000 dps and +/-8 g.
    const uint8_t config[][2] = {
        {0x6B, 0x01}, {0x6C, 0x00}, {0x6A, 0x10},
        {0x1A, 0x03}, {0x19, 0x00}, {0x1B, 0x18}, {0x1C, 0x10},
        {0x1D, 0x03}, {0x38, 0x01},
    };
    for (size_t i = 0; i < sizeof(config) / sizeof(config[0]); ++i) {
        err = mpu_write_byte(config[i][0], config[i][1]);
        if (err != ESP_OK) return err;
    }
    vTaskDelay(pdMS_TO_TICKS(100));
    ESP_LOGI(TAG, "MPU6500 initialized");
    return ESP_OK;
}

esp_err_t mpu6500_read_accel(float *x, float *y, float *z) {
    if (!x || !y || !z) return ESP_ERR_INVALID_ARG;
    uint8_t data[6];
    if (mpu_read_bytes(MPU6500_ACCEL_XOUT_H, data, 6) != ESP_OK) return ESP_FAIL;
    int16_t ax = (data[0] << 8) | data[1];
    int16_t ay = (data[2] << 8) | data[3];
    int16_t az = (data[4] << 8) | data[5];
    // Assuming +/- 8g
    *x = ax / 4096.0f;
    *y = ay / 4096.0f;
    *z = az / 4096.0f;
    return ESP_OK;
}

esp_err_t mpu6500_read_gyro(float *x, float *y, float *z) {
    if (!x || !y || !z) return ESP_ERR_INVALID_ARG;
    uint8_t data[6];
    if (mpu_read_bytes(MPU6500_GYRO_XOUT_H, data, 6) != ESP_OK) return ESP_FAIL;
    int16_t gx = (data[0] << 8) | data[1];
    int16_t gy = (data[2] << 8) | data[3];
    int16_t gz = (data[4] << 8) | data[5];
    // Assuming +/- 2000 dps
    *x = gx / 16.4f;
    *y = gy / 16.4f;
    *z = gz / 16.4f;
    return ESP_OK;
}

esp_err_t mpu6500_read_sample(fc_imu_t *sample) {
    if (!sample) return ESP_ERR_INVALID_ARG;
    uint8_t status=0;
    esp_err_t err=mpu_read_bytes(0x3A,&status,1);
    if (err!=ESP_OK)return err;
    if (!(status&1))return ESP_ERR_INVALID_STATE;
    uint8_t data[14];
    err=mpu_read_bytes(MPU6500_ACCEL_XOUT_H,data,sizeof(data));
    if (err!=ESP_OK)return err;
    sample->ax=(int16_t)((uint16_t)data[0]<<8|data[1])/4096.0f;
    sample->ay=(int16_t)((uint16_t)data[2]<<8|data[3])/4096.0f;
    sample->az=(int16_t)((uint16_t)data[4]<<8|data[5])/4096.0f;
    sample->gx=(int16_t)((uint16_t)data[8]<<8|data[9])/16.4f;
    sample->gy=(int16_t)((uint16_t)data[10]<<8|data[11])/16.4f;
    sample->gz=(int16_t)((uint16_t)data[12]<<8|data[13])/16.4f;
    return ESP_OK;
}
