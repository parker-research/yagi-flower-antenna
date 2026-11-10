"""3D-printable frame that holds the six yagi antennas, in six parts.

Parts (all stand on, and screw into, a plywood base):
    - `hub` (1x): Pentagonal block in the middle. A square socket on top
        holds the vertical (centre) yagi.
    - `arm` (5x, identical): Bolts to one of the hub's flat sides and runs
        outwards along the base to a ramp, sloped at the outer yagis'
        elevation (40 degrees), that carries one outer yagi. Hollow and
        open underneath.

How far out the arms reach is worked out so the yagis' horizontal elements
clear each other (see `Spec.min_element_clearance`), and every part must
fit the printer (`Spec.printer_bed_size`).

Mounting (all M5, with captive nuts):
    - Outer yagis: The boom lies on top of the ramp, pointing outwards and
        up. Two bolts go down through the boom and the ramp into hex nut
        pockets on its underside. Tails run down into the arm, and out
        through its end wall if they're long enough.
    - Centre yagi: The boom stands in the socket. Two horizontal bolts go
        through the socket and the boom into hex nut pockets on the far
        side, aimed between the arms, so they can be any length.
    - Arms to hub: Two horizontal bolts per arm, from inside the hub
        (reached from underneath), into nut pockets inside the arm.

Wood screws go down tubes from the top, seating near the bottom.

Z is up, with the base at z=0. Arm/yagi `k` points along azimuth
`k * 360 / outer_antenna_count` degrees (arm 0 along +X).
"""

import math
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import build123d as bd
from build123d_ease import show
from loguru import logger

# Small overlap so boolean cuts fully pierce faces.
EPS = 0.01

Vec3 = tuple[float, float, float]


