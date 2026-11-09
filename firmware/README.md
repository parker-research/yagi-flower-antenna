# Yagi Flower Antenna Switch Firmware

This firmware runs on the RP2040-Zero microcontroller board on the PCB.

## Building (Linux and macOS)

To build the firmware, follow these steps:

```bash
# Optionally, specify the Pico SDK path to your cloned Pico SDK (not recommended):
git clone https://github.com/raspberrypi/pico-sdk.git ~/pico-sdk
export PICO_SDK_PATH=~/pico-sdk

# If you skip the steps above (recommended to skip), cmake will automatically clone the Pico SDK.
cd firmware  # Navigate to the firmware directory of the repo.
mkdir build && cd build
cmake ..
make -j
```

## Flashing

1. Hold **BOOTSEL** on the RP2040-Zero while plugging it in. Or, hold **BOOTSEL** and press the reset button.
2. See that it mounts as a USB drive.
3. Drag `build/yagi_flower_switch.uf2` onto it.
4. It'll reboot and run.

## Monitor via USB Serial

Open the USB serial port at 115200 baud:

```bash
# Linux
screen /dev/ttyACM0 115200

# macOS
screen /dev/tty.usbmodem* 115200
```

Commands are newline-terminated (press Enter). Send `HELP` for the list. Highlights:

- `STATUS`: Mode, current target, and each port's config and fit to the target.
- `PORT <0-7>`: Force a port (manual mode). `AUTO`: Go back to automatic selection.
- `LOG <0-3>`: Log level. 0 (the default) prints nothing unsolicited, so it is safe to leave a rotator client attached. Levels 1 and up add periodic messages that can confuse hamlib.
- `BOOTSEL` / `REBOOT`.

Port numbers match `LNA_ENABLE_n` in the schematic. Port n connects to SKY13418 RF(n+1).

Button 1 forces the next port (manual mode). Button 2 returns to auto mode. The status LED gives a short blink in auto mode and stays mostly on in manual mode. The three LEDs on the switch control lines show the selected port in binary (V1 = MSB).

To kill `screen`, press `Ctrl+A`, then nothing will appear to happen, then `k`, then `y` when prompted.

## Rotator Control (hamlib)

The firmware speaks **Easycomm II** (hamlib rotator model `202`, `easycomm2`):

```bash
rotctl -m 202 -r /dev/ttyACM0 -s 115200   # interactive: P 123.4 45, p
rotctld -m 202 -r /dev/ttyACM0 -s 115200  # for GPredict, SatNOGS client, etc.
```

| Sent              | Meaning                    | Reply            |
|-------------------|----------------------------|------------------|
| `AZ123.4 EL45.0`  | Set target                 | (none)           |
| `AZ EL`           | Query position             | `AZ123.4 EL45.0` |
| `VE`              | Query version              | `VEyagi-flower-<git>` |
| `SA SE`, `ML`/`MR`/`MU`/`MD` | Stop/move (ignored) | (none)    |

The switch is solid-state, so it reports the last commanded target as its position, and the client sees it arrive immediately.

## Antenna Selection

Edit the table in `antenna_config.c` to describe the antenna on each port:

- `ANTENNA_CONFIG_TYPE_DIRECTIONAL`: Boresight az/el and the full 3 dB beamwidth in the horizontal and vertical planes.
- `ANTENNA_CONFIG_TYPE_OMNI`: A fallback, such as a QFH. Its az/el is only a "favoured direction", for example a north-tilted and a south-tilted QFH.
- `ANTENNA_CONFIG_TYPE_NONE`: Unused port.

For each new target (in auto mode), `antenna_select.c`:

1. Computes, for each directional antenna, the target's offset from boresight divided by the half-beamwidth in that direction, treating the beam as an ellipse. Call this `n`: `n = 1` is the 3 dB edge, and the loss is roughly `3 dB × n²`.
2. Picks the directional antenna with the smallest `n`. The current antenna gets a small hysteresis bonus (`ANTENNA_SELECT_HYSTERESIS_NORMALIZED`) so the selection does not flap on a boundary.
3. If the best `n` is still above `ANTENNA_SELECT_OMNI_FALLBACK_NORMALIZED` (1.5, about 6.75 dB down), it uses the omni whose favoured direction is closest to the target instead.

## Source Layout

Cross-file symbols are prefixed with their file name (`rf_switch_select()`, `antenna_config_ports[]`, `controller_set_target()`, ...).

| File               | Concern                                         |
|--------------------|-------------------------------------------------|
| `main.c`           | Init, main loop, buttons, LED, heartbeat        |
| `board.h`          | Pin map                                         |
| `antenna_config.*` | Antenna table (edit this)                       |
| `antenna_select.*` | Selection math (hardware-independent)           |
| `controller.*`     | Target and auto/manual mode, drives `rf_switch` |
| `rf_switch.*`      | SKY13418 control lines and LNA enables          |
| `rotator.*`        | Easycomm II protocol                            |
| `command_line.*`   | Serial line input and human commands            |
| `log.*`            | Logging                                         |

## Unit Tests

The hardware-independent modules (`antenna_select.c`, `rotator.c`) have host-side tests in `tests/`. They use the native compiler, not the Pico SDK, and run in CI:

```bash
cd firmware
cmake -S tests -B tests/build
cmake --build tests/build
ctest --test-dir tests/build --output-on-failure
```

The tests use their own fixed antenna table, so editing `antenna_config.c` will not break them.

## IDE Support

After building, enable IDE support by creating a symbolic link to `compile_commands.json` in the build directory:

```bash
cd firmware
ln -s build/compile_commands.json compile_commands.json
```
