# Mechanical

CAD models for the yagi flower, written in [build123d](https://github.com/gumyr/build123d). Each model is a script in `cad/`:

| Script                         | What                                                           |
|--------------------------------|----------------------------------------------------------------|
| `cad/antenna_frame.py`         | [Antenna frame](#antenna-frame): hub and 5 arms that hold all 6 yagis, on a plywood base. |
| `cad/enclosure_3d_printed.py`  | [Enclosure (3D-printed)](#enclosure-3d-printed) for the Antenna-Array-Switch-PCB. |

## Build

```bash
cd mechanical
uv sync
uv run python cad/antenna_frame.py          # Writes STL + STEP files to build/
uv run python cad/enclosure_3d_printed.py   # Likewise
```

## Antenna Frame

A 3D-printed frame, in 11 parts, that stands on a plywood base and holds six yagis with 15 × 15 mm square booms. Five yagis are spread evenly around it, pointing outwards at 40° above the horizon. The sixth stands in the middle, pointing straight up. All elements are horizontal.

| File                            | Print | Notes                                                              |
|---------------------------------|-------|--------------------------------------------------------------------|
| `antenna_frame_hub.stl`         | 1     | Base down. About 134 × 141 × 108 mm.                               |
| `antenna_frame_arm_extension_1.stl` | 5 | Base down. About 134 × 46 × 35 mm. Inner piece of each arm, bolts to the hub. |
| `antenna_frame_arm_ramp.stl`    | 5     | Base down. About 134 × 46 × 89 mm. Outer piece of each arm, carries a yagi. The ramp's underside overhangs 50° from vertical. |
| `antenna_frame_assembly.*`      | -     | Fit check only: hub, arms, booms, reflectors, and driven elements in place. |

### Shape

- **Hub**: A hollow pentagonal block, open underneath, with ribs and screw towers inside. A square socket on top holds the centre yagi.
- **Arms**: Each one bolts to a flat side of the hub and runs outwards along the base, then rises as a ramp at 40°. The outer yagi's boom lies on top of the ramp. Hollow and open underneath. Each arm is split into equal pieces, as few as fit the printer (two with the defaults), bolted end to end: extension pieces, then the ramp piece.

Every part stands directly on the plywood, so loads go straight down into it. The whole frame is about 660 mm across.

The arm length is set so the outer yagis' driven elements sit on a circle of `driven_element_radius_wavelengths` (0.70) wavelengths at `design_frequency_mhz` (435 MHz): a radius of 482 mm. The frame is then about 660 mm across, and every element is at least 125 mm from every other yagi's elements. The build fails if any element comes closer than `min_element_clearance` (25 mm), or if a part won't fit the printer (`printer_bed_size`, `printer_max_height`).

### Mounting

Everything uses M5 bolts with M5 nuts pressed into hex pockets.

- **Arm joints** (hub to arm, and between arm pieces): Two horizontal bolts per joint, put in from inside the inner part (from underneath), through both end walls, into nuts on the inside of the outer part (M5×25). Bolt the arms together and onto the hub before fixing the frame down.
- **Outer yagis**: Two bolts, 46 mm apart, go down through the boom and the ramp into nuts in pockets on the ramp's underside (press them in from below). The tails run down into the arm, and out through its end wall if they reach it. The hub and arms are high enough to leave `min_bolt_tail_length` (50 mm) under the nut before the lower bolts' tails reach the base, and about 90 mm for the upper ones.
- **Centre yagi**: The boom stands in the socket. Two horizontal bolts go through the socket and the boom, into nuts on the far side of the socket, aimed between the arms, so they can be any length.

Wood screws (e.g. #8 or M4) fix every part to the plywood base: five through the hub (between the arms), and five through each arm (two along the extension piece, one on the ramp piece's flat part, and two either side of the boom on the ramp). Each one drops down a 10 mm bore in a solid tower and seats 6 mm above the base. The build checks that no boom blocks a bore.

### Configuration

Edit the `Spec` defaults in `cad/antenna_frame.py`.

- **`outer_antenna_count`**, **`outer_antenna_elevation_deg`**: Five outer yagis, at 40°.
- **`boom_width`**, **`bolt_spacing`**: 15 mm booms, 46 mm between bolts.
- **`boom_rear_overhang`**: How far an outer boom extends behind its lower bolt, down the ramp (15 mm).
- **`reflector_length`**, **`reflector_offset`**, **`driven_element_length`**, **`driven_element_spacing`**: Yagi elements. The reflector (340 mm) is 75 mm forward of the front bolt, and the driven element (gamma match, so one continuous rod) is 155 mm further on. The driven element's length is a placeholder.
- **`driven_element_radius_wavelengths`**, **`design_frequency_mhz`**: Set how far out the arms reach (see [Shape](#shape)).
- **`min_element_clearance`**: The build fails if elements of different yagis come closer than this (25 mm).
- **`printer_bed_size`**, **`printer_max_height`**: 210 mm.
- **`hub_apothem`**: Hub size (60 mm, centre to each flat side).
- **`min_bolt_tail_length`**: Sets the height of the hub and the arms' flat part.

The build fails if a boom would hit the frame or a screw bore, and warns if an element would hit the frame or another yagi's boom.

## Enclosure (3D-printed)

3D-printable enclosure for the Antenna-Array-Switch-PCB. A sheet metal variant may come later.

### Parts

| File                     | Print | Notes                                                                    |
|--------------------------|-------|--------------------------------------------------------------------------|
| `enclosure_3d_printed_tray.stl`     | 1     | Floor down. Press an M3 nut into the hex pocket under each standoff.     |
| `enclosure_3d_printed_lid.stl`      | 1     | Top plate down. The raised pocket's ceiling is a ~33 mm bridge.          |
| `enclosure_3d_printed_spacers.stl`  | 1 set | Five 3.8 mm tubes that sit between the PCB and the lid.                  |
| `enclosure_3d_printed_assembly.*`   | -     | Fit check only: tray, a rough PCB, spacers, and lid in place, each named and coloured. |

Stack-up, bottom to top: tray, PCB, spacers, lid. Five M3×12 screws go down through the lid, spacers, PCB, and standoffs into M3 nuts sunk into the bottom of the tray (hex pockets, 3 mm deep, so the nuts sit flush or recessed). The build checks that `screw_length` reaches far enough into the nut and doesn't poke out the bottom.

### Configuration

Edit the `Spec` defaults in `cad/enclosure_3d_printed.py`.

- **`populated_ports`**: The SMA jacks that are fitted, by PCB silkscreen name: `IN0`..`IN7`, `OUT0`, `SW_OUT`, `TEST_A`, `TEST_B`. The default is `IN0`..`IN4`, `OUT0`, `SW_OUT`. The lid gets a hole for each one, with an engraved label directly south of it and a line to the port's LED (inputs only). Every other port position stays solid.
- **`label_closed_ports`**: Engrave closed input ports' names beside their LED instead (on by default). Closed ports without an LED (`OUT0`, `SW_OUT`, `TEST_*`) stay unlabelled.
- **`sma_body_height`**, **`sma_body_size`**: The Amphenol 901-144's square body. The height is measured at 2 mm, which (plus `sma_body_clearance`) stays under the lid, so there are no square pockets. If a taller body would reach the lid, it gets pocketed from underneath, and the labels move to clear the pocket.
- **`usb_receptacle_bottom_height`**, **`usb_receptacle_height_tolerance`**: Measured height of the RP2040-Zero's USB-C receptacle bottom above the main PCB (11.73 ± 0.3 mm), which sets the USB-C cutout height. The 7.5 mm cutout fits a 6.5 mm plug overmold (`usb_plug_overmold_height`) anywhere in that tolerance; the build fails if it wouldn't.
- **`tall_region_height`**: Height the RF can and RP2040-Zero need above the PCB (20 mm).
- **`clearance_below_pcb`**, **`clearance_above_pcb`**: Air gaps under and over the PCB (3.8 mm each).

### Features

- Raised pocket, with rounded outside corners and top edges, over the RF can and the socketed RP2040-Zero, with a USB-C cutout sized for the plug overmold.
- 1.2 mm windows over all 12 LEDs, for filling with clear epoxy: status, the 3 switch-control LEDs, and the 8 LNA-power LEDs.
- The push buttons are enclosed and not accessible.

PCB positions come from `cad/pcb_layout.py`, which was extracted from the KiCad board (Rev 1). Update it if the PCB layout changes.