@dataclass
class Spec:
    """Specification for the antenna frame. All dimensions in mm."""

    # Antennas.
    outer_antenna_count: int = 5
    outer_antenna_elevation_deg: float = 40.0  # Above the horizon.
    boom_width: float = 15.0  # Square booms.
    bolt_spacing: float = 46.0  # Between a yagi's two mounting bolts.
    # How far an outer boom extends behind its rear (lower) bolt, down the
    # ramp. The boom's rear end can reach the bottom of the ramp.
    boom_rear_overhang: float = 15.0

    # Yagi elements, all horizontal, centred on the boom. Measured along
    # the boom, forwards from the front (outermost/upper) bolt.
    reflector_length: float = 340.0
    reflector_offset: float = 75.0  # Front bolt to reflector centre.
    # Gamma-match: the driven element is one continuous rod, like the
    # others. TODO: Measure its length; this is a placeholder.
    driven_element_length: float = 320.0
    driven_element_spacing: float = 155.0  # Reflector to driven element.
    element_diameter: float = 6.0  # Display only.
    # The arms reach out until every element is at least this far from
    # every other yagi's elements, and from the base.
    min_element_clearance: float = 25.0
    # For reporting the driven elements' spacing in wavelengths.
    design_frequency_mhz: float = 435.0

    # Printer. Every part must fit, standing as modelled.
    printer_bed_size: float = 210.0
    printer_max_height: float = 210.0

    # Hub.
    hub_apothem: float = 60.0  # Centre to each flat side.
    hub_wall_thickness: float = 8.0
    hub_top_thickness: float = 8.0
    hub_rib_thickness: float = 5.0

    # Arms.
    arm_width: float = 46.0
    arm_side_wall_thickness: float = 4.0
    arm_end_wall_thickness: float = 8.0  # Against the hub.
    arm_outer_wall_thickness: float = 6.0  # Far end, under the ramp top.
    arm_top_thickness: float = 8.0  # Flat part, between hub and ramp.
    ramp_thickness: float = 8.0  # Perpendicular to the ramp.
    bolt_edge_margin: float = 8.0  # Bolt centre to the ramp's top edge.

    # Room for an outer bolt's tail, from the underside of the ramp to the
    # base (z=0). Sets the height of the hub and the arms' flat part.
    min_bolt_tail_length: float = 50.0

    # M5 hardware. Bolts go through a clearance hole, into a hex nut pocket.
    bolt_clearance_diameter: float = 5.5
    nut_width_across_flats: float = 8.0
    nut_thickness: float = 4.0
    nut_clearance: float = 0.3  # Added across the flats, for a press fit.
    nut_pocket_depth: float = 4.5  # Deeper than the nut: it sits recessed.
    # Under the ramp, the nut pocket is kept open this far past the
    # underside (so the nut can go in straight), clear of the end wall.
    nut_access_length: float = 3.0

    # Arm-to-hub bolts: two per arm, side by side, at half the hub height.
    joint_bolt_spacing: float = 24.0

    # Centre socket, on top of the hub.
    socket_wall_thickness: float = 7.0
    socket_fit_clearance: float = 0.3  # Per side, around the boom.
    center_bolt_floor_margin: float = 15.0  # Lower bolt above hub top.
    center_bolt_top_margin: float = 12.0  # Upper bolt below socket top.

    # Wood screws into the plywood base (e.g. #8 or M4). Each goes down a
    # bore in a solid tower and seats near the bottom.
    hub_screw_ring_diameter: float = 80.0  # Between the arms.
    ramp_screw_offset: float = 14.0  # Either side of the boom.
    screw_hole_diameter: float = 4.5
    screw_bore_diameter: float = 10.0  # For the head and screwdriver.
    screw_seat_thickness: float = 6.0  # Under the head.
    screw_tower_diameter: float = 16.0

    # Assembly view only.
    boom_display_length: float = 400.0

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert 0 < self.outer_antenna_elevation_deg < 90  # noqa: PLR2004
        assert self.boom_rear_overhang >= self.bolt_edge_margin, (
            "Rear bolt is too close to the bottom of the ramp."
        )
        assert self.nut_thickness < self.nut_pocket_depth, (
            "Nut doesn't fit in its pocket."
        )
        for name, wall in (
            ("ramp", self.ramp_thickness),
            ("socket wall", self.socket_wall_thickness),
            ("arm end wall", self.arm_end_wall_thickness),
        ):
            assert self.nut_pocket_depth <= wall - 2, (
                f"Less than 2 mm of {name} left beside a nut pocket."
            )
        assert self.screw_tower_diameter - self.screw_bore_diameter >= 4, (  # noqa: PLR2004
            "Screw tower walls are under 2 mm."
        )
        assert self.boom_width < self.arm_width
        # Ramp screw towers clear the nut pockets and fit in the arm.
        tower_r = self.screw_tower_diameter / 2
        assert self.ramp_screw_offset - tower_r >= self.nut_pocket_radius, (
            "Ramp screw towers run into the nut pockets."
        )
        assert self.ramp_screw_offset + tower_r <= self.arm_width / 2

        # The rear nut pocket must sit under the ramp, not the flat top.
        e = self.elevation_rad
        rear_nut_r = (
            self.rear_bolt_slant * math.cos(e)
            + self.ramp_thickness * math.sin(e)
            - self.nut_pocket_radius * math.cos(e)
        )
        assert rear_nut_r > self.ramp_underside_start_offset, (
            "Rear nut pocket runs into the arm's flat top."
        )

        # Hub screws clear the socket.
        bore_r = self.screw_bore_diameter / 2
        for x, y in hub_screw_positions(self):
            gap = distance_to_socket(self, x, y) - bore_r
            assert gap >= 1, f"Hub screw at ({x:.1f}, {y:.1f}) hits socket."

        assert self.center_bolt_z[1] < self.socket_top_z
        assert self.flat_screw_positions(), "Arm's flat part is too short."

    @property
    def elevation_rad(self) -> float:
        """Outer antenna elevation, in radians."""
        return math.radians(self.outer_antenna_elevation_deg)

    @property
    def outer_azimuths_deg(self) -> list[float]:
        """Azimuth of each outer yagi (and its arm)."""
        n = self.outer_antenna_count
        return [360 * k / n for k in range(n)]

    @property
    def between_azimuths_deg(self) -> list[float]:
        """Azimuths halfway between the arms."""
        half = 180 / self.outer_antenna_count
        return [a + half for a in self.outer_azimuths_deg]

    @property
    def nut_pocket_radius(self) -> float:
        """Circumradius (centre to corner) of the hex nut pocket."""
        flats = self.nut_width_across_flats + self.nut_clearance
        return flats / 2 / math.cos(math.radians(30))

    # Positions along the ramp are "slant" distances, measured up its top
    # surface from where it starts (at the end of the arm's flat part).
    @property
    def rear_bolt_slant(self) -> float:
        """Slant position of the rear (lower) outer bolt."""
        return self.boom_rear_overhang

    @property
    def front_bolt_slant(self) -> float:
        """Slant position of the front (upper) outer bolt."""
        return self.rear_bolt_slant + self.bolt_spacing

    @property
    def ramp_slant_length(self) -> float:
        """Length of the ramp's top, from the flat part to the arm's end."""
        e = self.elevation_rad
        # The front nut pocket (and its access past the underside) must
        # stay clear of the end wall. Its outermost point, radially, past
        # the front bolt's position on top of the ramp:
        nut_reach = (self.ramp_thickness + self.nut_access_length) * math.sin(
            e
        ) + self.nut_pocket_radius * math.cos(e)
        nut_margin = (nut_reach + self.arm_outer_wall_thickness + 1) / (
            math.cos(e)
        )
        return self.front_bolt_slant + max(self.bolt_edge_margin, nut_margin)

    @property
    def flat_height(self) -> float:
        """Z of the hub top, and the arms' flat top (where the ramp starts).

        High enough for `min_bolt_tail_length` under the rear bolts.
        """
        e = self.elevation_rad
        rear_bolt_rise = self.rear_bolt_slant * math.sin(e)
        underside_drop = self.ramp_thickness * math.cos(e)
        return (
            self.min_bolt_tail_length * math.cos(e)
            + underside_drop
            - rear_bolt_rise
        )

    @cached_property
    def ramp_start_radius(self) -> float:
        """Distance from the axis to where each ramp starts.

        As small as possible while the elements keep
        `min_element_clearance`.
        """
        start = (
            self.hub_apothem
            + self.arm_end_wall_thickness
            + self.screw_tower_diameter * 3
        )
        for r in range(math.ceil(start), 2000):
            if element_clearance(self, r) >= self.min_element_clearance:
                return r
        msg = "No arm length gives the elements enough clearance."
        raise ValueError(msg)

    @property
    def ramp_underside_start_offset(self) -> float:
        """Radially, how far past the ramp start its underside starts."""
        e = self.elevation_rad
        drop = self.ramp_thickness / math.cos(e) - self.arm_top_thickness
        return drop / math.tan(e)

    @property
    def arm_end_radius(self) -> float:
        """Distance from the axis to the far end of each arm."""
        run = self.ramp_slant_length * math.cos(self.elevation_rad)
        return self.ramp_start_radius + run

    @property
    def arm_top_z(self) -> float:
        """Z of the top of each arm (the ramp's top edge)."""
        rise = self.ramp_slant_length * math.sin(self.elevation_rad)
        return self.flat_height + rise

    @property
    def arm_length(self) -> float:
        """Length of each arm, from the hub to its far end."""
        return self.arm_end_radius - self.hub_apothem

    def ramp_z_at(self, r: float) -> float:
        """Z of the ramp's top at distance r from the axis."""
        return self.flat_height + (r - self.ramp_start_radius) * math.tan(
            self.elevation_rad
        )

    def ramp_underside_z_at(self, r: float) -> float:
        """Z of the ramp's underside at distance r from the axis."""
        return self.ramp_z_at(r) - self.ramp_thickness / math.cos(
            self.elevation_rad
        )

    # Centre socket.
    @property
    def socket_inner_size(self) -> float:
        """Inside width of the centre socket."""
        return self.boom_width + 2 * self.socket_fit_clearance

    @property
    def socket_outer_size(self) -> float:
        """Outside width of the centre socket."""
        return self.socket_inner_size + 2 * self.socket_wall_thickness

    @property
    def center_bolt_z(self) -> tuple[float, float]:
        """Z of the centre yagi's lower and upper bolts."""
        lower = self.flat_height + self.center_bolt_floor_margin
        return lower, lower + self.bolt_spacing

    @property
    def socket_top_z(self) -> float:
        """Z of the top of the centre socket."""
        return self.center_bolt_z[1] + self.center_bolt_top_margin

    @property
    def center_bolt_azimuth_deg(self) -> float:
        """Azimuth the centre bolts point along (nut side).

        Chosen so both ends of the bolt line are as far as possible from
        the arms.
        """

        def clearance(phi: float) -> float:
            return min(
                angle_between(end, arm)
                for end in (phi, phi + 180)
                for arm in self.outer_azimuths_deg
            )

        return max((i / 2 for i in range(360)), key=clearance)

    def flat_screw_positions(self) -> list[float]:
        """Radii of the screws along each arm's flat part (centreline)."""
        tower_r = self.screw_tower_diameter / 2
        first = self.hub_apothem + self.arm_end_wall_thickness + 2 * tower_r
        # Stay clear of the boom's rear end, which leans over the flat top.
        last = self.ramp_start_radius - self.boom_width - tower_r
        if last < first:
            return []
        if last - first < 2 * self.screw_tower_diameter:
            return [(first + last) / 2]
        return [first, last]


