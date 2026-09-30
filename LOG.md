# Engineering Log

Newest entries go at the top. Each entry covers one work session: what changed, why it changed, and what comes next. There's a blank template at the bottom of this file to copy for new entries.

---

## 2026-09-29: Firmware, 3D simulator and final PCB fixes

**Flight computer v2.1**
- A final review turned up one real problem. The I²C pull-up jumper (JP1) was shipping open, which would have required a solder bridge by hand. I tied it to the Nano's 5 V rail in copper, so the board now needs no hand soldering at all.
- Re-verified the Nano pin map against the KiCad library, compared the schematic to the PCB pad by pad (282 of 282 matched), and confirmed the design rule check and electrical rules check were both clean. Also double-checked the battery connector polarity (the chamfered side of an XT30 is negative) and the power switch wiring.
- Switched the JLCPCB order to full assembly: all surface-mount parts, the through-hole connectors and the Nano sockets, on both sides, with the edge rails removed. The Nano plugs into its sockets with the USB port facing the "< USB" arrow.

**Firmware (`firmware/RocketFC/RocketFC.ino`)**
- The flight states are PAD, BOOST, COAST, then either CHUTE or WAIT_IGNITE, then LAND_BURN and finally LANDED.
- TVC uses a gyro-integrated quaternion for attitude and a PID loop on tilt, with starting gains of Kp 0.30, Ki 0.05 and Kd 0.08 (degrees of gimbal per degree of tilt).
- Liftoff is detected at 1.5 g sustained for 50 ms, and the rocket must then climb 3 m within 2.5 s. If it doesn't, the computer goes back to the pad state, so bumping the rocket on the pad can't trigger the chute.
- An F15 can't be throttled, so the landing motor fires when a burn started at that moment would end right at the ground. If the apogee makes a soft landing impossible, the computer deploys the parachute instead.
- It fits on the Nano: 30,370 of 30,720 bytes of flash and 1,427 of 2,048 bytes of RAM.
- I ran the actual firmware against simulated sensors. The chute flight worked, a bump on the pad was correctly ignored, and the landing sequence worked.

**Chute ejector**
- A spring-loaded piston (22 mm OD spring, 100 mm free length) is held by a T-shaped stem that sits in a latch cup on an MG90S servo. Turning the servo 90° lines up the slots and releases it.

**3D simulator (`simulation/matlab/rocketSim3D.m`)**
- Lets me adjust the PID gains, the landing delay after apogee, the rocket's mass, CP/CG position, wind and more. An auto-find button searches for the softest landing.
- The best delay came out to about 1.76 s at 1.0 kg, and the usable window is only about ±0.01 s wide. The rocket also tilts 16 to 27° while coasting and falling, since there are no fins and the TVC is off, but the landing burn straightens it out in about 0.4 s.

**Next:** The boards should ship around October 8. Then comes bench testing.

---

## 2026-09-28: Flight computer v1 to v2, and the avionics bay

- Designed RocketFC in KiCad around an Arduino Nano and a 2S LiPo, with 4 pyro channels, 3 servo outputs, an IMU, a barometer and a microSD card.
- For v2, I shrank it to a 70 mm round board so it fits inside the Apogee 3" tube with room for the wall thickness, and moved the mounting holes to a standard 45 × 45 mm M3 pattern.
- Designed the avionics bay in Onshape and CadQuery. An aft ring and a forward bulkhead are joined by 4 M3 tie rods that pass through the PCB's mounting holes. 8 radial M3 heat-set inserts take screws through the tube wall, and there's a pocket for a 2S 1000 mAh battery.
- Fixed the geometry problems that caused Onshape import errors (curves, seam placement and thin walls).

---

## Template

```
## YYYY-MM-DD: Title

**What I did**
-

**What I learned or what went wrong**
-

**Data and photos** (images go in docs/images/, flight logs in data/)
-

**Next**
-
```
