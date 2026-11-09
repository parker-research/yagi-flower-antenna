/*
 * Antenna configuration: what is connected to each switch port, and where it points.
 * Edit the table in antenna_config.c to match the physical installation.
 *
 * Angles are in degrees. Azimuth: 0 = North, 90 = East. Elevation: 0 = horizon, 90 = zenith.
 */
#pragma once

#include "board.h"

typedef enum {
    ANTENNA_CONFIG_TYPE_NONE = 0,         // Nothing connected; never selected.
    ANTENNA_CONFIG_TYPE_DIRECTIONAL,      // E.g., yagi. Uses boresight + beamwidths.
    ANTENNA_CONFIG_TYPE_OMNI,             // E.g., QFH. Fallback only. Uses boresight as "favoured direction".
} antenna_config_type_t;

typedef struct {
    const char *name;
    antenna_config_type_t type;
    float az_deg;                 // Boresight (directional) or favoured direction (omni).
    float el_deg;
    float beamwidth_horizontal_deg;        // Full 3 dB beamwidth, horizontal plane (directional only).
    float beamwidth_vertical_deg;        // Full 3 dB beamwidth, vertical plane (directional only).
} antenna_config_antenna_t;

extern const antenna_config_antenna_t antenna_config_ports[BOARD_PORT_COUNT];

/// Port selected at boot, before any rotator command arrives.
extern const unsigned antenna_config_default_port;

const char *antenna_config_type_name(antenna_config_type_t type);