def angle_between(a_deg: float, b_deg: float) -> float:
    """Smallest angle between two azimuths, in degrees."""
    return abs((a_deg - b_deg + 180) % 360 - 180)


def add(a: Vec3, b: Vec3, k: float = 1.0) -> Vec3:
    """Return a + k * b."""
    return (a[0] + k * b[0], a[1] + k * b[1], a[2] + k * b[2])


def polar(radius: float, azimuth_deg: float) -> tuple[float, float]:
    """XY point at a radius and azimuth."""
    a = math.radians(azimuth_deg)
    return radius * math.cos(a), radius * math.sin(a)


@dataclass
class RampFrame:
    """Directions for one outer yagi's ramp."""

    radial: Vec3  # Horizontal, outwards.
    tangent: Vec3  # Horizontal, across the ramp.
    up_slope: Vec3  # Along the boom, outwards and up.
    normal: Vec3  # Out of the ramp's top surface, inwards and up.


def ramp_frame(spec: Spec, azimuth_deg: float) -> RampFrame:
    """Directions for the ramp at an azimuth."""
    a = math.radians(azimuth_deg)
    e = spec.elevation_rad
    r = (math.cos(a), math.sin(a), 0.0)
    return RampFrame(
        radial=r,
        tangent=(-math.sin(a), math.cos(a), 0.0),
        up_slope=(math.cos(e) * r[0], math.cos(e) * r[1], math.sin(e)),
        normal=(-math.sin(e) * r[0], -math.sin(e) * r[1], math.cos(e)),
    )


