#include "command_line.h"

#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#include "build_info.h"
#include "pico/stdlib.h"
#include "pico/bootrom.h"
#include "hardware/watchdog.h"

#include "board.h"
#include "controller.h"
#include "log.h"
#include "rotator.h"

#define LINE_MAX_LENGTH 80

static char s_line[LINE_MAX_LENGTH + 1];
static size_t s_line_length = 0;
static bool s_line_overflowed = false;

void command_line_print_help(void) {
    LOG(LOG_ALWAYS, "================= HELP ========================");
    LOG(LOG_ALWAYS, "Commands are newline-terminated and case-insensitive.");
    LOG(LOG_ALWAYS, "Rotator (Easycomm II, hamlib model 202):");
    LOG(LOG_ALWAYS, "  AZ<deg> EL<deg>   Set target, e.g. 'AZ123.4 EL45.0'");
    LOG(LOG_ALWAYS, "  AZ EL             Query target (reply 'AZ123.4 EL45.0')");
    LOG(LOG_ALWAYS, "  VE                Query version");
    LOG(LOG_ALWAYS, "Human:");
    LOG(LOG_ALWAYS, "  STATUS            Show mode, target, antenna config + fit");
    LOG(LOG_ALWAYS, "  PORT <0-%d>        Force antenna port (manual mode)", BOARD_PORT_COUNT - 1);
    LOG(LOG_ALWAYS, "  AUTO              Select antenna from rotator target (default)");
    LOG(LOG_ALWAYS, "  LOG <0-3>         Log level: 0 = quiet/rotator-safe (default),");
    LOG(LOG_ALWAYS, "                    1 = info, 2 = debug, 3 = trace");
    LOG(LOG_ALWAYS, "  BOOTSEL           Reboot into flash bootloader mode");
    LOG(LOG_ALWAYS, "  REBOOT            Reboot");
    LOG(LOG_ALWAYS, "  HELP              Print this help message");
    LOG(LOG_ALWAYS, "Buttons: 1 = manual, next port; 2 = auto.");
    LOG(LOG_ALWAYS, "===============================================");
    LOG(LOG_ALWAYS, "Build: " BUILD_TIMESTAMP " git=" GIT_COMMIT);
    LOG(LOG_ALWAYS, "===============================================");
}

/// Parse a decimal integer argument in [0, max]. Returns -1 if absent/invalid.
static int parse_integer_argument(const char *argument, int max) {
    if (!argument) return -1;
    char *end_of_number;
    const long value = strtol(argument, &end_of_number, 10);
    if (end_of_number == argument || *end_of_number != '\0' || value < 0 || value > max) return -1;
    return (int)value;
}

/// Handle human commands. Returns false if the line isn't one (so it goes to the rotator parser).
static bool handle_human_command(char *line) {
    char line_copy[LINE_MAX_LENGTH + 1];
    strcpy(line_copy, line);  // strtok is destructive; keep `line` intact for rotator.
    const char *command = strtok(line_copy, " \t");
    const char *argument = strtok(NULL, " \t");
    if (!command) return true;

    if (strcmp(command, "HELP") == 0 || strcmp(command, "H") == 0 || strcmp(command, "?") == 0) {
        command_line_print_help();
    } else if (strcmp(command, "STATUS") == 0) {
        controller_print_status();
    } else if (strcmp(command, "LOG") == 0) {
        const int level = parse_integer_argument(argument, LOG_TRACE);
        if (level < 0) {
            LOG(LOG_ALWAYS, "Usage: LOG <0-3> (currently %d)", log_level);
        } else {
            log_level = (log_level_t)level;
            LOG(LOG_ALWAYS, "Log level set to %d", level);
        }
    } else if (strcmp(command, "PORT") == 0) {
        const int port = parse_integer_argument(argument, BOARD_PORT_COUNT - 1);
        if (port < 0) LOG(LOG_ALWAYS, "Usage: PORT <0-%d>", BOARD_PORT_COUNT - 1);
        else controller_set_manual((uint8_t)port);
    } else if (strcmp(command, "AUTO") == 0) {
        controller_set_auto();
    } else if (strcmp(command, "BOOTSEL") == 0) {
        LOG(LOG_ALWAYS, "Rebooting into flash bootloader mode...");
        sleep_ms(1000);
        reset_usb_boot(0, 0);
    } else if (strcmp(command, "REBOOT") == 0) {
        LOG(LOG_ALWAYS, "Rebooting...");
        sleep_ms(1000);
        watchdog_reboot(0, 0, 0);  // Triggers an immediate watchdog reset -> firmware restart.
    } else {
        return false;
    }
    return true;
}

static void handle_line(char *line) {
    for (char *p = line; *p; p++) *p = (char)toupper((unsigned char)*p);
    LOG(LOG_TRACE, "RX line: '%s'", line);

    if (handle_human_command(line)) return;
    if (!rotator_handle_line(line)) {
        LOG(LOG_ALWAYS, "Unknown command. Send HELP for help.");
    }
}

void command_line_poll(void) {
    int character;
    while ((character = getchar_timeout_us(0)) != PICO_ERROR_TIMEOUT) {
        if (character == '\r' || character == '\n') {
            if (s_line_overflowed) {
                LOG(LOG_ALWAYS, "Line too long, ignored.");
            } else if (s_line_length > 0) {
                s_line[s_line_length] = '\0';
                handle_line(s_line);
            }
            s_line_length = 0;
            s_line_overflowed = false;
        } else if (s_line_length < LINE_MAX_LENGTH) {
            s_line[s_line_length++] = (char)character;
        } else {
            s_line_overflowed = true;
        }
    }
}
