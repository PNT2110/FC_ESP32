#pragma once
#include "esp_err.h"
#include "fc_command.h"
esp_err_t fc_radio_init(void);
bool fc_radio_snapshot(fc_command_t *command);
