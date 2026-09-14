#pragma once
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"
typedef void *spi_device_handle_t;
#define SPI_TRANS_USE_TXDATA 1
// Host double: only the fields used by this driver.
typedef struct {
    size_t length, rxlength;
    unsigned flags;
    uint8_t tx_data[4];
    const void *tx_buffer;
    void *rx_buffer;
} spi_transaction_t;
esp_err_t spi_device_transmit(spi_device_handle_t, spi_transaction_t *);
