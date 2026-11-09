#include "antenna_select.h"

#include <math.h>
#include <stdbool.h>
#include "antenna_config.h"

#define NO_PORT 0xFF

static float degrees_to_radians(float degrees) { return degrees * (float)M_PI / 180.0f; }
static float radians_to_degrees(float radians) { return radians * 180.0f / (float)M_PI; }

typedef struct { float north, east, up; } vector3_t;

static float dot_product(vector3_t a, vector3_t b) {
    return a.north * b.north + a.east * b.east + a.up * b.up;
}

static vector3_t unit_vector_from_az_el(float az_radians, float el_radians) {
    return (vector3_t){
        .north = cosf(el_radians) * cosf(az_radians),
        .east  = cosf(el_radians) * sinf(az_radians),
        .up    = sinf(el_radians),
    };
}

static float angle_between_radians(vector3_t a, vector3_t b) {
    const float cosine = fmaxf(-1.0f, fminf(1.0f, dot_product(a, b)));
    return acosf(cosine);
}

float antenna_select_normalized_offset(uint8_t port, float az_deg, float el_deg) {
    const antenna_config_antenna_t *antenna = &antenna_config_ports[port];
    const float boresight_az = degrees_to_radians(antenna->az_deg);
    const float boresight_el = degrees_to_radians(antenna->el_deg);

    const vector3_t target = unit_vector_from_az_el(degrees_to_radians(az_deg), degrees_to_radians(el_deg));
    const vector3_t boresight = unit_vector_from_az_el(boresight_az, boresight_el);
    const float offset_radians = angle_between_radians(target, boresight);

    if (antenna->type != ANTENNA_CONFIG_TYPE_DIRECTIONAL) {
        return radians_to_degrees(offset_radians) / 90.0f;
    }

    // Antenna-frame axes perpendicular to boresight: "right" (horizontal) and "up" (vertical).
    const vector3_t antenna_right = { -sinf(boresight_az), cosf(boresight_az), 0.0f };
    const vector3_t antenna_up = {
        -sinf(boresight_el) * cosf(boresight_az),
        -sinf(boresight_el) * sinf(boresight_az),
        cosf(boresight_el),
    };
    // Direction of the offset around boresight: 0 = right, pi/2 = up.
    const float offset_direction = atan2f(dot_product(target, antenna_up), dot_product(target, antenna_right));

    // Half-beamwidth of the elliptical beam in that direction (polar radius of an ellipse).
    const float half_beamwidth_horizontal = degrees_to_radians(antenna->beamwidth_horizontal_deg) * 0.5f;
    const float half_beamwidth_vertical = degrees_to_radians(antenna->beamwidth_vertical_deg) * 0.5f;
    const float horizontal_term = half_beamwidth_vertical * cosf(offset_direction);
    const float vertical_term = half_beamwidth_horizontal * sinf(offset_direction);
    const float half_beamwidth = half_beamwidth_horizontal * half_beamwidth_vertical
        / sqrtf(horizontal_term * horizontal_term + vertical_term * vertical_term);

    return (half_beamwidth > 0.0f) ? (offset_radians / half_beamwidth) : INFINITY;
}

uint8_t antenna_select_choose(float az_deg, float el_deg, uint8_t current_port) {
    uint8_t best_directional_port = NO_PORT, best_omni_port = NO_PORT;
    float best_directional_offset = INFINITY, best_omni_offset = INFINITY;

    for (uint8_t port = 0; port < BOARD_PORT_COUNT; port++) {
        const antenna_config_type_t type = antenna_config_ports[port].type;
        if (type == ANTENNA_CONFIG_TYPE_NONE) continue;

        float offset = antenna_select_normalized_offset(port, az_deg, el_deg);
        if (port == current_port) offset -= ANTENNA_SELECT_HYSTERESIS_NORMALIZED;

        if (type == ANTENNA_CONFIG_TYPE_DIRECTIONAL && offset < best_directional_offset) {
            best_directional_offset = offset;
            best_directional_port = port;
        } else if (type == ANTENNA_CONFIG_TYPE_OMNI && offset < best_omni_offset) {
            best_omni_offset = offset;
            best_omni_port = port;
        }
    }

    const bool directional_can_reach = best_directional_offset <= ANTENNA_SELECT_OMNI_FALLBACK_NORMALIZED;
    if (best_directional_port != NO_PORT && (directional_can_reach || best_omni_port == NO_PORT)) {
        return best_directional_port;
    }
    if (best_omni_port != NO_PORT) return best_omni_port;
    return (uint8_t)antenna_config_default_port;
}
