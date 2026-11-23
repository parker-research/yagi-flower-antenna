#include "antenna_config.h"

// As-built: two yagis connected (IN2, IN6); all other ports unused.
const antenna_config_antenna_t antenna_config_ports[BOARD_PORT_COUNT] = {
    //  name       type                              az     el    bw_h  bw_v
    { "Unused",  ANTENNA_CONFIG_TYPE_NONE,           0.0f,  0.0f,  0.0f,  0.0f }, // Port 0
    { "Unused",  ANTENNA_CONFIG_TYPE_NONE,           0.0f,  0.0f,  0.0f,  0.0f }, // Port 1
    { "Yagi ESE", ANTENNA_CONFIG_TYPE_DIRECTIONAL, 120.0f, 40.0f, 70.0f, 60.0f }, // Port 2
    { "Unused",  ANTENNA_CONFIG_TYPE_NONE,           0.0f,  0.0f,  0.0f,  0.0f }, // Port 3
    { "Unused",  ANTENNA_CONFIG_TYPE_NONE,           0.0f,  0.0f,  0.0f,  0.0f }, // Port 4
    { "Unused",  ANTENNA_CONFIG_TYPE_NONE,           0.0f,  0.0f,  0.0f,  0.0f }, // Port 5
    { "Yagi S",  ANTENNA_CONFIG_TYPE_DIRECTIONAL,  180.0f, 40.0f, 70.0f, 60.0f }, // Port 6
    { "Unused",  ANTENNA_CONFIG_TYPE_NONE,           0.0f,  0.0f,  0.0f,  0.0f }, // Port 7
};

// Default/init port on startup, until commanded with Az/El directive.
const unsigned antenna_config_default_port = 6;

const char *antenna_config_type_name(antenna_config_type_t type) {
    switch (type) {
        case ANTENNA_CONFIG_TYPE_NONE:        return "none";
        case ANTENNA_CONFIG_TYPE_DIRECTIONAL: return "directional";
        case ANTENNA_CONFIG_TYPE_OMNI:        return "omni";
    }
    return "unknown";
}
