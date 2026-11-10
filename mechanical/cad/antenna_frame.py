"""3D-printable frame that holds the six yagi antennas.

Shape: a cylinder, `Spec.rim_diameter` across, standing on the plywood base,
with a pentagonal dish sunk into its top. The dish has a flat floor and five
flat faces sloping up at the outer antennas' elevation (40 degrees). Under
the dish it's hollow and open at the bottom. The dish's sloped plate is held
up by the outer wall, five radial ribs (between the yagis), and a column
under the floor, all of which stand on the base.

Mounting (all M5, with captive nuts):
    - Outer yagis (5x): The boom lies on top of a sloped face, pointing
        outwards and up, past the rim. Two bolts go down through the boom
        and the plate into hex nut pockets on the plate's underside. Their
        tails run outwards and down into the hollow, through the outer
        wall if they're long enough.
    - Centre yagi (1x): The boom stands in a square socket on the floor.
        Two horizontal bolts go through the socket and the boom into hex
        nut pockets on the far side. The bolt line is cut right through the
        frame on both sides, aimed between the outer yagis.

Wood screws go down tubes from the top, seating near the bottom, to fix the
frame to the plywood base.

Z is up, with the base at z=0. Outer yagi `k` points along azimuth
`k * 360 / outer_antenna_count` degrees (yagi 0 along +X).
"""

