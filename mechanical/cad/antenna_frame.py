"""3D-printable frame that holds the six yagi antennas.

Shape: a bowl, open at the top. Its lower part is a pentagonal frustum whose
five flat outer faces slope at the outer antennas' elevation (40 degrees),
and it stands on a short vertical skirt. The rim is trimmed round to
`Spec.rim_diameter`. A square socket in the middle holds the vertical yagi.

Mounting (all M5, with captive nuts):
    - Outer yagis (5x): The boom lies flat against the underside of a
        sloped face, pointing outwards and up. Two bolts go up through the
        boom and the wall into hex nut pockets on the inside of the bowl.
        Their tails stick out into the open bowl.
    - Centre yagi (1x): The boom stands in the socket. Two horizontal bolts
        go through the socket and the boom into hex nut pockets on the far
        side. The bolt line runs through holes in the bowl wall on both
        sides, aimed between the outer yagis, so the bolts can be any length.

The floor has holes for wood screws into a plywood base. Fit those before
the antennas: the bolt tails pass over them.

Z is up, with the underside of the floor at z=0. Outer yagi `k` points along
azimuth `k * 360 / outer_antenna_count` degrees (yagi 0 along +X).
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
    # How far an outer boom extends behind its rear (lower) bolt, towards
    # the skirt. The boom's rear end can reach the bottom of the face.
    boom_rear_overhang: float = 15.0

    # Bowl.
    rim_diameter: float = 210.0
    wall_thickness: float = 8.0  # Sloped faces (perpendicular to them).
    rim_wall_thickness: float = 8.0  # Where the rim is trimmed round.
    floor_thickness: float = 6.0
    # Flat face kept clear of the round trim, either side of the boom.
    face_side_margin: float = 5.0
    # Bolt centre to the edge of a face, on the outside.
    bolt_edge_margin: float = 8.0
    # Nut pocket to the top edge of a face, on the inside.
    nut_edge_margin: float = 2.0

    # Outer bolts are fed in from under the boom, so the skirt is made tall
    # enough that a bolt this long (under the head, plus the head) fits
    # between the boom and the plywood base. Also keeps the booms' rear
    # ends `base_clearance` off the base.
    bolt_insertion_length: float = 45.0
    base_clearance: float = 2.0

    # M5 hardware. Bolts go through a clearance hole, into a hex nut pocket.
    bolt_clearance_diameter: float = 5.5
    # Centre yagi bolts: the hole in the bowl wall the head passes through.
    bolt_head_clearance_diameter: float = 10.0
    nut_width_across_flats: float = 8.0
    nut_thickness: float = 4.0
    nut_clearance: float = 0.3  # Added across the flats, for a press fit.
    nut_pocket_depth: float = 4.5  # Deeper than the nut: it sits recessed.
    # Warn if an outer bolt's tail can't reach this far into the bowl
    # (past the inside of the wall) before hitting the centre yagi/socket.
    min_bolt_tail_length: float = 40.0

    # Centre socket.
    socket_wall_thickness: float = 7.0
    socket_fit_clearance: float = 0.3  # Per side, around the boom.
    center_bolt_floor_margin: float = 15.0  # Lower bolt above the floor.
    center_bolt_top_margin: float = 12.0  # Upper bolt below socket top.

    # Floor holes for wood screws into a plywood base (e.g. #8 or M4).
    floor_hole_count: int = 10
    floor_hole_ring_diameter: float = 52.0
    floor_hole_diameter: float = 4.5
    floor_screw_head_diameter: float = 9.0  # For clearance checks only.

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
        assert self.nut_pocket_depth <= self.wall_thickness - 2, (
            "Less than 2 mm of wall left under the outer nut pockets."
        )
        assert self.nut_pocket_depth <= self.socket_wall_thickness - 2, (
            "Less than 2 mm of socket wall left under the nut pockets."
        )
        assert self.face_top_apothem < self.rim_diameter / 2
        assert self.face_bottom_apothem > self.socket_outer_size / 2, (
            "Bowl is too small for the centre socket."
        )

        # The rear nut pocket must sit on the sloped inside face, above
        # where it meets the skirt.
        e = self.elevation_rad
        rear_nut_from_bottom = (
            self.rear_bolt_slant + self.wall_thickness / math.tan(e)
        )
        assert (
            rear_nut_from_bottom
            >= self.nut_pocket_radius + self.nut_edge_margin
        ), "Rear nut pocket runs into the skirt."

        # Floor screws: inside the bowl, and clear of the socket.
        head_r = self.floor_screw_head_diameter / 2
        assert (
            self.floor_hole_ring_diameter / 2 + head_r
            <= self.skirt_inner_apothem - 1
        ), "Floor screw heads run into the bowl wall."
        for x, y in floor_hole_positions(self):
            gap = distance_to_socket(self, x, y) - head_r
            assert gap >= 1, f"Floor screw at ({x:.1f}, {y:.1f}) hits socket."

        # Centre bolt holes (head size, on the head side) pass the outer
        # booms. Booms are never closer to the axis than the face bottom.
        phi = self.center_bolt_azimuth_deg
        sep = min(
            angle_between(end, face)
            for end in (phi, phi + 180)
            for face in self.outer_azimuths_deg
        )
        offset = self.face_bottom_apothem * math.sin(math.radians(sep))
        assert (
            offset
            >= self.boom_width / 2 + self.bolt_head_clearance_diameter / 2
        ), "Centre yagi bolt line runs into an outer boom."

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
    def nut_pocket_radius(self) -> float:
        """Circumradius (centre to corner) of the hex nut pocket."""
        flats = self.nut_width_across_flats + self.nut_clearance
        return flats / 2 / math.cos(math.radians(30))

    # Positions along a sloped face are "slant" distances, measured up the
    # face from its bottom edge (where it meets the skirt).
    @property
    def rear_bolt_slant(self) -> float:
        """Slant position of the rear (lower) outer bolt."""
        return self.boom_rear_overhang

    @property
    def front_bolt_slant(self) -> float:
        """Slant position of the front (upper) outer bolt."""
        return self.rear_bolt_slant + self.bolt_spacing

    @property
    def face_slant_length(self) -> float:
        """Length of a sloped face, from the skirt to the rim."""
        # The bolt axis meets the inside face this much closer to the rim
        # (both faces end at the rim's top), so the nut pocket needs more.
        inside_shift = self.wall_thickness / math.tan(self.elevation_rad)
        nut_margin = (
            self.nut_pocket_radius + self.nut_edge_margin + inside_shift
        )
        return self.front_bolt_slant + max(self.bolt_edge_margin, nut_margin)

    @property
    def face_top_apothem(self) -> float:
        """Outside face's distance from the axis, at the rim.

        Small enough that the round trim leaves the face flat for
        `face_side_margin` either side of the boom.
        """
        half_width = self.boom_width / 2 + self.face_side_margin
        return math.sqrt((self.rim_diameter / 2) ** 2 - half_width**2)

    @property
    def face_bottom_apothem(self) -> float:
        """Outside face's distance from the axis, at the skirt."""
        run = self.face_slant_length * math.cos(self.elevation_rad)
        return self.face_top_apothem - run

    @property
    def skirt_height(self) -> float:
        """Z where the sloped faces start (top of the vertical skirt)."""
        e = self.elevation_rad
        w_drop = self.boom_width * math.cos(e)
        rear_end_rise = (
            self.rear_bolt_slant - self.boom_rear_overhang
        ) * math.sin(e)
        # The boom's lowest point is its rear end's outer edge.
        for_clearance = self.base_clearance + w_drop - rear_end_rise
        # Room to feed the rear bolt in along its axis, from the boom's
        # outer face down to the base.
        rear_bolt_rise = self.rear_bolt_slant * math.sin(e)
        for_insertion = (
            self.bolt_insertion_length * math.cos(e) + w_drop - rear_bolt_rise
        )
        return max(for_clearance, for_insertion, self.floor_thickness)

    @property
    def rim_z(self) -> float:
        """Z of the top of the rim."""
        return self.skirt_height + self.face_slant_length * math.sin(
            self.elevation_rad
        )

    def outer_apothem_at(self, z: float) -> float:
        """Outside face's distance from the axis at height z (sloped part)."""
        return self.face_bottom_apothem + (z - self.skirt_height) / math.tan(
            self.elevation_rad
        )

    def inner_apothem_at(self, z: float) -> float:
        """Inside face's distance from the axis at height z (sloped part)."""
        return self.outer_apothem_at(z) - self.wall_thickness / math.sin(
            self.elevation_rad
        )

    @property
    def skirt_inner_apothem(self) -> float:
        """Inside of the skirt, flush with the sloped inside faces above."""
        return self.inner_apothem_at(self.skirt_height)

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
        lower = self.floor_thickness + self.center_bolt_floor_margin
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


