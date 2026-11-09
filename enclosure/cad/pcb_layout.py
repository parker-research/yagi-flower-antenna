"""Antenna-Array-Switch-PCB (Rev 1) layout, as needed by the enclosure.

Positions were extracted from `Antenna-Array-Switch-PCB.kicad_pcb` with
KiCad's `pcbnew` Python API. They are kept in raw KiCad coordinates
(mm, +X right, +Y down) so they can be checked against the PCB editor.
Use `kicad_to_cad()` to convert to enclosure coordinates (PCB centred on
the origin, +Y up, looking down on the component side).
"""

from dataclasses import dataclass

# Board outline (Edge.Cuts rectangle), KiCad coordinates.
PCB_X_MIN, PCB_Y_MIN = 100.0, 50.0
PCB_X_MAX, PCB_Y_MAX = 198.0, 148.0
PCB_SIZE_X = PCB_X_MAX - PCB_X_MIN
PCB_SIZE_Y = PCB_Y_MAX - PCB_Y_MIN
PCB_THICKNESS = 1.6


def kicad_to_cad(x: float, y: float) -> tuple[float, float]:
    """Convert KiCad board coordinates to enclosure (centred, +Y up)."""
    return (
        x - (PCB_X_MIN + PCB_X_MAX) / 2,
        (PCB_Y_MIN + PCB_Y_MAX) / 2 - y,
    )


@dataclass(frozen=True)
class RfPort:
    """A vertical SMA jack (Amphenol 901-144) on the top of the PCB."""

    reference: str
    connector_x: float
    connector_y: float
    # Where the PCB silkscreen label sits (not used by the enclosure, whose
    # labels go directly south of the connector).
    silkscreen_x: float
    silkscreen_y: float
    # Footprint rotation (KiCad, CCW as seen from the top). Turns the
    # square SMA body.
    rotation_deg: float
    # Engraved text, if different from the port name.
    label: str | None = None


# Keyed by the PCB silkscreen label. J101/J102 share one "TEST" label.
RF_PORTS: dict[str, RfPort] = {
    "IN0": RfPort("J301", 177.50, 61.66, 183.49, 62.74, 180),
    "IN1": RfPort("J401", 154.75, 64.00, 160.50, 65.12, 180),
    "IN2": RfPort("J501", 192.81, 95.81, 192.70, 102.25, 90),
    "IN3": RfPort("J601", 107.25, 105.50, 107.36, 111.60, -90),
    "IN4": RfPort("J701", 192.70, 118.64, 190.89, 125.36, 75),
    "IN5": RfPort("J801", 106.81, 132.66, 110.07, 138.55, -60),
    "IN6": RfPort("J901", 171.20, 141.55, 177.49, 139.50, 30),
    "IN7": RfPort("J1001", 133.37, 142.31, 127.72, 140.54, -30),
    "OUT0": RfPort("J104", 173.25, 87.50, 167.96, 92.46, 45),
    "SW_OUT": RfPort("J103", 149.78, 109.40, 150.07, 115.36, 0),
    "TEST_A": RfPort("J101", 154.00, 54.50, 169.20, 53.74, -90, "TEST"),
    "TEST_B": RfPort("J102", 186.00, 54.50, 169.20, 53.74, 90, "TEST"),
}

# M3 mounting holes (H101..H105).
MOUNTING_HOLES: list[tuple[float, float]] = [
    (194.0, 54.0),
    (194.0, 144.0),
    (104.0, 144.0),
    (104.0, 97.0),
    (145.0, 54.0),
]

# 0603 LEDs: D201 status, D202..D204 switch control lines, D302..D1002 LNA
# power (one per input port, IN0..IN7).
LEDS: dict[str, tuple[float, float]] = {
    "D201": (103.05, 87.45),
    "D202": (130.25, 85.25),
    "D203": (127.25, 85.16),
    "D204": (124.25, 85.16),
    "D302": (183.10, 75.75),
    "D402": (160.35, 78.09),
    "D502": (178.72, 101.41),
    "D602": (121.34, 99.90),
    "D702": (177.65, 120.40),
    "D802": (116.21, 120.77),
    "D902": (159.31, 132.15),
    "D1002": (135.57, 127.31),
}

# LED that indicates each port's state (the LNA-power LED of each input).
# Ports not listed here have no LED of their own.
PORT_LEDS: dict[str, str] = {
    "IN0": "D302",
    "IN1": "D402",
    "IN2": "D502",
    "IN3": "D602",
    "IN4": "D702",
    "IN5": "D802",
    "IN6": "D902",
    "IN7": "D1002",
}

# RF shield can J201 (Wuerth 36103305, 30x30 mm, centred at 116.75, 66.75),
# which also covers the socketed RP2040-Zero. (x_min, y_min, x_max, y_max).
TALL_REGION = (101.75, 51.75, 131.75, 81.75)

# RP2040-Zero USB-C receptacle: centre X, and it faces -Y (the y=50 edge).
USB_CENTER_X = 115.09