import math
from dataclasses import dataclass
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
    # face. The boom's rear end can reach the dish floor.
    boom_rear_overhang: float = 15.0

    # Body.
    rim_diameter: float = 210.0
    outer_wall_thickness: float = 6.0
    plate_thickness: float = 8.0  # Sloped faces (perpendicular to them).
    floor_thickness: float = 8.0  # Flat dish floor, under the socket.
    rib_thickness: float = 5.0
    column_wall_thickness: float = 6.0  # Column under the dish floor.
    # Flat face kept clear of the round trim, either side of the boom.
    face_side_margin: float = 5.0
    # Bolt centre to the edge of a face, on top.
    bolt_edge_margin: float = 8.0

    # Room for an outer bolt's tail, from the underside of the plate to the
    # base (z=0). Sets how high the dish sits. Tails that reach the outer
    # wall go through it.
    min_bolt_tail_length: float = 50.0
    # Warn if there's less room than this above an outer boom, along the
    # bolt, to feed the bolt in (before reaching the centre socket). Bolt
    # length under the head, plus the head.
    min_bolt_feed_length: float = 35.0

    # M5 hardware. Bolts go through a clearance hole, into a hex nut pocket.
    bolt_clearance_diameter: float = 5.5
    # Centre yagi bolts: holes the head passes through, on the head side.
    bolt_head_clearance_diameter: float = 10.0
    nut_width_across_flats: float = 8.0
    nut_thickness: float = 4.0
    nut_clearance: float = 0.3  # Added across the flats, for a press fit.
    nut_pocket_depth: float = 4.5  # Deeper than the nut: it sits recessed.
    # Under the plate, the nut pocket is kept open this far past the
    # underside (so the nut can go in straight), clear of the outer wall.
    nut_access_length: float = 3.0

    # Centre socket.
    socket_wall_thickness: float = 7.0
    socket_fit_clearance: float = 0.3  # Per side, around the boom.
    # Lower bolt above the floor. High enough that the bolt line (and the
    # head-sized hole) passes beside the outer booms' rear ends.
    center_bolt_floor_margin: float = 26.0
    center_bolt_top_margin: float = 12.0  # Upper bolt below socket top.

    # Wood screws into the plywood base (e.g. #8 or M4), between the yagis.
    # Each goes down a bore in a solid tower and seats near the bottom.
    inner_screw_ring_diameter: float = 60.0  # Through the dish floor.
    outer_screw_ring_diameter: float = 150.0  # Through the sloped plate.
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
            "Rear bolt is too close to the bottom of the face."
        )
        assert self.nut_thickness < self.nut_pocket_depth, (
            "Nut doesn't fit in its pocket."
        )
        assert self.nut_pocket_depth <= self.plate_thickness - 2, (
            "Less than 2 mm of plate left over the outer nut pockets."
        )
        assert self.nut_pocket_depth <= self.socket_wall_thickness - 2, (
            "Less than 2 mm of socket wall left under the nut pockets."
        )
        assert self.screw_tower_diameter - self.screw_bore_diameter >= 4, (  # noqa: PLR2004
            "Screw tower walls are under 2 mm."
        )
        assert self.column_inner_apothem > self.socket_outer_size / 2 * (
            math.sqrt(2)
        ), "Column under the floor is too small for the socket."
        assert self.floor_z - self.floor_thickness > self.screw_seat_thickness

        # Floor screws clear the socket.
        bore_r = self.screw_bore_diameter / 2
        for x, y in inner_screw_positions(self):
            gap = distance_to_socket(self, x, y) - bore_r
            assert gap >= 1, f"Floor screw at ({x:.1f}, {y:.1f}) hits socket."

        assert self.center_bolt_z[1] < self.socket_top_z

    @property
    def elevation_rad(self) -> float:
        """Outer antenna elevation, in radians."""
        return math.radians(self.outer_antenna_elevation_deg)

    @property
    def outer_azimuths_deg(self) -> list[float]:
        """Azimuth of each outer yagi (and of its face's centre)."""
        n = self.outer_antenna_count
        return [360 * k / n for k in range(n)]

    @property
    def between_azimuths_deg(self) -> list[float]:
        """Azimuths halfway between outer yagis (ribs and screws)."""
        half = 180 / self.outer_antenna_count
        return [a + half for a in self.outer_azimuths_deg]

    @property
    def nut_pocket_radius(self) -> float:
        """Circumradius (centre to corner) of the hex nut pocket."""
        flats = self.nut_width_across_flats + self.nut_clearance
        return flats / 2 / math.cos(math.radians(30))

    @property
    def dish_inner_radius(self) -> float:
        """Radius of the round trim on the dish (inside the outer wall)."""
        return self.rim_diameter / 2 - self.outer_wall_thickness

    # Positions along a sloped face are "slant" distances, measured up the
    # face's top surface from where it meets the dish floor.
    @property
    def rear_bolt_slant(self) -> float:
        """Slant position of the rear (lower) outer bolt."""
        return self.boom_rear_overhang

    @property
    def front_bolt_slant(self) -> float:
        """Slant position of the front (upper) outer bolt."""
        return self.rear_bolt_slant + self.bolt_spacing

    @property
    def face_top_apothem(self) -> float:
        """Face's distance from the axis, at the rim.

        Small enough that the round trim leaves the face flat for
        `face_side_margin` either side of the boom.
        """
        half_width = self.boom_width / 2 + self.face_side_margin
        return math.sqrt(self.dish_inner_radius**2 - half_width**2)

    @property
    def face_slant_length(self) -> float:
        """Length of a sloped face, from the dish floor to the rim."""
        e = self.elevation_rad
        # The front nut pocket (and its access past the underside) must
        # stay inside the outer wall. Its outermost point, relative to the
        # front bolt's position on top of the face:
        nut_reach = (self.plate_thickness + self.nut_access_length) * math.sin(
            e
        ) + self.nut_pocket_radius * math.cos(e)
        inner_wall = self.rim_diameter / 2 - self.outer_wall_thickness - 1
        # front bolt radius = face_top_apothem - margin * cos(e)
        nut_margin = (self.face_top_apothem + nut_reach - inner_wall) / (
            math.cos(e)
        )
        return self.front_bolt_slant + max(self.bolt_edge_margin, nut_margin)

    @property
    def floor_apothem(self) -> float:
        """Dish floor's half-width (where the sloped faces start)."""
        run = self.face_slant_length * math.cos(self.elevation_rad)
        return self.face_top_apothem - run

    @property
    def floor_z(self) -> float:
        """Z of the dish floor's top surface.

        High enough for `min_bolt_tail_length` under the rear bolts.
        """
        e = self.elevation_rad
        rear_bolt_rise = self.rear_bolt_slant * math.sin(e)
        underside_drop = self.plate_thickness * math.cos(e)
        return (
            self.min_bolt_tail_length * math.cos(e)
            + underside_drop
            - rear_bolt_rise
        )

    @property
    def rim_z(self) -> float:
        """Z of the top of the rim (and the whole frame)."""
        return self.floor_z + self.face_slant_length * math.sin(
            self.elevation_rad
        )

    def dish_apothem_at(self, z: float) -> float:
        """Sloped faces' top surface: distance from the axis at height z."""
        return self.floor_apothem + (z - self.floor_z) / math.tan(
            self.elevation_rad
        )

    def underside_apothem_at(self, z: float) -> float:
        """Sloped plate's underside: distance from the axis at height z."""
        return self.dish_apothem_at(z) + self.plate_thickness / math.sin(
            self.elevation_rad
        )

    @property
    def column_outer_apothem(self) -> float:
        """Column under the floor, flush with the plate's underside."""
        return self.underside_apothem_at(self.floor_z - self.floor_thickness)

    @property
    def column_inner_apothem(self) -> float:
        """Inside of the column under the floor."""
        return self.column_outer_apothem - self.column_wall_thickness

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
        lower = self.floor_z + self.center_bolt_floor_margin
        return lower, lower + self.bolt_spacing

    @property
    def socket_top_z(self) -> float:
        """Z of the top of the centre socket."""
        return self.center_bolt_z[1] + self.center_bolt_top_margin

    @property
    def center_bolt_azimuth_deg(self) -> float:
        """Azimuth the centre bolts point along (nut side).

        Chosen so both ends of the bolt line are as far as possible from
        the outer yagis.
        """

        def clearance(phi: float) -> float:
            return min(
                angle_between(end, face)
                for end in (phi, phi + 180)
                for face in self.outer_azimuths_deg
            )

        return max((i / 2 for i in range(360)), key=clearance)


