#include "fc_command.h"
#include <string.h>
static uint16_t get16(const uint8_t *p) { return p[0] | (uint16_t)p[1] << 8; }
static uint32_t get32(const uint8_t *p) { return get16(p) | (uint32_t)get16(p+2) << 16; }
static void put16(uint8_t *p, uint16_t v) { p[0]=v; p[1]=v>>8; }
static void put32(uint8_t *p, uint32_t v) { put16(p,v); put16(p+2,v>>16); }
bool fc_command_decode(const uint8_t *p, size_t size, fc_command_t *out) {
    if (!p || !out || size != FC_PACKET_SIZE || memcmp(p,"FC01",4) ||
        p[20] > 1 || p[21] || p[22] || p[23]) return false;
    fc_command_t c = {.session=get32(p+4), .sequence=get32(p+8),
        .throttle=get16(p+12), .roll=(int16_t)get16(p+14),
        .pitch=(int16_t)get16(p+16), .yaw=(int16_t)get16(p+18), .arm=p[20]};
    if (c.throttle > 1000 || c.roll < -1000 || c.roll > 1000 ||
        c.pitch < -1000 || c.pitch > 1000 || c.yaw < -1000 || c.yaw > 1000) return false;
    *out=c;
    return true;
}
void fc_command_encode(const fc_command_t *c, uint8_t out[FC_PACKET_SIZE]) {
    memset(out,0,FC_PACKET_SIZE); memcpy(out,"FC01",4);
    put32(out+4,c->session); put32(out+8,c->sequence); put16(out+12,c->throttle);
    put16(out+14,c->roll); put16(out+16,c->pitch); put16(out+18,c->yaw); out[20]=c->arm;
}
bool fc_link_armed(fc_link_state_t *s, int64_t now) {
    if (!s->have_packet || now < s->received_us || now-s->received_us >= FC_LINK_TIMEOUT_US) {
        s->armed=false; s->ready_to_arm=false;
    }
    return s->armed;
}
bool fc_link_accept(fc_link_state_t *s, const fc_command_t *c, int64_t now) {
    fc_link_armed(s,now);
    if (!s->have_packet || c->session != s->command.session) {
        // A new transmitter boot must first announce disarmed at zero throttle.
        if (c->arm || c->throttle != 0) return false;
        s->armed=false; s->ready_to_arm=false;
    } else {
        uint32_t advance = c->sequence - s->command.sequence;
        if (!advance || advance >= UINT32_C(0x80000000)) return false;
    }
    if (!c->arm) {
        s->armed=false;
        s->ready_to_arm=c->throttle == 0;
    } else if (!s->armed) {
        s->armed=s->ready_to_arm && c->throttle == 0;
        s->ready_to_arm=false;
    }
    s->command=*c; s->received_us=now; s->have_packet=true;
    return true;
}
