/*
 * Rotator protocol: Easycomm II (hamlib rotator model 202, "easycomm2").
 *
 * Supported tokens (space-separated, several per line, newline-terminated):
 *   AZxxx.x  Set target azimuth (degrees).
 *   ELxx.x   Set target elevation (degrees).
 *   AZ       Query azimuth.   Reply: "AZxxx.x"
 *   EL       Query elevation. Reply: "ELxx.x"
 *   VE       Query version.   Reply: "VE<version>"
 *   SA, SE, ML, MR, MU, MD, UPxxx, DNxxx, XXX  Accepted and ignored.
 *
 * Replies for one line are joined with spaces, e.g. "AZ EL" -> "AZ123.0 EL45.0".
 * Being solid-state, the reported position is always the last commanded target.
 */
#pragma once

#include <stdbool.h>

/// Handle an (upper-cased) Easycomm line. Returns false if no token was recognised.
bool rotator_handle_line(char *line);
