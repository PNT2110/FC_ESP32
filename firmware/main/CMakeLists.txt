idf_component_register(SRCS "main.c" "mpu6500.c" "pid.c" "fc_command.c" "fc_radio.c" "fc_control.c"
    INCLUDE_DIRS "."
    REQUIRES driver esp_adc esp_wifi esp_event esp_netif esp_timer nvs_flash)
