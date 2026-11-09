"""3D-printable enclosure for the Antenna-Array-Switch-PCB.

Parts:
    - `tray`: Bottom. PCB sits on standoffs with M3 heat-set inserts.
    - `lid`: Top plate with SMA holes, LED windows, and port labels. Has a
        raised pocket over the RF can / socketed RP2040-Zero, with a USB-C
        cutout in its wall.
    - `spacers`: Tubes between the PCB top and the lid (print one set).

Assembly (bottom to top): tray -> PCB -> spacers -> lid. M3 screws go down
through the lid, spacers, and PCB into the tray's heat-set inserts.

Configure which RF connectors are populated with `Spec.populated_ports`.
Unpopulated ports are closed (solid lid, no label).
"""

import math
from dataclasses import dataclass
from pathlib import Path

import build123d as bd
from build123d_ease import show
from loguru import logger

from cad import pcb_layout as pcb

# Small overlap so boolean cuts fully pierce faces.
EPS = 0.01


@dataclass
class Spec:
    """Specification for the enclosure. All dimensions in mm."""

    # Ports with an SMA jack fitted, by PCB silkscreen name. See
    # `pcb_layout.RF_PORTS` for all names.
    populated_ports: tuple[str, ...] = ("IN0", "OUT0", "IN2", "SW_OUT")
    label_closed_ports: bool = False

    # Shell.
    pcb_edge_clearance: float = 0.5
    wall_thickness: float = 2.0
    floor_thickness: float = 2.0
    lid_thickness: float = 2.0
    outer_corner_radius: float = 3.0

    # Air gaps set by the standoffs (tray side) and spacers (lid side).
    clearance_below_pcb: float = 3.8
    clearance_above_pcb: float = 3.8

    # The RF can + socketed RP2040-Zero region gets a raised pocket.
    tall_region_height: float = 20.0  # Above the PCB top surface.
    tall_region_clearance: float = 0.5  # Extra, in X/Y and Z.
    # Thinner than the outer walls: LEDs D202..D204 sit 2.4 mm from the can.
    tall_region_wall_thickness: float = 1.6
    # Pocket sides this close to the outer wall are merged into it (so the
    # USB-C receptacle, which overhangs the can, reaches the outer wall).
    tall_region_snap_distance: float = 3.0

    # RP2040-Zero stack-up, for the USB-C cutout height.
    socket_height: float = 8.5  # Standard 2.54 mm female header.
    header_spacer_height: float = 2.5  # Male header plastic.
    rp2040_zero_pcb_thickness: float = 1.0
    usb_receptacle_height: float = 3.2
    # Big enough for a typical USB-C plug overmold to pass through.
    usb_cutout_width: float = 12.5
    usb_cutout_height: float = 7.0

    # Amphenol 901-144 vertical SMA jack. Body size/height are estimates:
    # check with calipers before printing.
    sma_thread_hole_diameter: float = 6.8  # 1/4"-36 thread.
    sma_body_size: float = 6.35
    sma_body_height: float = 4.6  # Above the PCB top surface.
    sma_body_clearance: float = 0.4  # Per side.

    led_hole_diameter: float = 1.2

    label_font_size: float = 3.5
    label_depth: float = 0.6
    label_gap: float = 1.2  # From the SMA hole edge to the text.

    # M3 hardware.
    screw_clearance_diameter: float = 3.4
    spacer_outer_diameter: float = 6.5  # Must fit on the 6.9 mm pad.
    standoff_outer_diameter: float = 7.5
    heat_set_insert_diameter: float = 4.0
    heat_set_insert_depth: float = 5.0

    def __post_init__(self) -> None:
        """Post initialization checks."""
        unknown = set(self.populated_ports) - set(pcb.RF_PORTS)
        assert not unknown, f"Unknown ports: {unknown}"

        assert self.heat_set_insert_depth < (
            self.clearance_below_pcb + self.floor_thickness
        ), "Heat-set insert hole would pierce the tray floor."

        usb_bottom = self.usb_center_z - self.usb_cutout_height / 2
        usb_top = self.usb_center_z + self.usb_cutout_height / 2
        assert usb_bottom > self.lid_top_z, "USB cutout hits the lid plate."
        assert usb_top < self.tall_region_ceiling_z, (
            "USB cutout hits the raised pocket's ceiling."
        )

    # Z levels (tray floor underside at z=0).
    @property
    def pcb_bottom_z(self) -> float:
        """Z of the PCB underside."""
        return self.floor_thickness + self.clearance_below_pcb

    @property
    def pcb_top_z(self) -> float:
        """Z of the PCB component side."""
        return self.pcb_bottom_z + pcb.PCB_THICKNESS

    @property
    def lid_bottom_z(self) -> float:
        """Z of the lid underside (and the top of the tray walls)."""
        return self.pcb_top_z + self.clearance_above_pcb

    @property
    def lid_top_z(self) -> float:
        """Z of the lid's top surface."""
        return self.lid_bottom_z + self.lid_thickness

    @property
    def tall_region_ceiling_z(self) -> float:
        """Z of the underside of the raised pocket's ceiling."""
        return (
            self.pcb_top_z
            + self.tall_region_height
            + self.tall_region_clearance
        )

    @property
    def usb_center_z(self) -> float:
        """Z of the RP2040-Zero USB-C receptacle centre."""
        return (
            self.pcb_top_z
            + self.socket_height
            + self.header_spacer_height
            + self.rp2040_zero_pcb_thickness
            + self.usb_receptacle_height / 2
        )

    # X/Y extents (half-sizes, enclosure centred on the origin).
    @property
    def inner_half_x(self) -> float:
        """Half of the interior width."""
        return pcb.PCB_SIZE_X / 2 + self.pcb_edge_clearance

    @property
    def inner_half_y(self) -> float:
        """Half of the interior depth."""
        return pcb.PCB_SIZE_Y / 2 + self.pcb_edge_clearance

    @property
    def outer_half_x(self) -> float:
        """Half of the outside width."""
        return self.inner_half_x + self.wall_thickness

    @property
    def outer_half_y(self) -> float:
        """Half of the outside depth."""
        return self.inner_half_y + self.wall_thickness


