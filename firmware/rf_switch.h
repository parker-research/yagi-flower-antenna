/*
 * RF switch (SKY13418 SP8T) + per-port LNA power control.
 */
#pragma once

#include <stdint.h>

#define RF_SWITCH_PORT_NONE 0xFF

void rf_switch_init(void);

/// Route port (0..BOARD_PORT_COUNT-1) to the common output, powering only its LNA.
void rf_switch_select(uint8_t port);

/// Currently selected port, or RF_SWITCH_PORT_NONE before the first selection.
uint8_t rf_switch_get_port(void);
