#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/ledc.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "esp_adc/adc_oneshot.h"
#include "hal/adc_types.h"
#include "mpu6500.h"
#include "fc_radio.h"
#include "fc_control.h"
#include "esp_timer.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "sdkconfig.h"

static const char *TAG = "FC_MAIN";

// Motor PWM Pins
#define MOTOR1_PIN 25
#define MOTOR2_PIN 26
#define MOTOR3_PIN 27
#define MOTOR4_PIN 33

// MPU-6500 SPI Pins
#define MPU_MISO_PIN 19
#define MPU_MOSI_PIN 23
#define MPU_CLK_PIN  18
#define MPU_CS_PIN   21
#define MPU_INT_PIN  34
#define SPI_HOST    VSPI_HOST

// LEDC Configuration
#define LEDC_TIMER              LEDC_TIMER_0
#define LEDC_MODE               LEDC_LOW_SPEED_MODE
#define LEDC_DUTY_RES           LEDC_TIMER_13_BIT 
#define LEDC_FREQUENCY          400 

// Optical Flow (MTF-01P) UART2
#define OPTFLOW_UART_NUM UART_NUM_2
#define OPTFLOW_TX_PIN   GPIO_NUM_17
#define OPTFLOW_RX_PIN   GPIO_NUM_16
#define OPTFLOW_BUF_SIZE 256

// I2C Expansion
#define I2C_MASTER_SCL_IO           GPIO_NUM_22      
#define I2C_MASTER_SDA_IO           GPIO_NUM_4       
#define I2C_MASTER_NUM              I2C_NUM_0        
#define I2C_MASTER_FREQ_HZ          400000

// UART1 Expansion
#define EXP_UART_NUM UART_NUM_1
#define EXP_TX_PIN   GPIO_NUM_14
#define EXP_RX_PIN   GPIO_NUM_32

// Battery ADC
#define BATT_ADC_CHAN ADC_CHANNEL_7 // GPIO35
static adc_oneshot_unit_handle_t adc1_handle;
static adc_cali_handle_t adc_calibration;
i2c_master_bus_handle_t i2c_bus_handle;
static spi_device_handle_t spi_mpu;

static void init_motor_pwm(void) {
    ESP_LOGI(TAG, "Initializing Motor PWM...");
    ledc_timer_config_t ledc_timer = {
        .speed_mode       = LEDC_MODE,
        .timer_num        = LEDC_TIMER,
        .duty_resolution  = LEDC_DUTY_RES,
        .freq_hz          = LEDC_FREQUENCY,
        .clk_cfg          = LEDC_AUTO_CLK
    };
    ESP_ERROR_CHECK(ledc_timer_config(&ledc_timer));

    int motor_pins[4] = {MOTOR1_PIN, MOTOR2_PIN, MOTOR3_PIN, MOTOR4_PIN};
    for (int i = 0; i < 4; i++) {
        ledc_channel_config_t ledc_channel = {
            .speed_mode     = LEDC_MODE,
            .channel        = (ledc_channel_t)i,
            .timer_sel      = LEDC_TIMER,
            .intr_type      = LEDC_INTR_DISABLE,
            .gpio_num       = motor_pins[i],
            .duty           = 0,
            .hpoint         = 0
        };
        ESP_ERROR_CHECK(ledc_channel_config(&ledc_channel));
    }
}

static void init_mpu6500_spi(void) {
    ESP_LOGI(TAG, "Initializing MPU-6500 SPI...");
    spi_bus_config_t buscfg = {
        .miso_io_num = MPU_MISO_PIN,
        .mosi_io_num = MPU_MOSI_PIN,
        .sclk_io_num = MPU_CLK_PIN,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 32
    };
    
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 1000000,
        .mode = 3,
        .spics_io_num = MPU_CS_PIN,
        .queue_size = 7,
    };
    
    ESP_ERROR_CHECK(spi_bus_initialize(SPI_HOST, &buscfg, SPI_DMA_CH_AUTO));
    ESP_ERROR_CHECK(spi_bus_add_device(SPI_HOST, &devcfg, &spi_mpu));
    
    gpio_config_t int_conf = {
        .intr_type = GPIO_INTR_DISABLE,
        .pin_bit_mask = (1ULL << MPU_INT_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE
    };
    ESP_ERROR_CHECK(gpio_config(&int_conf));
}

void battery_adc_init(void) {
    adc_oneshot_unit_init_cfg_t init_config = {
        .unit_id = ADC_UNIT_1,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_config, &adc1_handle));

    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc1_handle, BATT_ADC_CHAN, &config));
    adc_cali_line_fitting_config_t cal = {
        .unit_id=ADC_UNIT_1, .atten=ADC_ATTEN_DB_12,
        .bitwidth=ADC_BITWIDTH_DEFAULT, .default_vref=1100,
    };
    ESP_ERROR_CHECK(adc_cali_create_scheme_line_fitting(&cal, &adc_calibration));
}