def angle_between(a_deg: float, b_deg: float) -> float:
    """Smallest angle between two azimuths, in degrees."""
    return abs((a_deg - b_deg + 180) % 360 - 180)


def add(a: Vec3, b: Vec3, scale: float = 1.0) -> Vec3:
    """Return a + scale * b."""
    return (a[0] + scale * b[0], a[1] + scale * b[1], a[2] + scale * b[2])


def polar(radius: float, azimuth_deg: float) -> tuple[float, float]:
    """XY point at a radius and azimuth."""
    a = math.radians(azimuth_deg)
    return radius * math.cos(a), radius * math.sin(a)


@dataclass
class FaceFrame:
    """Directions for one outer yagi's sloped face."""

    radial: Vec3  # Horizontal, outwards.
    tangent: Vec3  # Horizontal, along the face.
    up_slope: Vec3  # Along the boom, outwards and up.
    normal: Vec3  # Out of the face's top surface, inwards and up.


def face_frame(spec: Spec, azimuth_deg: float) -> FaceFrame:
    """Directions for the sloped face at an azimuth."""
    a = math.radians(azimuth_deg)
    e = spec.elevation_rad
    r = (math.cos(a), math.sin(a), 0.0)
    return FaceFrame(
        radial=r,
        tangent=(-math.sin(a), math.cos(a), 0.0),
        up_slope=(math.cos(e) * r[0], math.cos(e) * r[1], math.sin(e)),
        normal=(-math.sin(e) * r[0], -math.sin(e) * r[1], math.cos(e)),
    )


def face_point(spec: Spec, azimuth_deg: float, slant: float) -> Vec3:
    """Point on the centreline of a face's top, `slant` up from the floor."""
    f = face_frame(spec, azimuth_deg)
    bottom = add((0, 0, spec.floor_z), f.radial, spec.floor_apothem)
    return add(bottom, f.up_slope, slant)


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


def polygon_frustum(
    spec: Spec, apothem_bottom: float, apothem_top: float, z0: float, z1: float
) -> bd.Part:
    """N-sided frustum (prism if apothems match), a face centred on +X."""
    n = spec.outer_antenna_count

    def polygon(apothem: float, z: float) -> bd.Sketch:
        # Align.NONE keeps it centred on the axis (odd sides aren't
        # symmetric in their bounding box). Rotated so a face, not a
        # vertex, is at azimuth 0.
        sketch = bd.RegularPolygon(
            apothem,
            n,
            major_radius=False,
            rotation=180 / n,
            align=(bd.Align.NONE, bd.Align.NONE),
        )
        return bd.Pos(0, 0, z) * sketch

    p = bd.loft(
        [polygon(apothem_bottom, z0), polygon(apothem_top, z1)], ruled=True
    )
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