def rounded_prism(
    half_x: float, half_y: float, radius: float, z0: float, z1: float
) -> bd.Part:
    """Rounded-rectangle prism, centred in X/Y, from z0 to z1."""
    sketch = bd.RectangleRounded(2 * half_x, 2 * half_y, radius)
    return bd.Pos(0, 0, z0) * bd.extrude(sketch, amount=z1 - z0)


Point3 = tuple[float, float, float]


def box_between(corner_a: Point3, corner_b: Point3) -> bd.Part:
    """Make an axis-aligned box spanning two corners."""
    x0, y0, z0 = corner_a
    x1, y1, z1 = corner_b
    return bd.Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * bd.Box(
        x1 - x0, y1 - y0, z1 - z0
    )


def mounting_hole_positions() -> list[tuple[float, float]]:
    """Mounting hole centres in enclosure coordinates."""
    return [pcb.kicad_to_cad(x, y) for x, y in pcb.MOUNTING_HOLES]


def outer_shell(spec: Spec, z0: float, z1: float) -> bd.Part:
    """Outside envelope of the enclosure between two Z levels."""
    return rounded_prism(
        spec.outer_half_x,
        spec.outer_half_y,
        spec.outer_corner_radius,
        z0,
        z1,
    )


def tray(spec: Spec) -> bd.Part | bd.Compound:
    """Bottom tray: floor, walls up to the lid, and PCB standoffs."""
    inner_radius = max(spec.outer_corner_radius - spec.wall_thickness, 0.1)

    p = outer_shell(spec, 0, spec.lid_bottom_z)
    p -= rounded_prism(
        spec.inner_half_x,
        spec.inner_half_y,
        inner_radius,
        spec.floor_thickness,
        spec.lid_bottom_z + EPS,
    )

    for x, y in mounting_hole_positions():
        p += bd.Cylinder(
            spec.standoff_outer_diameter / 2,
            spec.clearance_below_pcb + EPS,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ).moved(bd.Location((x, y, spec.floor_thickness - EPS)))
        p -= bd.Cylinder(
            spec.heat_set_insert_diameter / 2,
            spec.heat_set_insert_depth + EPS,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MAX),
        ).moved(bd.Location((x, y, spec.pcb_bottom_z + EPS)))

    assert isinstance(p, bd.Part | bd.Compound)
    return p


