/*
 * USB serial command line. Reads newline-terminated lines, handles the
 * human commands (HELP, LOG, STATUS, PORT, AUTO, BOOTSEL, REBOOT), and passes
 * everything else to the rotator protocol (rotator.c).
 */
#pragma once

/// Non-blocking: consume any pending serial input, executing complete lines.
void command_line_poll(void);

void command_line_print_help(void);
