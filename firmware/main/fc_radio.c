#include "fc_radio.h"
#include <string.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_now.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
static uint8_t sender[6];
static fc_link_state_t state;
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
static int hex(char c) {
    if (c >= '0' && c <= '9') return c-'0';
    if (c >= 'a' && c <= 'f') return c-'a'+10;
    if (c >= 'A' && c <= 'F') return c-'A'+10;
    return -1;
}
static bool parse_hex(const char *s, uint8_t *out, size_t n) {
    if (strlen(s) != n*2) return false;
    for (size_t i=0;i<n;i++) {
        int a=hex(s[2*i]), b=hex(s[2*i+1]);
        if (a<0 || b<0) return false;
        out[i]=a*16+b;
    }
    return true;
}
static void receive(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
    fc_command_t command;
    // Configured peer only; broadcast packets must never operate the arm gate.
    if (!info || !info->src_addr || !info->des_addr ||
        (info->des_addr[0]&1) || memcmp(info->src_addr,sender,6) || len<0 ||
        !fc_command_decode(data,(size_t)len,&command)) return;
    int64_t now=esp_timer_get_time();
    portENTER_CRITICAL(&lock);
    fc_link_accept(&state,&command,now);
    portEXIT_CRITICAL(&lock);
}
esp_err_t fc_radio_init(void) {
    uint8_t pmk[16], lmk[16];
    if (!parse_hex(CONFIG_FC_TX_MAC,sender,6) || (sender[0]&1) ||
        !parse_hex(CONFIG_FC_PMK,pmk,16) || !parse_hex(CONFIG_FC_LMK,lmk,16))
        return ESP_ERR_INVALID_ARG;
    esp_err_t err=nvs_flash_init();
    if (err != ESP_OK) return err;
#define TRY(call) do { err=(call); if (err != ESP_OK) return err; } while (0)
    TRY(esp_netif_init());
    TRY(esp_event_loop_create_default());
    wifi_init_config_t cfg=WIFI_INIT_CONFIG_DEFAULT();
    TRY(esp_wifi_init(&cfg)); TRY(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    TRY(esp_wifi_set_mode(WIFI_MODE_STA)); TRY(esp_wifi_start());
    TRY(esp_wifi_set_ps(WIFI_PS_NONE));
    TRY(esp_wifi_set_channel(CONFIG_FC_RADIO_CHANNEL,WIFI_SECOND_CHAN_NONE));
    TRY(esp_now_init()); TRY(esp_now_set_pmk(pmk));
    esp_now_peer_info_t peer={.channel=CONFIG_FC_RADIO_CHANNEL,
        .ifidx=WIFI_IF_STA, .encrypt=true};
    memcpy(peer.peer_addr,sender,6); memcpy(peer.lmk,lmk,16);
    TRY(esp_now_add_peer(&peer)); TRY(esp_now_register_recv_cb(receive));
    return ESP_OK;
}
bool fc_radio_snapshot(fc_command_t *command) {
    int64_t now=esp_timer_get_time();
    portENTER_CRITICAL(&lock);
    bool armed=fc_link_armed(&state,now);
    *command=state.command;
    portEXIT_CRITICAL(&lock);
    if (!armed) command->throttle=0;
    return armed;
}
