#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define FC_PACKET_SIZE 24
#define FC_LINK_TIMEOUT_US 250000

typedef struct {
    uint32_t session, sequence;
    uint16_t throttle; // 0..1000
    int16_t roll, pitch, yaw; // -1000..1000 normalized sticks
    bool arm;
} fc_command_t;
typedef struct {
    bool have_packet, ready_to_arm, armed;
    int64_t received_us;
    fc_command_t command;
} fc_link_state_t;
bool fc_command_decode(const uint8_t *data, size_t size, fc_command_t *out);
void fc_command_encode(const fc_command_t *command, uint8_t out[FC_PACKET_SIZE]);
bool fc_link_accept(fc_link_state_t *state, const fc_command_t *command, int64_t now_us);
bool fc_link_armed(fc_link_state_t *state, int64_t now_us);
