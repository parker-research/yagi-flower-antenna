#include "antenna_config.h"
#include "antenna_select.h"
#include "test_check.h"

#define NO_PORT 0xFF

// Fixed test geometry, independent of the real (editable) antenna_config.c.
const antenna_config_antenna_t antenna_config_ports[BOARD_PORT_COUNT] = {
    //  name           type                              az     el    bw_h  bw_v
    { "Yagi N",   ANTENNA_CONFIG_TYPE_DIRECTIONAL,     0.0f, 35.0f, 70.0f, 60.0f },
    { "Yagi E",   ANTENNA_CONFIG_TYPE_DIRECTIONAL,    90.0f,  0.0f, 60.0f, 40.0f },
    { "Yagi S",   ANTENNA_CONFIG_TYPE_DIRECTIONAL,   180.0f, 35.0f, 70.0f, 60.0f },
    { "Unused",   ANTENNA_CONFIG_TYPE_NONE,            0.0f,  0.0f,  0.0f,  0.0f },
    { "QFH N",    ANTENNA_CONFIG_TYPE_OMNI,            0.0f, 60.0f,  0.0f,  0.0f },
    { "QFH S",    ANTENNA_CONFIG_TYPE_OMNI,          180.0f, 60.0f,  0.0f,  0.0f },
    { "Unused",   ANTENNA_CONFIG_TYPE_NONE,            0.0f,  0.0f,  0.0f,  0.0f },
    { "Unused",   ANTENNA_CONFIG_TYPE_NONE,            0.0f,  0.0f,  0.0f,  0.0f },
};
const unsigned antenna_config_default_port = 4;

enum { YAGI_N = 0, YAGI_E = 1, YAGI_S = 2, QFH_N = 4, QFH_S = 5 };

static void test_normalized_offset(void) {
    // On boresight.
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_E, 90.0f, 0.0f), 0.0f, 1e-4f);

    // Yagi E boresight is on the horizon, so pure az/el steps are along its principal axes.
    // Half-beamwidths are 30 deg horizontal, 20 deg vertical: both edges must give n = 1.
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_E, 120.0f, 0.0f), 1.0f, 1e-3f);
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_E, 60.0f, 0.0f), 1.0f, 1e-3f);
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_E, 90.0f, 20.0f), 1.0f, 1e-3f);
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_E, 90.0f, -20.0f), 1.0f, 1e-3f);
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_E, 90.0f, 40.0f), 2.0f, 1e-3f);

    // Directly behind.
    CHECK(antenna_select_normalized_offset(YAGI_E, 270.0f, 0.0f) > 5.0f, "behind should be far outside the beam");

    // Omni: angular distance from favoured direction / 90 deg.
    CHECK_NEAR(antenna_select_normalized_offset(QFH_N, 0.0f, 60.0f), 0.0f, 1e-4f);
    CHECK_NEAR(antenna_select_normalized_offset(QFH_N, 0.0f, 90.0f), 30.0f / 90.0f, 1e-3f);

    // Azimuth wraps; elevation past zenith is the same as flipping azimuth.
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_E, -270.0f, 0.0f), 0.0f, 1e-3f);
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_E, 450.0f, 0.0f), 0.0f, 1e-3f);
    CHECK_NEAR(antenna_select_normalized_offset(YAGI_N, 0.0f, 35.0f),
               antenna_select_normalized_offset(YAGI_N, 180.0f, 145.0f), 1e-3f);
}

static void test_choose_on_boresight(void) {
    CHECK(antenna_select_choose(0.0f, 35.0f, NO_PORT) == YAGI_N, "");
    CHECK(antenna_select_choose(90.0f, 0.0f, NO_PORT) == YAGI_E, "");
    CHECK(antenna_select_choose(180.0f, 35.0f, NO_PORT) == YAGI_S, "");
}

static void test_choose_omni_fallback(void) {
    // Near zenith, every yagi is well past ANTENNA_SELECT_OMNI_FALLBACK_NORMALIZED.
    CHECK(antenna_select_choose(10.0f, 88.0f, NO_PORT) == QFH_N, "near-zenith, north side");
    CHECK(antenna_select_choose(190.0f, 88.0f, NO_PORT) == QFH_S, "near-zenith, south side");

    // West has no yagi: directly opposite Yagi E, far from N/S beams.
    const uint8_t west = antenna_select_choose(270.0f, 0.0f, NO_PORT);
    CHECK(antenna_config_ports[west].type == ANTENNA_CONFIG_TYPE_OMNI, "got port %u", west);

    // Still reachable by Yagi E just inside the fallback limit.
    CHECK(antenna_select_choose(90.0f + 30.0f * 1.4f, 0.0f, NO_PORT) == YAGI_E, "edge of fallback limit");
}

static void test_choose_never_unused_port(void) {
    for (int az = -180; az <= 540; az += 5) {
        for (int el = -10; el <= 100; el += 5) {
            const uint8_t port = antenna_select_choose((float)az, (float)el, NO_PORT);
            CHECK(port < BOARD_PORT_COUNT && antenna_config_ports[port].type != ANTENNA_CONFIG_TYPE_NONE,
                  "az=%d el=%d -> port %u", az, el, port);
        }
    }
}

static void test_choose_hysteresis(void) {
    // Sweep between Yagi N and Yagi E and find a point where Yagi E is only
    // slightly better than Yagi N (within the hysteresis margin).
    bool found = false;
    for (float el = 0.0f; el <= 35.0f && !found; el += 1.0f) {
        for (float az = 0.0f; az <= 90.0f && !found; az += 0.25f) {
            const float offset_north = antenna_select_normalized_offset(YAGI_N, az, el);
            const float offset_east = antenna_select_normalized_offset(YAGI_E, az, el);
            const float advantage = offset_north - offset_east;
            if (advantage > 0.0f && advantage < ANTENNA_SELECT_HYSTERESIS_NORMALIZED * 0.5f
                    && offset_east <= ANTENNA_SELECT_OMNI_FALLBACK_NORMALIZED) {
                found = true;
                CHECK(antenna_select_choose(az, el, NO_PORT) == YAGI_E, "no current port: pick best (az=%.2f el=%.0f)", az, el);
                CHECK(antenna_select_choose(az, el, YAGI_N) == YAGI_N, "current within margin: keep (az=%.2f el=%.0f)", az, el);
                CHECK(antenna_select_choose(az, el, YAGI_E) == YAGI_E, "current is best: keep (az=%.2f el=%.0f)", az, el);
            }
        }
    }
    CHECK(found, "test geometry has no N/E boundary inside the fallback limit");
}

int main(void) {
    test_normalized_offset();
    test_choose_on_boresight();
    test_choose_omni_fallback();
    test_choose_never_unused_port();
    test_choose_hysteresis();
    return TEST_CHECK_RESULT();
}