def inner_screw_positions(spec: Spec) -> list[tuple[float, float]]:
    """Wood screws through the dish floor, between the yagis."""
    r = spec.inner_screw_ring_diameter / 2
    return [polar(r, a) for a in spec.between_azimuths_deg]


def outer_screw_positions(spec: Spec) -> list[tuple[float, float]]:
    """Wood screws through the sloped plate, between the yagis."""
    r = spec.outer_screw_ring_diameter / 2
    return [polar(r, a) for a in spec.between_azimuths_deg]


def dish_recess(spec: Spec, z_top: float) -> bd.Part:
    """Space above the dish (floor and sloped faces), up to z_top."""
    p = polygon_frustum(
        spec,
        spec.floor_apothem,
        spec.dish_apothem_at(z_top),
        spec.floor_z,
        z_top,
    )
    p &= upright_cylinder(spec.dish_inner_radius, spec.floor_z - 1, z_top)
    assert isinstance(p, bd.Part)
    return p


def body(spec: Spec) -> bd.Part:
    """Dish, outer wall, ribs, column, and screw towers (no holes yet)."""
    r_rim, z_rim = spec.rim_diameter / 2, spec.rim_z
    envelope = upright_cylinder(r_rim, 0, z_rim) - dish_recess(
        spec, z_rim + 10
    )

    # Everything under the dish surface within the plate/floor thickness.
    z_floor_bottom = spec.floor_z - spec.floor_thickness
    plate = polygon_frustum(
        spec,
        spec.underside_apothem_at(z_floor_bottom),
        spec.underside_apothem_at(z_rim + 10),
        z_floor_bottom,
        z_rim + 10,
    )
    # Supports, all standing on the base. Oversized (below the base, past
    # the rim, into the plate) so the envelope trims them without leaving
    # coincident faces.
    lo, hi = -1, z_rim + 1
    supports = upright_cylinder(r_rim + 1, lo, hi) - upright_cylinder(
        r_rim - spec.outer_wall_thickness, lo - 1, hi + 1
    )
    column_top = spec.floor_z - spec.floor_thickness / 2
    supports += polygon_frustum(
        spec,
        spec.column_outer_apothem,
        spec.column_outer_apothem,
        lo,
        column_top,
    ) - polygon_frustum(
        spec,
        spec.column_inner_apothem,
        spec.column_inner_apothem,
        lo - 1,
        column_top + 1,
    )
    for azimuth in spec.between_azimuths_deg:
        supports += (
            bd.Rot(0, 0, azimuth)
            * bd.Pos(0, 0, lo)
            * bd.Box(
                r_rim + 1,
                spec.rib_thickness,
                hi - lo,
                align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.MIN),
            )
        )
    for x, y in inner_screw_positions(spec) + outer_screw_positions(spec):
        supports += upright_cylinder(
            spec.screw_tower_diameter / 2, lo, hi, x, y
        )

    p = envelope & (plate + supports)
    assert isinstance(p, bd.Part)
    return p


def outer_bolt_locations(spec: Spec) -> list[tuple[float, bd.Location]]:
    """Each outer bolt as (azimuth, location on top of the face).

    Local Z points along the bolt, into the plate (outwards and down).
    """
    result: list[tuple[float, bd.Location]] = []
    for azimuth in spec.outer_azimuths_deg:
        f = face_frame(spec, azimuth)
        down = add((0, 0, 0), f.normal, -1)
        for slant in (spec.rear_bolt_slant, spec.front_bolt_slant):
            origin = face_point(spec, azimuth, slant)
            result.append((azimuth, along_axis(origin, down, f.tangent)))
    return result


def center_bolt_locations(spec: Spec) -> list[bd.Location]:
    """Centre yagi bolts. Local Z is along the bolt, towards the nut."""
    return [
        socket_location(spec, z) * bd.Rot(0, 90, 0)  # Local Z -> X.
        for z in spec.center_bolt_z
    ]


