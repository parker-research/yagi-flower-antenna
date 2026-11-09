/*
 * Logging over USB-CDC with runtime-selectable verbosity.
 *
 * NOTE: The serial port is shared with the rotator protocol (hamlib). At
 * LOG_ALWAYS (the default), the firmware prints nothing unsolicited, so it is
 * safe to leave a rotator client attached. Higher levels add periodic/async
 * messages, which may confuse a rotator client.
 */
#pragma once

#include <stdio.h>
#include "pico/time.h"

typedef enum {
    LOG_ALWAYS = 0,   // Replies to human commands only. Nothing unsolicited.
    LOG_INFO   = 1,   // + antenna selection changes, heartbeat
    LOG_DEBUG  = 2,   // + every rotator command received
    LOG_TRACE  = 3,   // + every serial line received
} log_level_t;

extern volatile log_level_t log_level;

const char *log_level_name(log_level_t level);

#define LOG(level, fmt, ...) \
    do { \
        if (log_level >= (level)) { \
            printf("[%llu] [%s] " fmt "\n", (unsigned long long)(time_us_64() / 1000u), log_level_name(level), ##__VA_ARGS__); \
        } \
    } while (0)
