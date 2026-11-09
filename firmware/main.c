/*
 * Yagi Flower Antenna Switch Firmware
 * Target: RP2040-Zero on the Antenna-Array-Switch-PCB (SKY13418 SP8T + 8x LNA).
 *
 * Responsibilities:
 *   - Pretend to be an antenna rotator (Easycomm II, hamlib model 202) over USB-CDC.
 *   - Select the antenna port that best covers the commanded az/el (see antenna_select.h),
 *     falling back to an omni antenna when no directional antenna can reach it.
 *   - Power only the selected port's LNA.
 *   - Provide human commands + logging on the same serial port (see command_line.c).
 *
 * Files (cross-file symbols are prefixed by their file name):
 *   board.h           Pin map.
 *   log.*             Logging.
 *   antenna_config.*  Antenna table (edit me).
 *   antenna_select.*  Antenna selection math.
 *   rf_switch.*       RF switch + LNA GPIO.
 *   controller.*      Target + Auto/Manual mode.
 *   rotator.*         Easycomm II protocol.
 *   command_line.*    Serial line handling.
 *
 * Heartbeat (LOG_INFO, ~2.5 s):
 *   Heartbeat: log_level=<n> mode=<AUTO|MANUAL> port=<n> az=<deg> el=<deg> last_cmd_ago_s=<sec.ms|never>
 */

#include <stdint.h>
#include <stdbool.h>

#include "build_info.h"

#include "pico/stdlib.h"
#include "pico/stdio_usb.h"
#include "hardware/gpio.h"
#include "hardware/watchdog.h"

#include "antenna_config.h"
#include "board.h"
#include "command_line.h"
#include "controller.h"
#include "log.h"
#include "rf_switch.h"

// ---------------------------------------------------------------------------
// Tunables
// ---------------------------------------------------------------------------
static const uint32_t LOOP_INTERVAL_US = 500;

// Status LED: short led_pulse in Auto, inverted (mostly on) in Manual.
static const uint32_t LED_PERIOD_MS = 1000;
static const uint32_t LED_ON_TIME_MS = 100;

static const uint32_t BUTTON_DEBOUNCE_MS = 30;

static const uint32_t INFO_HEARTBEAT_MESSAGE_INTERVAL_MS = 2500;

// ---------------------------------------------------------------------------
// Buttons
// ---------------------------------------------------------------------------
typedef struct {
    uint pin;
    bool debounced_pressed;            // Debounced state (true = pressed).
    bool last_raw_pressed;
    uint64_t last_change_ms;
} button_t;

static button_t s_buttons[2] = {
    { .pin = BOARD_PIN_BUTTON_1 },
    { .pin = BOARD_PIN_BUTTON_2 },
};

/// Returns true once per debounced press.
static bool button_pressed(button_t *button, uint64_t now) {
    const bool raw_pressed = gpio_get(button->pin);
    if (raw_pressed != button->last_raw_pressed) {
        button->last_raw_pressed = raw_pressed;
        button->last_change_ms = now;
    }
    if (raw_pressed != button->debounced_pressed && (now - button->last_change_ms) >= BUTTON_DEBOUNCE_MS) {
        button->debounced_pressed = raw_pressed;
        return raw_pressed;
    }
    return false;
}

static void poll_buttons(uint64_t now) {
    if (button_pressed(&s_buttons[0], now)) {
        // Next connected port after the current one.
        uint8_t port = rf_switch_get_port();
        for (int i = 0; i < BOARD_PORT_COUNT; i++) {
            port = (port + 1) % BOARD_PORT_COUNT;
            if (antenna_config_ports[port].type != ANTENNA_CONFIG_TYPE_NONE) break;
        }
        controller_set_manual(port);
    }
    if (button_pressed(&s_buttons[1], now)) {
        controller_set_auto();
    }
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------
static void setup_gpio(void) {
    gpio_init(BOARD_PIN_STATUS_LED);
    gpio_set_dir(BOARD_PIN_STATUS_LED, GPIO_OUT);
    gpio_put(BOARD_PIN_STATUS_LED, 0);

    for (size_t i = 0; i < 2; i++) {
        gpio_init(s_buttons[i].pin);
        gpio_set_dir(s_buttons[i].pin, GPIO_IN);
        gpio_pull_down(s_buttons[i].pin);
    }
}

// ---------------------------------------------------------------------------
// Main loop
// ---------------------------------------------------------------------------
int main(void) {
    stdio_init_all();
    setup_gpio();
    rf_switch_init();
    controller_init();

    uint64_t last_info_heartbeat_time = 0;
    bool last_usb_connected = false;
    uint64_t last_usb_connected_check_time = 0;

    // [WATCHDOG] Detect if we woke from a watchdog reset and log it.
    const bool did_watchdog_cause_reboot = watchdog_caused_reboot();

    // [WATCHDOG] Enable. Timeout is 5000 ms.
    // pause_on_debug=true freezes the counter while a debugger is halted.
    watchdog_enable(5000, true);

    while (true) {
        command_line_poll();

        watchdog_update();  // [WATCHDOG] Feed dog. Must run < every 5000 ms.

        const uint64_t now = time_us_64() / 1000u;

        poll_buttons(now);

        // Banner on new USB CDC connection. Only at LOG_INFO+, because a rotator
        // client (hamlib) opening the port must not receive unsolicited text.
        if (now - last_usb_connected_check_time > 750) {
            const bool usb_connected = stdio_usb_connected();
            if (usb_connected && !last_usb_connected && log_level >= LOG_INFO) {
                sleep_ms(100); // Brief settling time for the CDC link to stabilize.
                LOG(LOG_INFO, "===============================================");
                LOG(LOG_INFO, "Yagi Flower Antenna Switch connected to USB...");
                LOG(LOG_INFO, "Build: " BUILD_TIMESTAMP " git=" GIT_COMMIT);
                if (did_watchdog_cause_reboot) {
                    LOG(LOG_INFO, "*** LAST REBOOT: WATCHDOG RESET DETECTED ***");
                }
                LOG(LOG_INFO, "===============================================");
                command_line_print_help();
            }
            last_usb_connected = usb_connected;
            last_usb_connected_check_time = now;
        }

        // Info-level heartbeat.
        if (log_level >= LOG_INFO && (now - last_info_heartbeat_time >= INFO_HEARTBEAT_MESSAGE_INTERVAL_MS)) {
            float az, el;
            controller_get_target(&az, &el);
            const uint64_t age_ms = controller_target_age_ms();
            char age_text[24];
            if (age_ms == UINT64_MAX) {
                snprintf(age_text, sizeof(age_text), "never");
            } else {
                snprintf(age_text, sizeof(age_text), "%llu.%03llu",
                         (unsigned long long)(age_ms / 1000u), (unsigned long long)(age_ms % 1000u));
            }
            LOG(
                LOG_INFO,
                "Heartbeat: log_level=%d mode=%s port=%u az=%.1f el=%.1f last_cmd_ago_s=%s%s",
                log_level, controller_is_manual() ? "MANUAL" : "AUTO", rf_switch_get_port(), az, el, age_text,
                did_watchdog_cause_reboot ? " (last reboot: WATCHDOG)" : ""
            );
            last_info_heartbeat_time = now;
        }

        const bool led_pulse = (now % LED_PERIOD_MS) < LED_ON_TIME_MS;
        gpio_put(BOARD_PIN_STATUS_LED, controller_is_manual() ? !led_pulse : led_pulse);

        sleep_us(LOOP_INTERVAL_US);
    }
}
