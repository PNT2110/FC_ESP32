#pragma once
#include <stdbool.h>
#include "pid.h"
#include "fc_command.h"
typedef struct { float ax,ay,az,gx,gy,gz; } fc_imu_t;
typedef struct {
    unsigned calibration_samples;
    float bias[3], roll, pitch;
    bool ready, armed, arm_allowed;
    pid_ctrl_t roll_pid, pitch_pid, yaw_pid;
} fc_control_t;
void fc_control_init(fc_control_t *state);
// Body axes must be verified on the physical board. Outputs are normalized 0..1.
bool fc_control_step(fc_control_t *state, const fc_imu_t *imu,
    const fc_command_t *command, bool link_armed, float dt, float motors[4]);