def ramp_point(
    spec: Spec,
    azimuth_deg: float,
    slant: float,
    ramp_start_radius: float | None = None,
) -> Vec3:
    """Point on the centreline of a ramp's top, `slant` up from its start.

    `ramp_start_radius` defaults to `spec.ramp_start_radius`.
    """
    if ramp_start_radius is None:
        ramp_start_radius = spec.ramp_start_radius
    f = ramp_frame(spec, azimuth_deg)
    start = add((0, 0, spec.flat_height), f.radial, ramp_start_radius)
    return add(start, f.up_slope, slant)


def along_axis(origin: Vec3, axis: Vec3, x_dir: Vec3) -> bd.Location:
    """Location whose local Z is `axis`, at `origin`."""
    return bd.Location(bd.Plane(origin=origin, x_dir=x_dir, z_dir=axis))


def cylinder_along(
    loc: bd.Location, diameter: float, z0: float, z1: float
) -> bd.Part:
    """Cylinder on the local Z axis of `loc`, from local z0 to z1."""
    return (
        loc
        * bd.Pos(0, 0, z0)
        * bd.Cylinder(
            diameter / 2,
            z1 - z0,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )


def hex_along(spec: Spec, loc: bd.Location, z0: float, z1: float) -> bd.Part:
    """Hex nut pocket on the local Z axis of `loc`, from local z0 to z1."""
    hexagon = bd.RegularPolygon(spec.nut_pocket_radius, 6)
    return loc * bd.Pos(0, 0, z0) * bd.extrude(hexagon, amount=z1 - z0)


def upright_cylinder(
    radius: float, z0: float, z1: float, x: float = 0, y: float = 0
) -> bd.Part:
    """Vertical cylinder at (x, y), from z0 to z1."""
    return bd.Pos(x, y, z0) * bd.Cylinder(
        radius, z1 - z0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )


def polygon_prism(spec: Spec, apothem: float, z0: float, z1: float) -> bd.Part:
    """N-sided prism, centred on the axis, with a flat side facing +X."""
    n = spec.outer_antenna_count
    # Align.NONE keeps it centred on the axis (odd sides aren't symmetric
    # in their bounding box). Rotated so a side, not a corner, faces +X.
    sketch = bd.RegularPolygon(
        apothem,
        n,
        major_radius=False,
        rotation=180 / n,
        align=(bd.Align.NONE, bd.Align.NONE),
    )
    return bd.Pos(0, 0, z0) * bd.extrude(sketch, amount=z1 - z0)


def side_profile(points: list[tuple[float, float]], width: float) -> bd.Part:
    """Extrude an (x, z) outline symmetrically in Y."""
    sketch = bd.Plane.XZ * bd.Polygon(
        *points, align=(bd.Align.NONE, bd.Align.NONE)
    )
    p = bd.extrude(sketch, amount=width / 2, both=True)
    assert isinstance(p, bd.Part)
    return p


def socket_location(spec: Spec, z: float = 0) -> bd.Location:
    """Centre socket frame: local X along the centre bolts (nut side)."""
    return bd.Location((0, 0, z), (0, 0, spec.center_bolt_azimuth_deg))


def distance_to_socket(spec: Spec, x: float, y: float) -> float:
    """Distance in XY from a point to the outside of the centre socket."""
    a = math.radians(-spec.center_bolt_azimuth_deg)
    u = x * math.cos(a) - y * math.sin(a)
    v = x * math.sin(a) + y * math.cos(a)
    half = spec.socket_outer_size / 2
    du, dv = max(abs(u) - half, 0), max(abs(v) - half, 0)
    return math.hypot(du, dv)


def hub_screw_positions(spec: Spec) -> list[tuple[float, float]]:
    """Wood screws through the hub, between the arms."""
    r = spec.hub_screw_ring_diameter / 2
    return [polar(r, a) for a in spec.between_azimuths_deg]


def arm_screw_positions(spec: Spec) -> list[tuple[float, float]]:
    """Wood screws through arm 0 (along +X)."""
    e = spec.elevation_rad
    mid_slant = (spec.rear_bolt_slant + spec.front_bolt_slant) / 2
    ramp_x = spec.ramp_start_radius + mid_slant * math.cos(e)
    off = spec.ramp_screw_offset
    return [(x, 0.0) for x in spec.flat_screw_positions()] + [
        (ramp_x, -off),
        (ramp_x, off),
    ]


def screw_cuts(
    spec: Spec, positions: list[tuple[float, float]]
) -> list[bd.Part]:
    """Bores (head and screwdriver) and through holes for wood screws."""
    cuts: list[bd.Part] = []
    for x, y in positions:
        cuts.append(
            upright_cylinder(
                spec.screw_bore_diameter / 2,
                spec.screw_seat_thickness,
                1000,
                x,
                y,
            )
        )
        cuts.append(
            upright_cylinder(
                spec.screw_hole_diameter / 2,
                -1,
                spec.screw_seat_thickness + EPS,
                x,
                y,
            )
        )
    return cuts


def screw_towers(
    spec: Spec, positions: list[tuple[float, float]], z_top: float
) -> list[bd.Part]:
    """Solid towers around the wood screws (trim to the part's outside)."""
    return [
        upright_cylinder(spec.screw_tower_diameter / 2, -1, z_top, x, y)
        for x, y in positions
    ]


def joint_bolt_locations(spec: Spec) -> list[bd.Location]:
    """Arm 0's bolts to the hub. Local Z points outwards, along +X."""
    z = spec.flat_height / 2
    half = spec.joint_bolt_spacing / 2
    return [
        bd.Location((0, y, z)) * bd.Rot(0, 90, 0)  # Local Z -> X.
        for y in (-half, half)
    ]


def outer_bolt_locations(spec: Spec, azimuth: float = 0) -> list[bd.Location]:
    """Locate an outer yagi's (rear, front) bolts, on top of its ramp.

    Local Z points along the bolt, into the ramp (outwards and down).
    """
    f = ramp_frame(spec, azimuth)
    down = add((0, 0, 0), f.normal, -1)
    return [
        along_axis(ramp_point(spec, azimuth, slant), down, f.tangent)
        for slant in (spec.rear_bolt_slant, spec.front_bolt_slant)
    ]


def center_bolt_locations(spec: Spec) -> list[bd.Location]:
    """Centre yagi bolts. Local Z is along the bolt, towards the nut."""
    return [
        socket_location(spec, z) * bd.Rot(0, 90, 0)  # Local Z -> X.
        for z in spec.center_bolt_z
    ]


def center_socket(spec: Spec) -> bd.Part:
    """Square socket for the vertical yagi's boom, on top of the hub."""
    z0, z1 = spec.flat_height - EPS, spec.socket_top_z
    outer, inner = spec.socket_outer_size, spec.socket_inner_size
    align = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    p = bd.Box(outer, outer, z1 - z0, align=align)
    p -= bd.Pos(0, 0, spec.flat_height - z0) * bd.Box(
        inner, inner, z1 - z0, align=align
    )
    p = socket_location(spec, z0) * p
    assert isinstance(p, bd.Part)
    return p


def hub(spec: Spec) -> bd.Part | bd.Compound:
    """Make the hub: hollow pentagonal block, open underneath, plus socket."""
    a, h = spec.hub_apothem, spec.flat_height
    envelope = polygon_prism(spec, a, 0, h)

    cavity = polygon_prism(
        spec, a - spec.hub_wall_thickness, -1, h - spec.hub_top_thickness
    )
    supports: bd.Part = bd.Part(None)
    for azimuth in spec.between_azimuths_deg:
        supports += bd.Rot(0, 0, azimuth) * bd.Box(
            2 * a,
            spec.hub_rib_thickness,
            h + 2,
            align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER),
        )
    for tower in screw_towers(spec, hub_screw_positions(spec), h + 1):
        supports += tower
    p = envelope - (cavity - supports)
    p += center_socket(spec)

    # Arm bolts: holes through each side (heads inside the hub).
    for azimuth in spec.outer_azimuths_deg:
        for loc in joint_bolt_locations(spec):
            p -= bd.Rot(0, 0, azimuth) * cylinder_along(
                loc, spec.bolt_clearance_diameter, a - 20, a + 1
            )

    # Centre yagi bolts: through the socket, with nut pockets on its far
    # side. Nothing else is on their line, so they can be any length.
    half = spec.socket_outer_size / 2
    for loc in center_bolt_locations(spec):
        p -= cylinder_along(
            loc, spec.bolt_clearance_diameter, -half - 1, half + 1
        )
        p -= hex_along(spec, loc, half - spec.nut_pocket_depth, half + 5)

    for cut in screw_cuts(spec, hub_screw_positions(spec)):
        p -= cut

    assert isinstance(p, bd.Part | bd.Compound)
    return p


