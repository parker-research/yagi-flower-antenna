#include "rotator.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "build_info.h"
#include "controller.h"
#include "log.h"

static bool parse_float(const char *text, float *out) {
    char *end_of_number;
    const float value = strtof(text, &end_of_number);
    if (end_of_number == text || *end_of_number != '\0') return false;
    *out = value;
    return true;
}

static bool is_ignored_token(const char *token) {
    static const char *const ignored[] = { "SA", "SE", "ML", "MR", "MU", "MD", "XXX" };
    for (size_t i = 0; i < sizeof(ignored) / sizeof(ignored[0]); i++) {
        if (strcmp(token, ignored[i]) == 0) return true;
    }
    // Easycomm I uplink/downlink frequency fields (e.g. "UP000", "DN000").
    return strncmp(token, "UP", 2) == 0 || strncmp(token, "DN", 2) == 0;
}

bool rotator_handle_line(char *line) {
    float az, el;
    controller_get_target(&az, &el);
    bool az_set = false, el_set = false, recognised = false;

    char reply[96];
    size_t reply_len = 0;
    reply[0] = '\0';
    #define APPEND_REPLY(fmt, ...) \
        reply_len += snprintf(reply + reply_len, sizeof(reply) - reply_len, "%s" fmt, reply_len ? " " : "", ##__VA_ARGS__)

    for (char *token = strtok(line, " \t"); token; token = strtok(NULL, " \t")) {
        if (strcmp(token, "AZ") == 0) {
            APPEND_REPLY("AZ%.1f", az);
        } else if (strcmp(token, "EL") == 0) {
            APPEND_REPLY("EL%.1f", el);
        } else if (strncmp(token, "AZ", 2) == 0 && parse_float(token + 2, &az)) {
            az_set = true;
        } else if (strncmp(token, "EL", 2) == 0 && parse_float(token + 2, &el)) {
            el_set = true;
        } else if (strcmp(token, "VE") == 0) {
            APPEND_REPLY("VEyagi-flower-%s", GIT_COMMIT);
        } else if (is_ignored_token(token)) {
            // Nothing to do for a solid-state "rotator".
        } else {
            LOG(LOG_DEBUG, "Rotator: unknown token '%s'", token);
            continue;
        }
        recognised = true;
        if (reply_len >= sizeof(reply)) reply_len = sizeof(reply) - 1;
    }
    #undef APPEND_REPLY

    if (az_set || el_set) {
        LOG(LOG_DEBUG, "Rotator: set az=%.1f el=%.1f", az, el);
        controller_set_target(az, el);
    }
    if (reply_len) {
        printf("%s\n", reply);
    }
    return recognised;
}
