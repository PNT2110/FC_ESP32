#include "fc_command.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    uint8_t packet[FC_PACKET_SIZE];
    fc_command_t c={.session=123,.sequence=1,.roll=-1000,.pitch=1000}, d;
    fc_command_encode(&c,packet);
    assert(fc_command_decode(packet,sizeof(packet),&d));
    assert(d.session==123 && d.roll==-1000 && d.pitch==1000);
    assert(!fc_command_decode(packet,sizeof(packet)-1,&d));
    packet[23]=1; assert(!fc_command_decode(packet,sizeof(packet),&d)); packet[23]=0;
    packet[12]=0xff; packet[13]=0xff;
    assert(!fc_command_decode(packet,sizeof(packet),&d));
    fc_link_state_t s={0};
    c.arm=true; assert(!fc_link_accept(&s,&c,1));
    c.arm=false; assert(fc_link_accept(&s,&c,2));
    c.arm=true; c.sequence++; c.throttle=1;
    assert(fc_link_accept(&s,&c,3)); assert(!fc_link_armed(&s,3));
    c.throttle=0; c.sequence++;
    assert(fc_link_accept(&s,&c,4)); assert(!fc_link_armed(&s,4));
    c.arm=false; c.sequence++; assert(fc_link_accept(&s,&c,5));
    c.arm=true; c.sequence++; assert(fc_link_accept(&s,&c,6));
    assert(fc_link_armed(&s,6));
    c.throttle=500; c.sequence++; assert(fc_link_accept(&s,&c,7));
    assert(fc_link_armed(&s,7));
    assert(!fc_link_accept(&s,&c,8)); // duplicate cannot refresh freshness
    assert(fc_link_armed(&s,7+FC_LINK_TIMEOUT_US-1));
    assert(!fc_link_armed(&s,7+FC_LINK_TIMEOUT_US));
    c.sequence++; c.throttle=0;
    assert(fc_link_accept(&s,&c,300000)); assert(!fc_link_armed(&s,300000));
    c.arm=false; c.sequence++; assert(fc_link_accept(&s,&c,300001));
    c.arm=true; c.sequence++; assert(fc_link_accept(&s,&c,300002));
    assert(fc_link_armed(&s,300002));
    c.session++; assert(!fc_link_accept(&s,&c,300003));
    c.arm=false; c.sequence=UINT32_MAX;
    assert(fc_link_accept(&s,&c,300004));
    c.arm=true; c.sequence=0;
    assert(fc_link_accept(&s,&c,300005)); // defined sequence wrap
    assert(fc_link_armed(&s,300005));
    c.sequence=UINT32_MAX; assert(!fc_link_accept(&s,&c,300006));
    c.sequence=1; c.arm=false; assert(fc_link_accept(&s,&c,300007));
    assert(!fc_link_armed(&s,300007));
    puts("ESP-NOW protocol and arming/failsafe tests passed");
}
