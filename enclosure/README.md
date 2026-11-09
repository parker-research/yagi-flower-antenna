# Enclosure

3D-printable enclosure for the Antenna-Array-Switch-PCB, written in [build123d](https://github.com/gumyr/build123d).

## Build

```bash
cd enclosure
uv sync
uv run python cad/enclosure.py   # Writes STL + STEP files to build/
```

## Parts

| File                     | Print | Notes                                                                    |
|--------------------------|-------|--------------------------------------------------------------------------|
| `enclosure_tray.stl`     | 1     | Floor down. Press an M3 nut into the hex pocket under each standoff.     |
| `enclosure_lid.stl`      | 1     | Top plate down. The raised pocket's ceiling is a ~33 mm bridge.          |
| `enclosure_spacers.stl`  | 1 set | Five 3.8 mm tubes that sit between the PCB and the lid.                  |
| `enclosure_assembly.*`   | -     | Fit check only: tray, a rough PCB, spacers, and lid in place, each named and coloured. |

Stack-up, bottom to top: tray, PCB, spacers, lid. Five M3×12 screws go down through the lid, spacers, PCB, and standoffs into M3 nuts sunk into the bottom of the tray (hex pockets, 3 mm deep, so the nuts sit flush or recessed). The build checks that `screw_length` reaches far enough into the nut and doesn't poke out the bottom.

## Configuration

Edit the `Spec` defaults in `cad/enclosure.py`.

- **`populated_ports`**: The SMA jacks that are fitted, by PCB silkscreen name: `IN0`..`IN7`, `OUT0`, `SW_OUT`, `TEST_A`, `TEST_B`. The default is `IN0`..`IN4`, `OUT0`, `SW_OUT`. The lid gets a hole for each one, with an engraved label directly south of it and a line to the port's LED (inputs only). Every other port position stays solid.
- **`label_closed_ports`**: Engrave closed input ports' names beside their LED instead (on by default). Closed ports without an LED (`OUT0`, `SW_OUT`, `TEST_*`) stay unlabelled.
- **`sma_body_height`**, **`sma_body_size`**: Estimates for the Amphenol 901-144's square body. **Measure one before printing.** If the body reaches the lid, it is pocketed from underneath.
- **`usb_receptacle_bottom_height`**, **`usb_receptacle_height_tolerance`**: Measured height of the RP2040-Zero's USB-C receptacle bottom above the main PCB (11.73 ± 0.3 mm), which sets the USB-C cutout height. The 7.5 mm cutout fits a 6.5 mm plug overmold (`usb_plug_overmold_height`) anywhere in that tolerance; the build fails if it wouldn't.
- **`tall_region_height`**: Height the RF can and RP2040-Zero need above the PCB (20 mm).
- **`clearance_below_pcb`**, **`clearance_above_pcb`**: Air gaps under and over the PCB (3.8 mm each).

## Features

- Raised pocket, with rounded outside corners and top edges, over the RF can and the socketed RP2040-Zero, with a USB-C cutout sized for the plug overmold.
- 1.2 mm windows over all 12 LEDs, for filling with clear epoxy: status, the 3 switch-control LEDs, and the 8 LNA-power LEDs.
- The push buttons are enclosed and not accessible.

PCB positions come from `cad/pcb_layout.py`, which was extracted from the KiCad board (Rev 1). Update it if the PCB layout changes.
