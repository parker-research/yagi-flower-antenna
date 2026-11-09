#include "rf_switch.h"

#include "board.h"
#include "pico/stdlib.h"
#include "hardware/gpio.h"

// TPS22917 turn-on is ~100 us with C_T open; give the LNA margin to bias up
// before routing it to the output (make-before-break).
static const uint32_t LNA_SETTLE_US = 300;

// SKY13418 switching time is ~2 us, plus the RC filter on the control lines.
static const uint32_t SWITCH_SETTLE_US = 50;

static uint8_t s_selected_port = RF_SWITCH_PORT_NONE;

static void set_lna_power(uint8_t port, bool on) {
    gpio_put(BOARD_PIN_LNA_ENABLE_BASE + port, on);
}

void rf_switch_init(void) {
    for (uint8_t i = 0; i < BOARD_PORT_COUNT; i++) {
        const uint pin = BOARD_PIN_LNA_ENABLE_BASE + i;
        gpio_init(pin);
        gpio_set_dir(pin, GPIO_OUT);
        gpio_put(pin, 0);
    }

    const uint control_pins[] = { BOARD_PIN_SWITCH_V1, BOARD_PIN_SWITCH_V2, BOARD_PIN_SWITCH_V3 };
    for (size_t i = 0; i < 3; i++) {
        gpio_init(control_pins[i]);
        gpio_set_dir(control_pins[i], GPIO_OUT);
        gpio_put(control_pins[i], 0);
    }
}

void rf_switch_select(uint8_t port) {
    if (port >= BOARD_PORT_COUNT || port == s_selected_port) return;

    set_lna_power(port, true);
    sleep_us(LNA_SETTLE_US);

    gpio_put(BOARD_PIN_SWITCH_V1, (port >> 2) & 1);
    gpio_put(BOARD_PIN_SWITCH_V2, (port >> 1) & 1);
    gpio_put(BOARD_PIN_SWITCH_V3, (port >> 0) & 1);
    sleep_us(SWITCH_SETTLE_US);

    if (s_selected_port != RF_SWITCH_PORT_NONE) {
        set_lna_power(s_selected_port, false);
    }
    s_selected_port = port;
}

uint8_t rf_switch_get_port(void) {
    return s_selected_port;
}