def arm(spec: Spec) -> bd.Part | bd.Compound:
    """Make arm 0 (along +X), in place. The others are rotated copies."""
    a = spec.hub_apothem
    r0, r1 = spec.ramp_start_radius, spec.arm_end_radius
    h, top = spec.flat_height, spec.arm_top_z
    w = spec.arm_width

    envelope = side_profile([(a, 0), (r1, 0), (r1, top), (r0, h), (a, h)], w)

    # Hollow inside, open underneath: under the flat top, then the ramp.
    x0 = a + spec.arm_end_wall_thickness
    x1 = r1 - spec.arm_outer_wall_thickness
    flat_under = h - spec.arm_top_thickness
    ramp_under_start = r0 + spec.ramp_underside_start_offset
    cavity = side_profile(
        [
            (x0, -1),
            (x1, -1),
            (x1, spec.ramp_underside_z_at(x1)),
            (ramp_under_start, flat_under),
            (x0, flat_under),
        ],
        w - 2 * spec.arm_side_wall_thickness,
    )
    screws = arm_screw_positions(spec)
    supports: bd.Part = bd.Part(None)
    for tower in screw_towers(spec, screws, top + 1):
        supports += tower
    p = envelope - (cavity - supports)

    # Outer yagi bolts: the line is cut right through (ramp, and the end
    # wall if it reaches it), with nut pockets under the ramp.
    t = spec.ramp_thickness
    for loc in outer_bolt_locations(spec):
        p -= cylinder_along(loc, spec.bolt_clearance_diameter, -1, 500)
        p -= hex_along(
            spec, loc, t - spec.nut_pocket_depth, t + spec.nut_access_length
        )

    # Hub bolts: through the end wall, nuts on its inside, tails free.
    for loc in joint_bolt_locations(spec):
        p -= cylinder_along(loc, spec.bolt_clearance_diameter, a - 1, x0 + 1)
        p -= hex_along(spec, loc, x0 - spec.nut_pocket_depth, x0 + 3)

    for cut in screw_cuts(spec, screws):
        p -= cut

    assert isinstance(p, bd.Part | bd.Compound)
    return p