def center_bolt_corridors(spec: Spec) -> list[bd.Part]:
    """Space the centre bolts need: the line, and the head's way in."""
    far = spec.rim_diameter
    half = spec.socket_outer_size / 2
    result: list[bd.Part] = []
    for loc in center_bolt_locations(spec):
        result.append(
            cylinder_along(loc, spec.bolt_clearance_diameter, -far, far)
        )
        result.append(
            cylinder_along(loc, spec.bolt_head_clearance_diameter, -far, -half)
        )
    return result


def screw_corridors(spec: Spec) -> list[bd.Part]:
    """Vertical bores for the wood screws' heads and the screwdriver."""
    return [
        upright_cylinder(
            spec.screw_bore_diameter / 2, spec.screw_seat_thickness, 1000, x, y
        )
        for x, y in inner_screw_positions(spec) + outer_screw_positions(spec)
    ]


def center_socket(spec: Spec) -> bd.Part:
    """Square socket for the vertical yagi's boom, standing on the floor."""
    z0, z1 = spec.floor_z - EPS, spec.socket_top_z
    outer, inner = spec.socket_outer_size, spec.socket_inner_size
    align = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    p = bd.Box(outer, outer, z1 - z0, align=align)
    p -= bd.Pos(0, 0, spec.floor_z - z0) * bd.Box(
        inner, inner, z1 - z0, align=align
    )
    p = socket_location(spec, z0) * p
    assert isinstance(p, bd.Part)
    return p


def frame(spec: Spec) -> bd.Part | bd.Compound:
    """Make the whole antenna frame (one print)."""
    p = body(spec) + center_socket(spec)

    # Outer yagis: bolt line cut right through (plate, and the outer wall
    # where it reaches it), with nut pockets on the plate's underside.
    t = spec.plate_thickness
    for _, loc in outer_bolt_locations(spec):
        p -= cylinder_along(loc, spec.bolt_clearance_diameter, -1, 500)
        p -= hex_along(
            spec,
            loc,
            t - spec.nut_pocket_depth,
            t + spec.nut_access_length,
        )

    # Centre yagi: horizontal bolts, cut right through the frame.
    half = spec.socket_outer_size / 2
    for cutter in center_bolt_corridors(spec):
        p -= cutter
    for loc in center_bolt_locations(spec):
        p -= hex_along(spec, loc, half - spec.nut_pocket_depth, half + 5)

    # Wood screws: through hole at the bottom, bore above.
    for cutter in screw_corridors(spec):
        p -= cutter
    for x, y in inner_screw_positions(spec) + outer_screw_positions(spec):
        p -= upright_cylinder(
            spec.screw_hole_diameter / 2,
            -EPS,
            spec.screw_seat_thickness + EPS,
            x,
            y,
        )

    assert isinstance(p, bd.Part | bd.Compound)
    return p