def tall_region_bounds(spec: Spec) -> tuple[float, float, float, float]:
    """Return the raised pocket interior as (x0, y0, x1, y1)."""
    kx0, ky0, kx1, ky1 = pcb.TALL_REGION
    x0, y1 = pcb.kicad_to_cad(kx0, ky0)  # KiCad +Y is down.
    x1, y0 = pcb.kicad_to_cad(kx1, ky1)
    c = spec.tall_region_clearance
    x0, y0, x1, y1 = x0 - c, y0 - c, x1 + c, y1 + c

    def snap(value: float, wall: float) -> float:
        """Snap a pocket side to the outer wall if it's close to it."""
        if abs(value - wall) < spec.tall_region_snap_distance:
            return wall
        return value

    return (
        snap(x0, -spec.inner_half_x),
        snap(y0, -spec.inner_half_y),
        snap(x1, spec.inner_half_x),
        snap(y1, spec.inner_half_y),
    )


def usb_cutout(spec: Spec) -> bd.Part:
    """USB-C cutout through the +Y wall of the raised pocket."""
    x, _ = pcb.kicad_to_cad(pcb.USB_CENTER_X, pcb.PCB_Y_MIN)
    wall_center_y = (spec.inner_half_y + spec.outer_half_y) / 2
    radius = min(spec.usb_cutout_width, spec.usb_cutout_height) / 2 - EPS
    sketch = bd.RectangleRounded(
        spec.usb_cutout_width, spec.usb_cutout_height, radius
    )
    # Extrude along Z, then rotate so the sketch stands in XZ, cutting in Y.
    cutter = bd.extrude(sketch, amount=spec.wall_thickness * 2, both=True)
    return bd.Pos(x, wall_center_y, spec.usb_center_z) * (
        bd.Rot(90, 0, 0) * cutter
    )


def label_center(
    spec: Spec, name: str, text_size: tuple[float, float]
) -> tuple[float, float]:
    """Place a port label beside its connector, like the PCB silkscreen."""
    port = pcb.RF_PORTS[name]
    cx, cy = pcb.kicad_to_cad(port.connector_x, port.connector_y)
    sx, sy = pcb.kicad_to_cad(port.silkscreen_x, port.silkscreen_y)
    length = math.hypot(sx - cx, sy - cy)
    ux, uy = (sx - cx) / length, (sy - cy) / length

    # Distance from the connector centre to the text box edge along (ux, uy).
    text_w, text_h = text_size
    half_extent = min(
        text_w / 2 / max(abs(ux), EPS), text_h / 2 / max(abs(uy), EPS)
    )
    distance = spec.sma_thread_hole_diameter / 2 + spec.label_gap
    distance += half_extent
    return (cx + ux * distance, cy + uy * distance)


