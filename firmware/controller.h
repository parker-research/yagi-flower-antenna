/*
 * Controller: owns the pointing target and Auto/Manual mode, and drives the
 * RF switch from them.
 *
 * Auto:   port chosen by antenna_select_choose() whenever a new target arrives.
 * Manual: port forced by the user (serial PORT command or button 1).
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

void controller_init(void);

/// New pointing target (from the rotator protocol). Reselects the antenna in Auto mode.
void controller_set_target(float az_deg, float el_deg);
void controller_get_target(float *az_deg, float *el_deg);

/// Milliseconds since the last controller_set_target(), or UINT64_MAX if never.
uint64_t controller_target_age_ms(void);

void controller_set_manual(uint8_t port);
void controller_set_auto(void);
bool controller_is_manual(void);

/// Human-readable dump of the mode, target, and each port's config + fit.
void controller_print_status(void);
