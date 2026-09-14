#include "fc_control.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
static void zero(const float m[4]) {for (int i=0;i<4;i++)assert(m[i]==0);}
int main(void) {
    fc_control_t s;fc_control_init(&s);
    fc_imu_t imu={.az=1,.gx=.2f,.gy=-.1f,.gz=.3f};
    fc_command_t c={0};float motors[4];
    for (int i=0;i<500;i++) {
        assert(!fc_control_step(&s,&imu,&c,true,.002f,motors));zero(motors);
    }
    assert(s.ready && !s.armed);
    assert(!fc_control_step(&s,&imu,&c,true,.002f,motors)); // cannot arm during calibration
    assert(!fc_control_step(&s,&imu,&c,false,.002f,motors));
    assert(fc_control_step(&s,&imu,&c,true,.002f,motors));zero(motors);
    c.throttle=500;
    assert(fc_control_step(&s,&imu,&c,true,.002f,motors));
    for(int i=0;i<4;i++)assert(fabsf(motors[i]-.5f)<.001f);
    assert(!fc_control_step(&s,&imu,&c,false,.002f,motors));zero(motors);
    assert(!fc_control_step(&s,&imu,&c,true,.002f,motors));zero(motors);
    c.throttle=0;fc_control_step(&s,&imu,&c,false,.002f,motors);
    assert(fc_control_step(&s,&imu,&c,true,.002f,motors));
    c.throttle=1000;c.roll=1000;c.pitch=-1000;c.yaw=1000;
    assert(fc_control_step(&s,&imu,&c,true,.002f,motors));
    for(int i=0;i<4;i++)assert(isfinite(motors[i])&&motors[i]>=0&&motors[i]<=1);
    assert(!fc_control_step(&s,&imu,&c,true,0,motors));zero(motors);
    imu.gx=NAN;
    assert(!fc_control_step(&s,&imu,&c,true,.002f,motors));zero(motors);
    fc_control_init(&s);imu=(fc_imu_t){.ax=1};
    for(int i=0;i<600;i++)fc_control_step(&s,&imu,&c,false,.002f,motors);
    assert(!s.ready); // sideways board must not calibrate
    puts("Controller calibration, arming, output limits and fault tests passed");
}