def lid(spec: Spec) -> bd.Part | bd.Compound:
    """Lid: plate, raised pocket, SMA holes, LED windows, labels."""
    p = outer_shell(spec, spec.lid_bottom_z, spec.lid_top_z)

    # Raised pocket over the RF can / RP2040-Zero.
    x0, y0, x1, y1 = tall_region_bounds(spec)
    w = spec.tall_region_wall_thickness
    pocket_top_z = spec.tall_region_ceiling_z + spec.lid_thickness
    pocket = box_between(
        (x0 - w, y0 - w, spec.lid_bottom_z), (x1 + w, y1 + w, pocket_top_z)
    )
    pocket &= outer_shell(spec, spec.lid_bottom_z, pocket_top_z)
    p += pocket
    p -= box_between(
        (x0, y0, spec.lid_bottom_z - EPS), (x1, y1, spec.tall_region_ceiling_z)
    )
    p -= usb_cutout(spec)

    # Screw clearance holes.
    for x, y in mounting_hole_positions():
        p -= bd.Pos(x, y, spec.lid_bottom_z - EPS) * bd.Cylinder(
            spec.screw_clearance_diameter / 2,
            spec.lid_thickness + 2 * EPS,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )

    # LED windows (fill with clear epoxy).
    for x, y in (pcb.kicad_to_cad(*xy) for xy in pcb.LEDS.values()):
        p -= bd.Pos(x, y, spec.lid_bottom_z - EPS) * bd.Cylinder(
            spec.led_hole_diameter / 2,
            spec.lid_thickness + 2 * EPS,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )

    # SMA jacks: thread hole, plus a pocket for the square body if it
    # reaches the lid.
    body_top_z = (
        spec.pcb_top_z + spec.sma_body_height + spec.sma_body_clearance
    )
    body_width = spec.sma_body_size + 2 * spec.sma_body_clearance
    for name in spec.populated_ports:
        port = pcb.RF_PORTS[name]
        x, y = pcb.kicad_to_cad(port.connector_x, port.connector_y)
        p -= bd.Pos(x, y, spec.lid_bottom_z - EPS) * bd.Cylinder(
            spec.sma_thread_hole_diameter / 2,
            spec.lid_thickness + 2 * EPS,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        if body_top_z > spec.lid_bottom_z:
            p -= (
                bd.Pos(x, y, spec.lid_bottom_z - EPS)
                * bd.Rot(0, 0, port.rotation_deg)
                * bd.Box(
                    body_width,
                    body_width,
                    body_top_z - spec.lid_bottom_z + EPS,
                    align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
                )
            )

    # Engraved port labels.
    labelled = [
        name
        for name in pcb.RF_PORTS
        if name in spec.populated_ports or spec.label_closed_ports
    ]
    for name in labelled:
        text = bd.Text(pcb.RF_PORTS[name].label or name, spec.label_font_size)
        size = text.bounding_box().size
        x, y = label_center(spec, name, (size.X, size.Y))
        p -= bd.Pos(x, y, spec.lid_top_z + EPS) * bd.extrude(
            text, amount=-(spec.label_depth + EPS)
        )

    return p


def spacers(spec: Spec) -> bd.Part | bd.Compound:
    """One set of PCB-to-lid spacer tubes, laid out in a row for printing."""
    p = bd.Part(None)
    pitch = spec.spacer_outer_diameter + 3
    for i in range(len(pcb.MOUNTING_HOLES)):
        tube = bd.Cylinder(
            spec.spacer_outer_diameter / 2,
            spec.clearance_above_pcb,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        ) - bd.Cylinder(
            spec.screw_clearance_diameter / 2,
            spec.clearance_above_pcb * 3,
        )
        p += bd.Pos(i * pitch, 0, 0) * tube
    return p


def pcb_placeholder(spec: Spec) -> bd.Part | bd.Compound:
    """Rough PCB + tall region, for checking fit in the assembly view."""
    p = bd.Pos(0, 0, spec.pcb_bottom_z) * bd.Box(
        pcb.PCB_SIZE_X,
        pcb.PCB_SIZE_Y,
        pcb.PCB_THICKNESS,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    kx0, ky0, kx1, ky1 = pcb.TALL_REGION
    x0, y1 = pcb.kicad_to_cad(kx0, ky0)
    x1, y0 = pcb.kicad_to_cad(kx1, ky1)
    p += box_between(
        (x0, y0, spec.pcb_top_z),
        (x1, y1, spec.pcb_top_z + spec.tall_region_height),
    )
    return p


def assembly(spec: Spec) -> bd.Compound:
    """Everything in its assembled position."""
    spacer_set = [
        bd.Pos(x, y, spec.pcb_top_z)
        * bd.Cylinder(
            spec.spacer_outer_diameter / 2,
            spec.clearance_above_pcb,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        for x, y in mounting_hole_positions()
    ]
    return bd.Compound(
        children=[tray(spec), pcb_placeholder(spec), *spacer_set, lid(spec)]
    )


if __name__ == "__main__":
    spec = Spec()
    parts = {
        "enclosure_tray": tray(spec),
        "enclosure_lid": show(lid(spec)),
        "enclosure_spacers": spacers(spec),
        "enclosure_assembly": assembly(spec),
    }

    logger.info("Showing CAD model(s)")

    (export_folder := Path(__file__).parent.with_name("build")).mkdir(
        exist_ok=True
    )
    for name, part in parts.items():
        assert isinstance(part, bd.Part | bd.Solid | bd.Compound), (
            f"{name} is not an expected type ({type(part)})"
        )
        if not part.is_manifold:
            logger.warning(f'Part "{name}" is not manifold')

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
