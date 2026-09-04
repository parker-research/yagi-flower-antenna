# yagi-flower-antenna
A group of UHF yagi antennas, arranged in a flower pattern and connected with a SP6T RF switch, should enable coarse beam direction control (like an antenna rotator, but solid-state)

## Status

In development. Expected completion: 2026-11-01.

## Parts

1. Antennas (6x yagi antennas, approx. 7 dBi each)
2. Structural mount for antennas
3. SP6T RF switch PCB
  - Microcontroller
  - SP6T RF switch IC
  - SMA ports to each antenna + common
4. Software for PCB microcontroller, masquerading as an antenna rotator
5. Cables to each antenna

## Why?

Satellite tracking works best with a directional antenna: less ambient noise/interference, and higher gain. Omnidirectional antennas are about as much work to build as this project anyway.

However, mechanical antenna rotators are expensive and wear out over time. They require zeroing/calibration, especially after power outages. There are no high-quality open source/DIY designs available. Cheap rotators (e.g., AntRunner) fail in weatherproofing.

This project aims to solve these problems by providing a low-cost, high-quality, open source/DIY, solid-state replacement for a traditional mechanical antenna rotator.

Consider an antenna being deployed in a remote location, like the arctic. As far as I can tell, this yagi flower antenna is ideal for such a deployment.

## Features

- Downlink-only
- Presents itself as a traditional antenna rotator, ensuring compatibility with existing antenna rotator software (e.g., SatNOGS Client, GPredict)
- Solid-state (no moving parts) adds reliability and durability for harsh environments
