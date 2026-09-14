#include "fc_control.h"
#include <math.h>
#include <string.h>
#define DEG 57.2957795131f
#define CALIBRATION_SAMPLES 500
static float limit(float x,float low,float high) { return fminf(high,fmaxf(low,x)); }
void fc_control_init(fc_control_t *s) {
    memset(s,0,sizeof(*s));
    // Provisional normalized-output gains. Bench tuning is mandatory.
    pid_init(&s->roll_pid,.0012f,.0004f,.00001f,100,.25f);
    pid_init(&s->pitch_pid,.0012f,.0004f,.00001f,100,.25f);
    pid_init(&s->yaw_pid,.0015f,.0004f,0,100,.25f);
}
static void stop(fc_control_t *s) {
    s->armed=false; s->arm_allowed=false;
    pid_reset(&s->roll_pid);pid_reset(&s->pitch_pid);pid_reset(&s->yaw_pid);
}
bool fc_control_step(fc_control_t *s,const fc_imu_t *v,const fc_command_t *c,
                     bool link_armed,float dt,float motors[4]) {
    memset(motors,0,4*sizeof(float));
    if (!isfinite(v->ax)||!isfinite(v->ay)||!isfinite(v->az)||!isfinite(v->gx)||
        !isfinite(v->gy)||!isfinite(v->gz)||!isfinite(dt)||dt<.0005f||dt>.01f) {
        stop(s); return false;
    }
    float magnitude=sqrtf(v->ax*v->ax+v->ay*v->ay+v->az*v->az);
    float accel_roll=atan2f(v->ay,v->az)*DEG;
    float accel_pitch=atan2f(-v->ax,hypotf(v->ay,v->az))*DEG;
    if (!s->ready) {
        stop(s);
        if (magnitude<.9f||magnitude>1.1f||fabsf(v->gx)>5||fabsf(v->gy)>5||
            fabsf(v->gz)>5||fabsf(accel_roll)>10||fabsf(accel_pitch)>10) {
            s->calibration_samples=0;memset(s->bias,0,sizeof(s->bias));return false;
        }
        s->bias[0]+=v->gx;s->bias[1]+=v->gy;s->bias[2]+=v->gz;
        if (++s->calibration_samples==CALIBRATION_SAMPLES) {
            for (int i=0;i<3;i++)s->bias[i]/=CALIBRATION_SAMPLES;
            s->roll=accel_roll;s->pitch=accel_pitch;s->ready=true;
        }
        return false;
    }
    float gx=v->gx-s->bias[0],gy=v->gy-s->bias[1],gz=v->gz-s->bias[2];
    // Complementary filter, 0.5 s accelerometer correction time constant.
    float alpha=.5f/(.5f+dt);
    s->roll+=gx*dt;s->pitch+=gy*dt;
    if (magnitude>.8f && magnitude<1.2f) {
        s->roll=alpha*s->roll+(1-alpha)*accel_roll;
        s->pitch=alpha*s->pitch+(1-alpha)*accel_pitch;
    }
    if (fabsf(s->roll)>60 || fabsf(s->pitch)>60) {stop(s);return false;}
    if (!link_armed) {stop(s);s->arm_allowed=c->throttle==0;return false;}
    if (!s->armed) {
        s->armed=s->arm_allowed && c->throttle==0;s->arm_allowed=false;
        if (!s->armed)return false;
    }
    if (c->throttle==0) {
        pid_reset(&s->roll_pid);pid_reset(&s->pitch_pid);pid_reset(&s->yaw_pid);
        return true;
    }
    float roll_rate=limit((c->roll*.020f-s->roll)*4,-150,150);
    float pitch_rate=limit((c->pitch*.020f-s->pitch)*4,-150,150);
    float roll=pid_update(&s->roll_pid,roll_rate,gx,dt);
    float pitch=pid_update(&s->pitch_pid,pitch_rate,gy,dt);
    float yaw=pid_update(&s->yaw_pid,c->yaw*.12f,gz,dt);
    float throttle=c->throttle*.001f;
    // NW, NE, SE, SW. Signs/rotation direction need a restrained bench check.
    motors[0]=limit(throttle-pitch+roll+yaw,0,1);
    motors[1]=limit(throttle-pitch-roll-yaw,0,1);
    motors[2]=limit(throttle+pitch-roll+yaw,0,1);
    motors[3]=limit(throttle+pitch+roll-yaw,0,1);
    return true;
}
