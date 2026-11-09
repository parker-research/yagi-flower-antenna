/*
 * Antenna selection: pick the best port for a target azimuth/elevation.
 *
 * Algorithm:
 *   1. For each directional antenna, compute the "normalized offset" n of the
 *      target from boresight: angular offset divided by the half-beamwidth in
 *      that direction (elliptical beam). n = 1 is the 3 dB edge; estimated
 *      loss ~= 3 dB * n^2 (Gaussian beam approximation).
 *   2. Pick the directional antenna with the smallest n (the current antenna
 *      gets a small hysteresis bonus to avoid flapping on a boundary).
 *   3. If even the best directional has n > ANTENNA_SELECT_OMNI_FALLBACK_NORMALIZED, fall back
 *      to the omni whose favoured direction is angularly closest to the target.
 *      (If no omni is configured, the best directional is used anyway.)
 *
 * Hardware-independent, so it can be unit-tested on a host PC.
 */
#pragma once

#include <stdint.h>

// Beyond this normalized offset (~1.5x the 3 dB half-beamwidth, ~6.75 dB down)
// a directional antenna is considered unable to "reach" the target.
#define ANTENNA_SELECT_OMNI_FALLBACK_NORMALIZED  1.5f

// The currently selected antenna must be beaten by this much (in normalized
// offset units) before switching away from it.
#define ANTENNA_SELECT_HYSTERESIS_NORMALIZED     0.1f

/// Normalized offset of (az, el) from antenna `port`'s beam. Omni: offset angle in degrees / 90.
float antenna_select_normalized_offset(uint8_t port, float az_deg, float el_deg);

/// Best port for (az, el). `current_port` may be RF_SWITCH_PORT_NONE (0xFF).
uint8_t antenna_select_choose(float az_deg, float el_deg, uint8_t current_port);
