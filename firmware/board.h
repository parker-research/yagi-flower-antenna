/*
 * Board pin map for the Antenna-Array-Switch-PCB (RP2040-Zero).
 *
 * Values are the x in the schematic's GPx pin labels.
 */
#pragma once

#define BOARD_PORT_COUNT            8

#define BOARD_PIN_STATUS_LED        26

// Push buttons: active-high (external pull-downs, pressed = 3V3).
#define BOARD_PIN_BUTTON_1          15
#define BOARD_PIN_BUTTON_2          14

// SKY13418 control lines (3V3 GPIO -> divider -> 1V8 at the switch).
// Each line also drives an indicator LED (D202..D204).
// Datasheet Table 4: RF(n+1) selected when n = V1*4 + V2*2 + V3.
#define BOARD_PIN_SWITCH_V1         27   // SWITCH_CTRL1 -> SKY13418 pin 7 (V1, MSB)
#define BOARD_PIN_SWITCH_V2         28   // SWITCH_CTRL2 -> SKY13418 pin 6 (V2)
#define BOARD_PIN_SWITCH_V3         29   // SWITCH_CTRL3 -> SKY13418 pin 5 (V3, LSB)

// LNA_ENABLE_n powers the LNA on port n (via TPS22917, active-high).
// Port n is AntennaBranch n, wired to SKY13418 RF(n+1). LNA_ENABLE_n = GPn.
#define BOARD_PIN_LNA_ENABLE_BASE   0
