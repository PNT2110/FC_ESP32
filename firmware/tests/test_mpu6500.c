#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "mpu6500.h"

static uint8_t regs[128];
static int fail_transfer;
esp_err_t spi_device_transmit(spi_device_handle_t dev, spi_transaction_t *t) {
    assert(dev);
    if (fail_transfer) return ESP_FAIL;
    if (t->flags & SPI_TRANS_USE_TXDATA) {
        assert(t->length == 16);
        regs[t->tx_data[0]] = t->tx_data[1];
    } else {
        assert(t->length <= 120 && t->length % 8 == 0);
        const uint8_t *tx = t->tx_buffer;
        uint8_t *rx = t->rx_buffer;
        assert(tx && rx && (tx[0] & 0x80));
        rx[0] = 0xFF; // Address-phase garbage must never become sensor data.
        for (size_t i = 1; i < t->length / 8; ++i)
            rx[i] = regs[(tx[0] & 0x7F) + i - 1];
    }
    return ESP_OK;
}
static void word(unsigned reg, int16_t value) {
    regs[reg] = (uint16_t)value >> 8;
    regs[reg+1] = (uint16_t)value & 255;
}
int main(void) {
    float x = 99, y = 99, z = 99;
    assert(mpu6500_init(NULL) == ESP_ERR_INVALID_ARG);
    assert(mpu6500_read_accel(&x,&y,&z) != ESP_OK);
    regs[0x75] = 0x71;
    assert(mpu6500_init((void *)1) == ESP_ERR_NOT_FOUND);
    regs[0x75] = 0x70;
    fail_transfer = 1;
    assert(mpu6500_init((void *)1) == ESP_FAIL);
    fail_transfer = 0;
    assert(mpu6500_init((void *)1) == ESP_OK);
    assert(regs[0x1B] == 0x18 && regs[0x1C] == 0x10);
    word(0x3B,4096); word(0x3D,-4096); word(0x3F,0);
    assert(mpu6500_read_accel(&x,&y,&z) == ESP_OK);
    assert(x == 1 && y == -1 && z == 0);
    word(0x43,1640); word(0x45,-1640); word(0x47,0);
    assert(mpu6500_read_gyro(&x,&y,&z) == ESP_OK);
    assert(fabsf(x-100)<0.001 && fabsf(y+100)<0.001 && z==0);
    assert(mpu6500_read_gyro(NULL,&y,&z) == ESP_ERR_INVALID_ARG);
    fc_imu_t sample;
    assert(mpu6500_read_sample(&sample)==ESP_ERR_INVALID_STATE);
    regs[0x3A]=1;
    assert(mpu6500_read_sample(&sample)==ESP_OK);
    assert(sample.ax==1 && sample.ay==-1 && fabsf(sample.gx-100)<.001f);
    fail_transfer = 1;
    x = 99;
    assert(mpu6500_read_accel(&x,&y,&z) != ESP_OK && x == 99);
    puts("MPU6500 host regression tests passed");
}
