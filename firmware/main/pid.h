#ifndef PID_H
#define PID_H

typedef struct {
    float kp;
    float ki;
    float kd;
    float integral;
    float prev_error;
    float max_integral;
    float max_output;
} pid_ctrl_t;

void pid_init(pid_ctrl_t *pid, float kp, float ki, float kd, float max_i, float max_out);
float pid_update(pid_ctrl_t *pid, float setpoint, float measured, float dt);
void pid_reset(pid_ctrl_t *pid);

#endif
