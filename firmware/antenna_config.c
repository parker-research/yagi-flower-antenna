#include "antenna_config.h"

// TODO: Placeholder layout. Update to match the as-built structure.
// Six yagis around the compass, tilted up, plus two QFH fallbacks.
const antenna_config_antenna_t antenna_config_ports[BOARD_PORT_COUNT] = {
    //  name           type                      az     el    bw_h  bw_v
    { "Yagi N",   ANTENNA_CONFIG_TYPE_DIRECTIONAL,     0.0f, 35.0f, 70.0f, 60.0f },
    { "Yagi NE",  ANTENNA_CONFIG_TYPE_DIRECTIONAL,    60.0f, 35.0f, 70.0f, 60.0f },
    { "Yagi SE",  ANTENNA_CONFIG_TYPE_DIRECTIONAL,   120.0f, 35.0f, 70.0f, 60.0f },
    { "Yagi S",   ANTENNA_CONFIG_TYPE_DIRECTIONAL,   180.0f, 35.0f, 70.0f, 60.0f },
    { "Yagi SW",  ANTENNA_CONFIG_TYPE_DIRECTIONAL,   240.0f, 35.0f, 70.0f, 60.0f },
    { "Yagi NW",  ANTENNA_CONFIG_TYPE_DIRECTIONAL,   300.0f, 35.0f, 70.0f, 60.0f },
    { "QFH N",    ANTENNA_CONFIG_TYPE_OMNI,            0.0f, 60.0f,  0.0f,  0.0f },
    { "QFH S",    ANTENNA_CONFIG_TYPE_OMNI,          180.0f, 60.0f,  0.0f,  0.0f },
};

const unsigned antenna_config_default_port = 6;

const char *antenna_config_type_name(antenna_config_type_t type) {
    switch (type) {
        case ANTENNA_CONFIG_TYPE_NONE:        return "none";
        case ANTENNA_CONFIG_TYPE_DIRECTIONAL: return "directional";
        case ANTENNA_CONFIG_TYPE_OMNI:        return "omni";
    }
    return "unknown";
}