def arm_for_printing(spec: Spec) -> bd.Part | bd.Compound:
    """Arm 0, moved so its hub end is at x=0 (still standing on z=0)."""
    return bd.Pos(-spec.hub_apothem, 0, 0) * arm(spec)


@dataclass
class YagiFrame:
    """Where a yagi's boom is, for placing its elements."""

    front_bolt: Vec3  # On the boom's centreline.
    forward: Vec3  # Along the boom, towards the elements.
    across: Vec3  # Horizontal, square to the boom: along the elements.


def yagi_frames(
    spec: Spec, ramp_start_radius: float | None = None
) -> list[YagiFrame]:
    """Each yagi's boom frame: the outer yagis, then the centre one."""
    w = spec.boom_width
    frames: list[YagiFrame] = []
    for azimuth in spec.outer_azimuths_deg:
        f = ramp_frame(spec, azimuth)
        bolt = ramp_point(
            spec, azimuth, spec.front_bolt_slant, ramp_start_radius
        )
        frames.append(
            YagiFrame(
                front_bolt=add(bolt, f.normal, w / 2),
                forward=f.up_slope,
                across=f.tangent,
            )
        )
    phi = math.radians(spec.center_bolt_azimuth_deg)
    frames.append(
        YagiFrame(
            front_bolt=(0.0, 0.0, spec.center_bolt_z[1]),
            forward=(0.0, 0.0, 1.0),
            across=(-math.sin(phi), math.cos(phi), 0.0),
        )
    )
    return frames


@dataclass
class Element:
    """A yagi element: a straight rod, centred on the boom."""

    centre: Vec3
    axis: Vec3  # Unit vector along the rod.
    length: float

    def ends(self) -> tuple[Vec3, Vec3]:
        """Both tips of the rod."""
        half = self.length / 2
        return add(self.centre, self.axis, -half), add(
            self.centre, self.axis, half
        )

    def solid(self, diameter: float) -> bd.Part:
        """Make the rod as a cylinder."""
        loc = along_axis(self.centre, self.axis, (0.0, 0.0, 1.0))
        half = self.length / 2
        return cylinder_along(loc, diameter, -half, half)


def yagi_elements(spec: Spec, yagi: YagiFrame) -> tuple[Element, Element]:
    """Place a yagi's reflector and driven element."""
    reflector_at = spec.reflector_offset
    driven_at = reflector_at + spec.driven_element_spacing
    return (
        Element(
            add(yagi.front_bolt, yagi.forward, reflector_at),
            yagi.across,
            spec.reflector_length,
        ),
        Element(
            add(yagi.front_bolt, yagi.forward, driven_at),
            yagi.across,
            spec.driven_element_length,
        ),
    )


def segment_distance(p1: Vec3, q1: Vec3, p2: Vec3, q2: Vec3) -> float:
    """Shortest distance between two line segments, p1-q1 and p2-q2."""
    d1, d2 = add(q1, p1, -1), add(q2, p2, -1)
    r = add(p1, p2, -1)

    def dot(u: Vec3, v: Vec3) -> float:
        return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]

    a, e, f = dot(d1, d1), dot(d2, d2), dot(d2, r)
    c, b = dot(d1, r), dot(d1, d2)
    denom = a * e - b * b

    def clamp(x: float) -> float:
        return min(max(x, 0.0), 1.0)

    s = clamp((b * f - c * e) / denom) if denom > 1e-12 else 0.0  # noqa: PLR2004
    t = (b * s + f) / e
    if t < 0 or t > 1:
        t = clamp(t)
        s = clamp((b * t - c) / a)
    closest = add(add(p1, d1, s), add(p2, d2, t), -1)
    return math.sqrt(dot(closest, closest))