@dataclass
class FaceFrame:
    """Directions for one outer yagi's sloped face."""

    radial: Vec3  # Horizontal, outwards.
    tangent: Vec3  # Horizontal, along the face.
    up_slope: Vec3  # Along the boom, outwards and up.
    outward_normal: Vec3  # Out of the face, outwards and down.


def face_frame(spec: Spec, azimuth_deg: float) -> FaceFrame:
    """Directions for the sloped face at an azimuth."""
    a = math.radians(azimuth_deg)
    e = spec.elevation_rad
    r = (math.cos(a), math.sin(a), 0.0)
    return FaceFrame(
        radial=r,
        tangent=(-math.sin(a), math.cos(a), 0.0),
        up_slope=(math.cos(e) * r[0], math.cos(e) * r[1], math.sin(e)),
        outward_normal=(math.sin(e) * r[0], math.sin(e) * r[1], -math.cos(e)),
    )


def face_point(spec: Spec, azimuth_deg: float, slant: float) -> Vec3:
    """Point on the centreline of an outside face, `slant` up from bottom."""
    f = face_frame(spec, azimuth_deg)
    bottom = add((0, 0, spec.skirt_height), f.radial, spec.face_bottom_apothem)
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


def floor_hole_positions(spec: Spec) -> list[tuple[float, float]]:
    """Wood screw hole centres in the floor."""
    r = spec.floor_hole_ring_diameter / 2
    n = spec.floor_hole_count
    return [
        (r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]


def bowl(spec: Spec) -> bd.Part:
    """Hollow bowl: skirt, sloped faces, floor, round-trimmed rim."""
    a0 = spec.face_bottom_apothem
    z_skirt, z_rim = spec.skirt_height, spec.rim_z
    r_rim = spec.rim_diameter / 2

    p = polygon_frustum(spec, a0, a0, 0, z_skirt)
    p += polygon_frustum(spec, a0, spec.face_top_apothem, z_skirt, z_rim)
    p &= bd.Cylinder(
        r_rim, z_rim, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )

    # Cavity: vertical inside the skirt, then following the sloped faces
    # (continued above the rim so the cut goes right through).
    z_top = z_rim + 10
    a_in = spec.skirt_inner_apothem
    cavity = polygon_frustum(
        spec, a_in, a_in, spec.floor_thickness, z_skirt + EPS
    )
    cavity += polygon_frustum(
        spec, a_in, spec.inner_apothem_at(z_top), z_skirt, z_top
    )
    cavity &= bd.Pos(0, 0, spec.floor_thickness - EPS) * bd.Cylinder(
        r_rim - spec.rim_wall_thickness,
        z_top,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    p -= cavity
    assert isinstance(p, bd.Part)
    return p


def outer_bolt_locations(spec: Spec) -> list[tuple[float, bd.Location]]:
    """Each outer bolt as (azimuth, location on the outside face).

    Local Z points along the bolt, into the wall (inwards and up).
    """
    result: list[tuple[float, bd.Location]] = []
    for azimuth in spec.outer_azimuths_deg:
        f = face_frame(spec, azimuth)
        inward = add((0, 0, 0), f.outward_normal, -1)
        for slant in (spec.rear_bolt_slant, spec.front_bolt_slant):
            origin = face_point(spec, azimuth, slant)
            result.append((azimuth, along_axis(origin, inward, f.tangent)))
    return result


def center_socket(spec: Spec) -> bd.Part:
    """Square socket for the vertical yagi's boom, standing on the floor."""
    z0, z1 = spec.floor_thickness - EPS, spec.socket_top_z
    outer, inner = spec.socket_outer_size, spec.socket_inner_size
    align = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    p = bd.Box(outer, outer, z1 - z0, align=align)
    p -= bd.Pos(0, 0, spec.floor_thickness - z0) * bd.Box(
        inner, inner, z1 - z0, align=align
    )
    p = socket_location(spec, z0) * p
    assert isinstance(p, bd.Part)
    return p


def frame(spec: Spec) -> bd.Part | bd.Compound:
    """Make the whole antenna frame (one print)."""
    p = bowl(spec) + center_socket(spec)

    # Outer yagis: bolt holes through the wall (open on both sides, so the
    # tail runs free into the bowl), and nut pockets on the inside.
    t = spec.wall_thickness
    for _, loc in outer_bolt_locations(spec):
        p -= cylinder_along(loc, spec.bolt_clearance_diameter, -50, t + 5)
        p -= hex_along(spec, loc, t - spec.nut_pocket_depth, t + 5)

    # Centre yagi: horizontal bolts. The line is cut right through the
    # bowl, with a head-sized hole on the head side.
    far = spec.rim_diameter
    half = spec.socket_outer_size / 2
    for z in spec.center_bolt_z:
        loc = socket_location(spec, z) * bd.Rot(0, 90, 0)  # Local Z -> X.
        p -= cylinder_along(loc, spec.bolt_clearance_diameter, -far, far)
        p -= cylinder_along(
            loc, spec.bolt_head_clearance_diameter, -far, -half
        )
        p -= hex_along(spec, loc, half - spec.nut_pocket_depth, half + 5)

    # Floor holes for wood screws into a plywood base.
    for x, y in floor_hole_positions(spec):
        p -= bd.Pos(x, y, -EPS) * bd.Cylinder(
            spec.floor_hole_diameter / 2,
            spec.floor_thickness + 2 * EPS,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )

    assert isinstance(p, bd.Part | bd.Compound)
    return p


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


def outer_bolt_tail_room(spec: Spec, loc: bd.Location) -> float:
    """How far an outer bolt's tail can go past the inside of the wall.

    Limited by the centre socket and the centre yagi's boom above it.
    """
    # Work in the socket's frame, where both obstacles are axis-aligned.
    to_socket = socket_location(spec).inverse() * loc
    origin = to_socket.position
    axis = to_socket.z_axis.direction
    o: Vec3 = (origin.X, origin.Y, origin.Z)
    d: Vec3 = (axis.X, axis.Y, axis.Z)

    half_s, half_b = spec.socket_outer_size / 2, spec.boom_width / 2
    floor = spec.floor_thickness
    hits = [
        ray_box_distance(
            o,
            d,
            (-half_s, -half_s, floor),
            (half_s, half_s, spec.socket_top_z),
        ),
        ray_box_distance(
            o, d, (-half_b, -half_b, floor), (half_b, half_b, 1e6)
        ),
    ]
    reach = min((h for h in hits if h is not None), default=math.inf)
    return reach - spec.wall_thickness


def report_bolts(spec: Spec) -> None:
    """Log bolt lengths that fit, and warn about short tail room."""
    rear_room = min(
        outer_bolt_tail_room(spec, loc)
        for i, (_, loc) in enumerate(outer_bolt_locations(spec))
        if i % 2 == 0
    )
    front_room = min(
        outer_bolt_tail_room(spec, loc)
        for i, (_, loc) in enumerate(outer_bolt_locations(spec))
        if i % 2 == 1
    )
    for name, room in (("rear", rear_room), ("front", front_room)):
        # Under the head: through the boom and wall, then the tail room.
        longest = spec.boom_width + spec.wall_thickness + room
        logger.info(
            f"Outer {name} bolts: tail has {room:.0f} mm of room past the "
            f"wall (bolts up to {longest:.0f} mm long)."
        )
        if room < spec.min_bolt_tail_length:
            logger.warning(f"Outer {name} bolt tails hit the centre yagi.")
    logger.info(
        f"Outer bolts fit from under the boom up to "
        f"{spec.bolt_insertion_length:.0f} mm long (incl. head). Centre "
        "yagi bolts can be any length."
    )


def boom_placeholders(spec: Spec) -> list[bd.Part]:
    """Square booms in their mounted positions, for the assembly view."""
    w, length = spec.boom_width, spec.boom_display_length
    booms: list[bd.Part] = []
    for azimuth in spec.outer_azimuths_deg:
        f = face_frame(spec, azimuth)
        rear_end = spec.rear_bolt_slant - spec.boom_rear_overhang
        centre = add(
            face_point(spec, azimuth, rear_end), f.outward_normal, w / 2
        )
        loc = bd.Location(
            bd.Plane(origin=centre, x_dir=f.up_slope, z_dir=f.outward_normal)
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
        socket_location(spec, spec.floor_thickness)
        * bd.Box(
            w,
            w,
            length,
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
    )
    return booms


def assembly(spec: Spec) -> bd.Compound:
    """Frame with boom stubs in place."""

    def named(
        part: bd.Part | bd.Compound, label: str, color: str | None
    ) -> bd.Part:
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
            named(frame(spec), "frame", color=None),
            bd.Compound(label="booms", children=booms),
        ],
    )


if __name__ == "__main__":
    spec = Spec()
    logger.info(
        f"Bowl: {spec.rim_diameter:.0f} mm across, {spec.rim_z:.1f} mm "
        f"tall (skirt {spec.skirt_height:.1f} mm). Floor: "
        f"{2 * spec.skirt_inner_apothem:.1f} mm across the flats, inside. "
        f"Centre bolts along azimuth {spec.center_bolt_azimuth_deg} deg."
    )
    report_bolts(spec)

    parts = {
        "antenna_frame": frame(spec),
        "antenna_frame_assembly": show(assembly(spec)),
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
