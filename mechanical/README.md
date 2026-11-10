# Mechanical

CAD models for the yagi flower, written in [build123d](https://github.com/gumyr/build123d). Each model is a script in `cad/`:

| Script                         | What                                                           |
|--------------------------------|----------------------------------------------------------------|
| `cad/antenna_frame.py`         | [Antenna frame](#antenna-frame): the bowl that holds all 6 yagis. |
| `cad/enclosure_3d_printed.py`  | [Enclosure (3D-printed)](#enclosure-3d-printed) for the Antenna-Array-Switch-PCB. |

## Build

```bash
cd mechanical
uv sync
uv run python cad/antenna_frame.py          # Writes STL + STEP files to build/
uv run python cad/enclosure_3d_printed.py   # Likewise
```

## Antenna Frame

A 3D-printed bowl, 210 mm across the rim, that holds six yagis with 15 × 15 mm square booms. Five yagis are spread evenly around the outside, pointing outwards at 40° above the horizon. The sixth stands in a socket in the middle, pointing straight up.

| File                            | Print | Notes                                                              |
|---------------------------------|-------|--------------------------------------------------------------------|
| `antenna_frame.stl`             | 1     | Floor down. The sloped faces' undersides overhang 50° from vertical. |
| `antenna_frame_assembly.*`      | -     | Fit check only: the frame with a stub of each boom in place.       |

### Shape

The lower part of the bowl is a pentagonal frustum standing on a short vertical skirt. Each of its five flat outer faces slopes at 40°, and an outer yagi's boom lies flat against the underside of one, pointing outwards and up. The rim is trimmed round, but each face is kept flat for 5 mm either side of its boom.

### Mounting

Everything uses M5 bolts, two per yagi, 46 mm apart, with M5 nuts pressed into hex pockets in the frame.

- **Outer yagis**: The bolts go up through the boom and the wall, into nuts on the inside of the bowl. The tails stick out into the open bowl. The build logs how much room they have before reaching the centre yagi (about 65 mm past the wall for the lower bolts, 120 mm for the upper ones). The skirt is tall enough that a bolt up to `bolt_insertion_length` (45 mm, including the head) can be fed in from under the boom.
- **Centre yagi**: The boom stands in the square socket, on the floor. Two horizontal bolts go through the socket and the boom, into nuts on the far side of the socket. The bolt line runs through holes in the bowl wall on both sides (head-sized on the head side), aimed between the outer yagis, so these bolts can be any length.

Ten 4.5 mm holes in the floor take wood screws (e.g. #8 or M4) into a plywood base. Fit them before the antennas, since the bolt tails pass over them.

### Configuration

Edit the `Spec` defaults in `cad/antenna_frame.py`. The bowl's height and floor size are worked out from these.

- **`outer_antenna_count`**, **`outer_antenna_elevation_deg`**: Five outer yagis, at 40°.
- **`rim_diameter`**: 210 mm.
- **`boom_width`**, **`bolt_spacing`**: 15 mm booms, 46 mm between bolts.
- **`boom_rear_overhang`**: How far an outer boom extends behind its lower bolt (15 mm). A longer overhang moves the bolts further up the face, making the bowl taller.
- **`bolt_insertion_length`**: Sets the skirt height. See [Mounting](#mounting).
- **`floor_hole_count`**, **`floor_hole_ring_diameter`**, **`floor_hole_diameter`**: Wood screw holes. The build checks the screw heads clear the wall and the socket.

The build fails if the nut pockets would break out of a face, or if the centre yagi's bolt line would hit an outer boom.

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