def element_clearance(spec: Spec, ramp_start_radius: float) -> float:
    """Smallest gap between elements of different yagis, or to the base."""
    rods = [
        (i, element)
        for i, yagi in enumerate(yagi_frames(spec, ramp_start_radius))
        for element in yagi_elements(spec, yagi)
    ]
    radius = spec.element_diameter / 2
    gaps = [
        min(z for _, _, z in element.ends()) - radius for _, element in rods
    ]
    for n, (i, rod_i) in enumerate(rods):
        for j, rod_j in rods[n + 1 :]:
            if i != j:
                gap = segment_distance(*rod_i.ends(), *rod_j.ends())
                gaps.append(gap - 2 * radius)
    return min(gaps)


def boom_placeholders(spec: Spec) -> list[bd.Part]:
    """Square booms in their mounted positions, with their bolt holes."""
    w, length = spec.boom_width, spec.boom_display_length
    d = spec.bolt_clearance_diameter
    booms: list[bd.Part] = []
    for azimuth in spec.outer_azimuths_deg:
        f = ramp_frame(spec, azimuth)
        rear_end = spec.rear_bolt_slant - spec.boom_rear_overhang
        centre = add(ramp_point(spec, azimuth, rear_end), f.normal, w / 2)
        loc = bd.Location(
            bd.Plane(origin=centre, x_dir=f.up_slope, z_dir=f.normal)
        )
        boom = loc * bd.Box(
            length,
            w,
            w,
            align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER),
        )
        # Bolt locations sit on the ramp, pointing into it, so the boom is
        # from local z=-w to 0.
        for bolt in outer_bolt_locations(spec, azimuth):
            boom -= cylinder_along(bolt, d, -w - 1, 1)
        assert isinstance(boom, bd.Part)
        booms.append(boom)

    centre_boom = socket_location(spec, spec.flat_height) * bd.Box(
        w, w, length, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    for bolt in center_bolt_locations(spec):
        centre_boom -= cylinder_along(bolt, d, -w, w)
    assert isinstance(centre_boom, bd.Part)
    booms.append(centre_boom)
    return booms


def placed_parts(
    spec: Spec,
    hub_part: bd.Part | bd.Compound,
    arm_part: bd.Part | bd.Compound,
) -> list[tuple[str, bd.Part | bd.Compound]]:
    """Place the hub and every arm in their assembled positions."""
    parts: list[tuple[str, bd.Part | bd.Compound]] = [("hub", hub_part)]
    for k, azimuth in enumerate(spec.outer_azimuths_deg):
        parts.append((f"arm_{k}", bd.Rot(0, 0, azimuth) * arm_part))
    return parts


def check_print_fit(
    spec: Spec,
    hub_part: bd.Part | bd.Compound,
    arm_part: bd.Part | bd.Compound,
) -> None:
    """Fail if a part doesn't fit the printer, standing as modelled."""
    for name, part in (("hub", hub_part), ("arm", arm_part)):
        size = part.bounding_box().size
        assert max(size.X, size.Y) <= spec.printer_bed_size, (
            f"The {name} is {size.X:.0f} x {size.Y:.0f} mm: too big to print."
        )
        assert spec.printer_max_height >= size.Z, (
            f"The {name} is {size.Z:.0f} mm tall: too tall to print."
        )
        logger.info(
            f"The {name} is {size.X:.0f} x {size.Y:.0f} x {size.Z:.0f} mm."
        )


def check_clearances(
    spec: Spec, parts: list[tuple[str, bd.Part | bd.Compound]]
) -> None:
    """Fail if a boom hits a part, or blocks a wood screw's bore."""
    booms = boom_placeholders(spec)
    bores: list[bd.Part] = [
        upright_cylinder(spec.screw_bore_diameter / 2, 0, 1000, x, y)
        for x, y in hub_screw_positions(spec)
    ]
    for azimuth in spec.outer_azimuths_deg:
        bores += [
            bd.Rot(0, 0, azimuth)
            * upright_cylinder(spec.screw_bore_diameter / 2, 0, 1000, x, y)
            for x, y in arm_screw_positions(spec)
        ]
    for i, boom in enumerate(booms):
        for name, part in parts:
            assert (boom & part).volume < EPS, f"Boom {i} runs into {name}."
        for bore in bores:
            assert (boom & bore).volume < EPS, (
                f"Boom {i} blocks a wood screw's bore."
            )


def check_elements(
    spec: Spec, parts: list[tuple[str, bd.Part | bd.Compound]]
) -> None:
    """Warn if an element hits a part, or a boom of another yagi."""
    booms = boom_placeholders(spec)
    for i, yagi in enumerate(yagi_frames(spec)):
        for name, element in zip(
            ("reflector", "driven element"),
            yagi_elements(spec, yagi),
            strict=True,
        ):
            rod = element.solid(spec.element_diameter)
            for part_name, part in parts:
                if (rod & part).volume > EPS:
                    logger.warning(f"Yagi {i}'s {name} hits {part_name}.")
            for j, boom in enumerate(booms):
                if j != i and (rod & boom).volume > EPS:
                    logger.warning(f"Yagi {i}'s {name} hits boom {j}.")


def report(spec: Spec) -> None:
    """Log the layout: size, element spacing, bolt lengths."""
    e = spec.elevation_rad
    reach = math.hypot(spec.arm_end_radius, spec.arm_width / 2)
    logger.info(
        f"Frame: {2 * reach:.0f} mm across, {spec.arm_top_z:.0f} mm tall at "
        f"the arm ends ({spec.socket_top_z:.0f} mm at the socket). Arms "
        f"are {spec.arm_length:.0f} mm long; ramps start "
        f"{spec.ramp_start_radius:.0f} mm from the centre."
    )

    wavelength = 299_792.458 / spec.design_frequency_mhz  # mm
    frames = yagi_frames(spec)
    outer = [yagi_elements(spec, y)[1] for y in frames[:-1]]
    centre = yagi_elements(spec, frames[-1])[1]
    feed_radius = math.hypot(outer[0].centre[0], outer[0].centre[1])
    tip_radius = max(math.hypot(x, y) for el in outer for x, y, _ in el.ends())
    logger.info(
        f"Driven elements (outer yagis): centres on a circle of radius "
        f"{feed_radius:.0f} mm ({feed_radius / wavelength:.2f} wavelengths "
        f"at {spec.design_frequency_mhz:.0f} MHz), "
        f"{outer[0].centre[2]:.0f} mm above the base. All of each element "
        f"fits in a circle of radius {tip_radius:.0f} mm."
    )
    logger.info(
        f"Driven element (centre yagi): {centre.centre[2]:.0f} mm above "
        "the base, on the axis."
    )
    gap = element_clearance(spec, spec.ramp_start_radius)
    logger.info(
        f"Elements are at least {gap:.0f} mm from other yagis' elements "
        "and the base."
    )

    for name, loc in zip(
        ("rear", "front"), outer_bolt_locations(spec), strict=True
    ):
        underside_z = loc.position.Z - spec.ramp_thickness * math.cos(e)
        tail = underside_z / math.cos(e)
        longest = spec.boom_width + spec.ramp_thickness + tail
        logger.info(
            f"Outer {name} bolts: up to {longest:.0f} mm long before the "
            f"tail reaches the base plane ({tail:.0f} mm past the nut)."
        )
    logger.info("Centre yagi bolts can be any length.")


def assembly(
    spec: Spec, parts: list[tuple[str, bd.Part | bd.Compound]]
) -> bd.Compound:
    """Hub, arms, booms, and elements in place."""

    def named(
        part: bd.Part | bd.Compound, label: str, color: str | None = None
    ) -> bd.Part:
        """Label a part, and colour it (None keeps the viewer's default)."""
        part = bd.Part(part.wrapped) if isinstance(part, bd.Compound) else part
        part.label = label
        if color is not None:
            part.color = bd.Color(color)
        return part

    booms = [
        named(boom, f"boom_{i}", "silver")
        for i, boom in enumerate(boom_placeholders(spec))
    ]
    elements: list[bd.Part] = []
    for i, yagi in enumerate(yagi_frames(spec)):
        reflector, driven = yagi_elements(spec, yagi)
        elements += [
            named(
                reflector.solid(spec.element_diameter),
                f"reflector_{i}",
                "darkorange",
            ),
            named(
                driven.solid(spec.element_diameter),
                f"driven_element_{i}",
                "firebrick",
            ),
        ]
    return bd.Compound(
        label="antenna_frame_assembly",
        children=[
            bd.Compound(
                label="frame",
                children=[named(part, name) for name, part in parts],
            ),
            bd.Compound(label="booms", children=booms),
            bd.Compound(label="elements", children=elements),
        ],
    )


if __name__ == "__main__":
    spec = Spec()
    report(spec)

    hub_part = hub(spec)
    arm_part = arm(spec)
    placed = placed_parts(spec, hub_part, arm_part)
    check_print_fit(spec, hub_part, arm_part)
    check_clearances(spec, placed)
    check_elements(spec, placed)

    parts = {
        "antenna_frame_hub": hub_part,
        "antenna_frame_arm": arm_for_printing(spec),
        "antenna_frame_assembly": show(assembly(spec, placed)),
    }

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
