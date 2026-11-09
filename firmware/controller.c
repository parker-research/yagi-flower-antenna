#include "controller.h"

#include "antenna_config.h"
#include "log.h"
#include "rf_switch.h"
#include "antenna_select.h"

static bool s_manual_mode = false;
static float s_target_az_deg = 0.0f, s_target_el_deg = 90.0f;
static uint64_t s_target_received_ms = 0;
static bool s_has_target = false;

static void apply_automatic_selection(void) {
    const uint8_t old_port = rf_switch_get_port();
    const uint8_t new_port = antenna_select_choose(s_target_az_deg, s_target_el_deg, old_port);
    if (new_port != old_port) {
        rf_switch_select(new_port);
        LOG(LOG_INFO, "Auto: az=%.1f el=%.1f -> port %u (%s)",
            s_target_az_deg, s_target_el_deg, new_port, antenna_config_ports[new_port].name);
    }
}

void controller_init(void) {
    rf_switch_select((uint8_t)antenna_config_default_port);
}

void controller_set_target(float az_deg, float el_deg) {
    s_target_az_deg = az_deg;
    s_target_el_deg = el_deg;
    s_has_target = true;
    s_target_received_ms = time_us_64() / 1000u;
    if (!s_manual_mode) apply_automatic_selection();
}

void controller_get_target(float *az_deg, float *el_deg) {
    *az_deg = s_target_az_deg;
    *el_deg = s_target_el_deg;
}

uint64_t controller_target_age_ms(void) {
    if (!s_has_target) return UINT64_MAX;
    return time_us_64() / 1000u - s_target_received_ms;
}

void controller_set_manual(uint8_t port) {
    if (port >= BOARD_PORT_COUNT) return;
    s_manual_mode = true;
    rf_switch_select(port);
    LOG(LOG_ALWAYS, "Manual -> port %u (%s)", port, antenna_config_ports[port].name);
}

void controller_set_auto(void) {
    s_manual_mode = false;
    LOG(LOG_ALWAYS, "Auto mode");
    // Without a target yet, stay on the default port rather than guessing.
    if (s_has_target) apply_automatic_selection();
    else rf_switch_select((uint8_t)antenna_config_default_port);
}

bool controller_is_manual(void) {
    return s_manual_mode;
}

void controller_print_status(void) {
    const uint8_t port = rf_switch_get_port();
    LOG(LOG_ALWAYS, "Mode=%s target: az=%.1f el=%.1f (%s) port=%u (%s)",
        s_manual_mode ? "MANUAL" : "AUTO", s_target_az_deg, s_target_el_deg, s_has_target ? "set" : "none yet",
        port, antenna_config_ports[port].name);
    LOG(LOG_ALWAYS, "Port  Name      Type         Az     El     BW_H   BW_V   n(target)");
    for (uint8_t i = 0; i < BOARD_PORT_COUNT; i++) {
        const antenna_config_antenna_t *antenna = &antenna_config_ports[i];
        LOG(LOG_ALWAYS, "%u%c    %-9s %-12s %6.1f %6.1f %6.1f %6.1f %6.2f",
            i, (i == port) ? '*' : ' ', antenna->name, antenna_config_type_name(antenna->type),
            antenna->az_deg, antenna->el_deg, antenna->beamwidth_horizontal_deg, antenna->beamwidth_vertical_deg,
            (antenna->type == ANTENNA_CONFIG_TYPE_NONE) ? 0.0f : antenna_select_normalized_offset(i, s_target_az_deg, s_target_el_deg));
    }
    LOG(LOG_ALWAYS, "n: directional = offset / 3dB half-beamwidth (loss ~3dB*n^2, omni fallback if n>%.2f);"
        " omni = offset_deg / 90", ANTENNA_SELECT_OMNI_FALLBACK_NORMALIZED);
}
