#include "pid.h"
#include <math.h>

void pid_init(pid_ctrl_t *pid, float kp, float ki, float kd, float max_i, float max_out) {
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->max_integral = max_i;
    pid->max_output = max_out;
}

float pid_update(pid_ctrl_t *pid, float setpoint, float measured, float dt) {
    if (!isfinite(dt) || dt <= 0 || !isfinite(setpoint) || !isfinite(measured)) {
        pid_reset(pid);
        return 0;
    }
    float error = setpoint - measured;
    
    pid->integral += error * dt;
    if (pid->integral > pid->max_integral) pid->integral = pid->max_integral;
    else if (pid->integral < -pid->max_integral) pid->integral = -pid->max_integral;
    
    float derivative = (error - pid->prev_error) / dt;
    pid->prev_error = error;
    
    float output = (pid->kp * error) + (pid->ki * pid->integral) + (pid->kd * derivative);
    
    if (output > pid->max_output) output = pid->max_output;
    else if (output < -pid->max_output) output = -pid->max_output;
    
    return output;
}

void pid_reset(pid_ctrl_t *pid) {
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
}
