# (dx, dy, rotation_deg, side) of each part's COURTYARD CENTRE relative to board centre.
# +x right, +y down (KiCad).  Board: 70.0 mm circle (fits Apogee AC-74 coupler, ID 72.6 mm).
#
#   12 o'clock  power switch (edge)          NW  battery XT30 + reverse diode + LDO
#    9 o'clock  ARM plug (edge, bottom)       NE  servo 5 V buck
#    3 o'clock  Nano USB (edge, bottom)       E   Qwiic + servo bulk cap
#    6 o'clock  e-match WAGO row (bottom)     SE  servo headers
#   centre      IMU exactly on the rocket axis, baro + level shifters + SD buffer beside it
#   4x M3 mounting holes on a 45.0 x 45.0 mm square (bolt circle 63.6 mm)
HOLE = 22.5                  # 45.0 x 45.0 mm square, bolt circle 63.6 mm
NANO_X = 6.0                 # Nano pin rows sit at y = -7.62 / +7.62
WAGO_Y = 17.5                # WAGO body centre row (bottom side)
WAGO_X = [-14.25, -4.75, 4.75, 14.25]

PLACE = {
    # ================= BOTTOM SIDE (hand-soldered THT) =================
    'A1': (NANO_X, 0.0, 270, 'B'),            # Arduino Nano, USB toward +x edge
    'J5': (-25.6, 0.0, 270, 'B'),             # ARM plug, mouth at the -x edge
    # ================= MOUNTING =================
    'H1': (-HOLE, -HOLE, 0, 'F'), 'H2': (HOLE, -HOLE, 0, 'F'),
    'H3': (-HOLE, HOLE, 0, 'F'), 'H4': (HOLE, HOLE, 0, 'F'),

    # ================= TOP: centre band between the Nano rows =================
    'U3': (0.0, 0.0, 0, 'F'),                 # IMU on the rocket centreline
    'C20': (0.0, -2.55, 0, 'F'), 'C21': (0.0, 2.55, 0, 'F'),
    'U4': (-6.2, -1.6, 90, 'F'),              # barometer
    'C22': (-6.2, 2.4, 0, 'F'),
    'Q6': (6.4, -3.0, 0, 'F'), 'Q7': (6.4, 2.6, 0, 'F'),                 # I2C level shift
    'R34': (3.0, -4.0, 90, 'F'), 'R35': (3.0, 4.0, 90, 'F'),           # 3V3-side pull-ups
    'R32': (9.6, -4.3, 90, 'F'), 'R33': (9.6, -0.6, 90, 'F'),           # Nano-side pull-ups
    'JP1': (9.6, 3.2, 90, 'F'),
    'U5': (15.4, 0.0, 0, 'F'),                # SPI buffer
    'C23': (20.3, -3.6, 90, 'F'), 'R36': (20.3, 0.0, 90, 'F'), 'C24': (20.4, 3.9, 90, 'F'),
    # battery-voltage and arm-sense dividers (next to A6 / A7)
    'R1': (-15.5, -3.6, 90, 'F'), 'R2': (-13.8, -3.6, 90, 'F'), 'C3': (-12.1, -3.6, 90, 'F'),
    'R12': (-15.5, 3.0, 90, 'F'), 'R13': (-13.8, 3.0, 90, 'F'), 'C14': (-12.1, 3.0, 90, 'F'),

    # ================= TOP: north - microSD + power switch + power LED =================
    'J10': (0.0, -18.4, 0, 'F'),
    'R37': (9.4, -27.4, 90, 'F'), 'R38': (9.4, -24.4, 90, 'F'), 'R39': (9.4, -21.4, 90, 'F'),
    'SW1': (-1.0, -31.5, 180, 'F'),
    'R3': (-8.8, -30.2, 90, 'F'), 'D2': (-6.9, -30.2, 90, 'F'),

    # ================= TOP: north-west - battery input, reverse diode, hold-up, 3.3 V =================
    'J1': (-16.4, -12.0, 0, 'F'),             # XT30 battery (vertical)
    'D1': (-15.0, -18.0, 0, 'F'),
    'C1': (-13.2, -24.9, 90, 'F'),            # 220 uF hold-up
    'C2': (-9.9, -17.8, 90, 'F'),
    'U1': (-27.0, -10.5, 0, 'F'),             # AMS1117-3.3
    'C4': (-27.6, -16.8, 90, 'F'), 'C5': (-25.2, -16.8, 90, 'F'),

    # ================= TOP: north-east - servo buck (proven hand-routed geometry) =========
    'U2': (13.6, -13.0, 180, 'F'), 'C9': (14.2, -10.5, 0, 'F'), 'C8': (15.3, -15.8, 0, 'F'),
    'C6': (15.6, -17.6, 0, 'F'), 'C7': (15.6, -19.6, 0, 'F'),
    'L1': (20.4, -13.0, 0, 'F'),
    'R4': (10.8, -16.2, 270, 'F'), 'R5': (12.4, -16.2, 90, 'F'),
    'R6': (11.0, -10.25, 0, 'F'), 'R7': (9.9, -12.6, 90, 'F'),
    'C10': (25.1, -14.2, 90, 'F'), 'C11': (25.1, -10.6, 270, 'F'), 'C12': (20.4, -17.4, 180, 'F'),

    # ================= TOP: east - Qwiic, servo bulk, MISO pull-up =================
    'J11': (29.6, -6.8, 270, 'F'),     # opening faces inboard so the cable clears the coupler wall
    'C13': (28.6, 1.0, 0, 'F'),
    'R40': (23.0, -2.6, 90, 'F'),
    # ================= TOP: south-east - servo headers =================
    'J2': (20.6, 13.2, 0, 'F'), 'J3': (24.2, 13.2, 0, 'F'), 'J4': (27.8, 13.2, 0, 'F'),
    'R8': (24.5, 6.9, 90, 'F'), 'R9': (26.5, 6.9, 90, 'F'), 'R10': (28.5, 6.9, 90, 'F'),

    # ================= TOP: south - buzzer + driver, test points =================
    'BZ1': (0.0, 28.0, 0, 'F'),
    'Q5': (-9.0, 24.8, 0, 'F'), 'R31': (-12.6, 24.8, 90, 'F'), 'R30': (-12.6, 28.4, 90, 'F'),
    'D3': (-7.4, 29.0, 90, 'F'),              # flyback, right across the buzzer pins
    'TP1': (-16.4, 27.8, 0, 'F'), 'TP2': (-10.6, 31.4, 0, 'F'),
    'TP3': (8.8, 31.6, 0, 'F'), 'TP4': (12.6, 29.8, 0, 'F'), 'TP5': (16.2, 27.4, 0, 'F'),

    # ================= west - arm bleed + VPYRO cap (top, over the ARM plug) =================
    'R11': (-27.5, 0.0, 90, 'F'), 'C15': (-24.6, 0.0, 90, 'F'),
}
# WAGO lever terminals (bottom) and one identical pyro column above each (top)
for i, (j, q, rg, rpd, rs1, rs2, c) in enumerate([
        ('J6', 'Q1', 'R14', 'R15', 'R16', 'R17', 'C16'), ('J7', 'Q2', 'R18', 'R19', 'R20', 'R21', 'C17'),
        ('J8', 'Q3', 'R22', 'R23', 'R24', 'R25', 'C18'), ('J9', 'Q4', 'R26', 'R27', 'R28', 'R29', 'C19')]):
    xc = WAGO_X[3 - i]       # channel 1 east ... channel 4 west, matching Nano A0..A3 order
    PLACE[j] = (xc, WAGO_Y, 0, 'B')          # pin 2 (PYRO_N) sits at xc+1.81, pin 1 (VPYRO) at xc-1.69
    PLACE[q] = (xc + 2.6, 13.0, 270, 'F')    # drain points straight down at the PYRO_N pin
    PLACE[rg] = (xc + 2.8, 9.6, 180, 'F')    # CMD pad east, gate pad west
    PLACE[rpd] = (xc - 0.3, 9.6, 180, 'F')   # gate pad east, GND pad west
    PLACE[rs1] = (xc + 0.05, 12.7, 90, 'F')  # PYRO_N bottom, CONT top
    PLACE[rs2] = (xc - 1.55, 12.7, 270, 'F') # CONT top, GND bottom
    PLACE[c] = (xc - 3.15, 12.7, 270, 'F')   # CONT top, GND bottom
SILK = []