void optflow_uart_init(void) {
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_ERROR_CHECK(uart_param_config(OPTFLOW_UART_NUM, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(OPTFLOW_UART_NUM, OPTFLOW_TX_PIN, OPTFLOW_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(OPTFLOW_UART_NUM, OPTFLOW_BUF_SIZE * 2, 0, 0, NULL, 0));
}

void exp_uart_init(void) {
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_ERROR_CHECK(uart_param_config(EXP_UART_NUM, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(EXP_UART_NUM, EXP_TX_PIN, EXP_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(EXP_UART_NUM, 256 * 2, 0, 0, NULL, 0));
}

void i2c_master_init(void) {
    i2c_master_bus_config_t i2c_bus_config = {
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .i2c_port = I2C_MASTER_NUM,
        .scl_io_num = I2C_MASTER_SCL_IO,
        .sda_io_num = I2C_MASTER_SDA_IO,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    ESP_ERROR_CHECK(i2c_new_master_bus(&i2c_bus_config, &i2c_bus_handle));
}

static bool write_motors(const float duty[4]) {
    for (int i=0;i<4;i++) {
#ifdef CONFIG_FC_ENABLE_MOTORS
        uint32_t value=(uint32_t)(duty[i]*8191.0f);
#else
        (void)duty;
        uint32_t value=0;
#endif
        if (ledc_set_duty(LEDC_MODE,(ledc_channel_t)i,value)!=ESP_OK ||
            ledc_update_duty(LEDC_MODE,(ledc_channel_t)i)!=ESP_OK) {
            for (int j=0;j<4;j++)ledc_stop(LEDC_MODE,(ledc_channel_t)j,0);
            return false;
        }
    }
    return true;
}

static void sensor_task(void *pvParameters) {
    (void)pvParameters;
    fc_control_t controller;
    fc_control_init(&controller);
    TickType_t wake=xTaskGetTickCount();
    const TickType_t period=pdMS_TO_TICKS(2);
    configASSERT(period>0);
    int64_t last=esp_timer_get_time(),last_adc=0,last_log=0;
    float battery=0;
    bool battery_ok=false;
    while (1) {
        int64_t now=esp_timer_get_time();
        float dt=(now-last)*1e-6f;
        last=now;
        fc_command_t command;
        bool link_armed=fc_radio_snapshot(&command);
        fc_imu_t sample;
        esp_err_t imu_error=mpu6500_read_sample(&sample);
        if (now-last_adc>=20000) {
            int raw,mv;
            battery_ok=adc_oneshot_read(adc1_handle,BATT_ADC_CHAN,&raw)==ESP_OK &&
                adc_cali_raw_to_voltage(adc_calibration,raw,&mv)==ESP_OK;
            if (battery_ok)battery=mv*.002f; // 100k/100k divider
            battery_ok=battery_ok && battery>=3.5f && battery<=4.45f;
            last_adc=now;
        }
        float motors[4]={0};
        if (imu_error!=ESP_OK || !battery_ok) {
            // Fault recovery requires calibration and a new disarm/arm sequence.
            fc_control_init(&controller);
        } else {
            fc_control_step(&controller,&sample,&command,link_armed,dt,motors);
        }
        if (!write_motors(motors))fc_control_init(&controller);
        if (now-last_log>=1000000) {
            ESP_LOGI(TAG,"battery=%.2f V ready=%d armed=%d roll=%.1f pitch=%.1f",
                battery,controller.ready,controller.armed,controller.roll,controller.pitch);
            last_log=now;
        }
        vTaskDelayUntil(&wake,period);
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "Starting FC_ESP32 Flight Controller...");
#ifndef CONFIG_FC_ENABLE_MOTORS
    ESP_LOGW(TAG,"Motor outputs inhibited by build configuration");
#endif
    init_motor_pwm();
    init_mpu6500_spi();
    ESP_ERROR_CHECK(mpu6500_init(spi_mpu));
    battery_adc_init();
    optflow_uart_init();
    exp_uart_init();
    i2c_master_init();
    esp_err_t radio_error = fc_radio_init();
    if (radio_error != ESP_OK)
        ESP_LOGW(TAG, "ESP-NOW unavailable: %s; configure peer MAC and keys", esp_err_to_name(radio_error));
    
    if (xTaskCreate(sensor_task, "sensor_task", 4096, NULL, 5, NULL) != pdPASS) {
        ESP_LOGE(TAG, "Could not create sensor task; motors remain stopped");
    }
}
