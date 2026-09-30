# Firmware

`RocketFC/RocketFC.ino` builds in the Arduino IDE with the board set to "Arduino Nano" (ATmega328P). It only uses the built-in Wire, SPI, SD and Servo libraries.

Set `FLIGHT_MODE` near the top of the file, and fly the chute test first. For bench testing, open the Serial Monitor at 115200 baud with the line ending set to "Newline". The available commands are:

| Command | What it does |
|---|---|
| `s` | Prints status: sensors, battery, arm plug, continuity |
| `sweep` | Moves each TVC servo through its full range |
| `tvc` | Live TVC test, where the servos respond as you tilt the rocket |
| `open` / `lock` | Opens or locks the chute latch |
| `beep` | Tests the buzzer |
| `fire1` to `fire4` | Fires a pyro channel (only works with the ARM plug in) |

Each flight is logged to a new `FLTnn.CSV` file on the SD card.