def boom_placeholders(spec: Spec) -> list[bd.Part]:
    """Square booms in their mounted positions."""
    w, length = spec.boom_width, spec.boom_display_length
    booms: list[bd.Part] = []
    for azimuth in spec.outer_azimuths_deg:
        f = face_frame(spec, azimuth)
        rear_end = spec.rear_bolt_slant - spec.boom_rear_overhang
        centre = add(face_point(spec, azimuth, rear_end), f.normal, w / 2)
        loc = bd.Location(
            bd.Plane(origin=centre, x_dir=f.up_slope, z_dir=f.normal)
        )
        booms.append(
            loc
            * bd.Box(
                length,
                w,
                w,
                align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.CENTER),
            )
        )
    booms.append(
        socket_location(spec, spec.floor_z)
        * bd.Box(
            w,
            w,
            length,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    return booms


def check_clearances(spec: Spec, part: bd.Part | bd.Compound) -> None:
    """Fail if a boom hits the frame, a centre bolt, or a screw's bore."""
    booms = boom_placeholders(spec)
    keep_out = [
        ("frame", part),
        *(("centre yagi bolt", c) for c in center_bolt_corridors(spec)),
        *(("screw bore", c) for c in screw_corridors(spec)),
    ]
    center_boom = len(booms) - 1
    for i, boom in enumerate(booms):
        for name, shape in keep_out:
            if i == center_boom and name == "centre yagi bolt":
                continue  # They go through it.
            overlap = (boom & shape).volume
            assert overlap < EPS, f"Boom {i} runs into a {name}."


def ray_box_distance(
    origin: Vec3,
    direction: Vec3,
    box_min: Vec3,
    box_max: Vec3,
) -> float | None:
    """Distance along a ray to where it enters a box (slab method)."""
    t_enter, t_exit = 0.0, math.inf
    for o, d, lo, hi in zip(origin, direction, box_min, box_max, strict=True):
        if abs(d) < 1e-12:  # noqa: PLR2004
            if not lo <= o <= hi:
                return None
            continue
        t0, t1 = sorted(((lo - o) / d, (hi - o) / d))
        t_enter, t_exit = max(t_enter, t0), min(t_exit, t1)
    return t_enter if t_enter <= t_exit else None


def head_side_room(spec: Spec, loc: bd.Location) -> float:
    """Room above an outer boom, along the bolt, to feed the bolt in.

    Limited by the centre socket and the centre yagi's boom.
    """
    # Work in the socket's frame, where both obstacles are axis-aligned.
    to_socket = socket_location(spec).inverse() * loc
    origin, axis = to_socket.position, -to_socket.z_axis.direction
    # Start from the top of the boom.
    w = spec.boom_width
    o: Vec3 = (
        origin.X + axis.X * w,
        origin.Y + axis.Y * w,
        origin.Z + axis.Z * w,
    )
    d: Vec3 = (axis.X, axis.Y, axis.Z)
    half_s, half_b = spec.socket_outer_size / 2, w / 2
    z0 = spec.floor_z
    hits = [
        ray_box_distance(
            o, d, (-half_s, -half_s, z0), (half_s, half_s, spec.socket_top_z)
        ),
        ray_box_distance(o, d, (-half_b, -half_b, z0), (half_b, half_b, 1e6)),
    ]
    return min((h for h in hits if h is not None), default=math.inf)


def report_bolts(spec: Spec) -> None:
    """Log how long each outer bolt can be."""
    e = spec.elevation_rad
    locations = outer_bolt_locations(spec)
    for name, index in (("rear", 0), ("front", 1)):
        _, loc = locations[index]
        # Tail: from the plate's underside down to the base plane.
        underside_z = loc.position.Z - spec.plate_thickness * math.cos(e)
        tail = underside_z / math.cos(e)
        longest = spec.boom_width + spec.plate_thickness + tail
        room = min(
            head_side_room(spec, loc)
            for i, (_, loc) in enumerate(locations)
            if i % 2 == index
        )
        logger.info(
            f"Outer {name} bolts: up to {longest:.0f} mm long before the tail"
            f" reaches the base plane ({tail:.0f} mm past the nut). "
            f"{room:.0f} mm above the boom to feed them in."
        )
        if room < spec.min_bolt_feed_length:
            logger.warning(
                f"Outer {name} bolts: only {room:.0f} mm to feed them in."
            )
    logger.info("Centre yagi bolts can be any length.")


def assembly(spec: Spec, part: bd.Part | bd.Compound) -> bd.Compound:
    """Frame with boom stubs in place."""

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
    return bd.Compound(
        label="antenna_frame_assembly",
        children=[
            named(part, "frame"),
            bd.Compound(label="booms", children=booms),
        ],
    )


if __name__ == "__main__":
    spec = Spec()
    logger.info(
        f"Frame: {spec.rim_diameter:.0f} mm across, {spec.rim_z:.1f} mm "
        f"tall. Dish floor at z={spec.floor_z:.1f} mm, "
        f"{2 * spec.floor_apothem:.1f} mm across the flats. Centre bolts "
        f"along azimuth {spec.center_bolt_azimuth_deg} deg."
    )
    report_bolts(spec)

    frame_part = frame(spec)
    check_clearances(spec, frame_part)
    parts = {
        "antenna_frame": frame_part,
        "antenna_frame_assembly": show(assembly(spec, frame_part)),
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
