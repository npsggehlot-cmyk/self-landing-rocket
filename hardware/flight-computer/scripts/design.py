# Single source of truth for the flight computer netlist.
# Each part: ref, lib_id, value, footprint, pins {pin_number: net}, extra fields, schematic group
# Nets named in CAPS. 'NC' = no connect.

PARTS = []
def P(ref, lib, value, fp, pins, group, mpn='', lcsc='', unit=None, note=''):
    PARTS.append(dict(ref=ref, lib=lib, value=value, fp=fp, pins=pins, group=group,
                      mpn=mpn, lcsc=lcsc, unit=unit, note=note))

R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'

def R(ref, val, a, b, group, mpn=''):
    P(ref, 'Device:R', val, R0603, {'1': a, '2': b}, group, mpn=mpn or f'0603 1% {val}')
def C(ref, val, a, b, group, fp=C0603, mpn=''):
    P(ref, 'Device:C', val, fp, {'1': a, '2': b}, group, mpn=mpn or val)

# ---------------- POWER INPUT ----------------
P('J1', 'Connector:Screw_Terminal_01x02', 'BATTERY 2S (XT30 male, vertical)',
  'Connector_AMASS:AMASS_XT30UPB-M_1x02_P5.0mm_Vertical',
  {'1': 'GND', '2': 'VBAT'}, 'power', mpn='AMASS XT30UPB-M')
P('D1', 'Diode:SS34', 'SS34', 'Diode_SMD:D_SMA', {'1': 'VBAT_D', '2': 'VBAT'}, 'power',
  mpn='SS34 (40V 3A Schottky)', lcsc='C8678')
P('SW1', 'Switch:SW_DPDT_x2', 'POWER', 'Button_Switch_THT:SW_CK_JS202011AQN_DPDT_Angled',
  {'1': 'NC', '2': 'VBAT_D', '3': 'VLOGIC'}, 'power', mpn='C&K JS202011AQN', unit=1)
P('SW1', 'Switch:SW_DPDT_x2', 'POWER', 'Button_Switch_THT:SW_CK_JS202011AQN_DPDT_Angled',
  {'4': 'VLOGIC', '5': 'VBAT_D', '6': 'NC'}, 'power', mpn='C&K JS202011AQN', unit=2)
P('C1', 'Device:C_Polarized', '220uF 16V', 'Capacitor_SMD:CP_Elec_6.3x7.7',
  {'1': 'VLOGIC', '2': 'GND'}, 'power', mpn='Panasonic EEE-FK1C221P 220uF 16V (brown-out hold-up)')
C('C2', '10uF 25V', 'VLOGIC', 'GND', 'power', fp=C0805)
R('R1', '100k', 'VBAT', 'VBAT_SENSE', 'power')
R('R2', '33k', 'VBAT_SENSE', 'GND', 'power')
C('C3', '10nF', 'VBAT_SENSE', 'GND', 'power')

# 3.3 V LDO for sensors / SD / level shifting
P('U1', 'Regulator_Linear:AMS1117-3.3', 'AMS1117-3.3', 'Package_TO_SOT_SMD:SOT-223-3_TabPin2',
  {'1': 'GND', '2': '+3V3', '3': 'VLOGIC'}, 'power', mpn='AMS1117-3.3', lcsc='C6186')
C('C4', '22uF 10V', '+3V3', 'GND', 'power', fp=C0805)
C('C5', '100nF', '+3V3', 'GND', 'power')
R('R3', '1k', '+3V3', 'LED_PWR', 'power')
P('D2', 'Device:LED', 'RED', 'LED_SMD:LED_0603_1608Metric', {'1': 'GND', '2': 'LED_PWR'}, 'power',
  mpn='KT-0603R red LED', lcsc='C2286')

# ---------------- SERVO 5 V BUCK (independent of logic) ----------------
P('U2', 'Regulator_Switching:TPS563200', 'TPS563200', 'Package_TO_SOT_SMD:SOT-23-6',
  {'1': 'GND', '2': 'BUCK_SW', '3': 'VBAT', '4': 'BUCK_FB', '5': 'BUCK_EN', '6': 'BUCK_BST'},
  'servo', mpn='TI TPS563200DDCR')
C('C6', '10uF 25V', 'VBAT', 'GND', 'servo', fp=C0805)
C('C7', '10uF 25V', 'VBAT', 'GND', 'servo', fp=C0805)
C('C8', '100nF', 'VBAT', 'GND', 'servo')
C('C9', '100nF', 'BUCK_BST', 'BUCK_SW', 'servo')
P('L1', 'Device:L', '2.2uH', 'Inductor_SMD:L_Bourns_SRN6045TA', {'1': 'BUCK_SW', '2': 'VSERVO'}, 'servo',
  mpn='Bourns SRN6045TA-2R2Y (2.2uH, 6A)', lcsc='C1332316')
R('R4', '100k', 'VSERVO', 'BUCK_FB', 'servo')
R('R5', '18k', 'BUCK_FB', 'GND', 'servo')
R('R6', '100k', 'VLOGIC', 'BUCK_EN', 'servo')
R('R7', '100k', 'BUCK_EN', 'GND', 'servo')
C('C10', '22uF 10V', 'VSERVO', 'GND', 'servo', fp=C0805)
C('C11', '22uF 10V', 'VSERVO', 'GND', 'servo', fp=C0805)
C('C12', '22uF 10V', 'VSERVO', 'GND', 'servo', fp=C0805)
P('C13', 'Device:C_Polarized', '220uF 16V', 'Capacitor_SMD:CP_Elec_6.3x7.7',
  {'1': 'VSERVO', '2': 'GND'}, 'servo', mpn='Panasonic EEE-FK1C221P 220uF 16V (servo bulk)')

for i, (sig, pin) in enumerate([('SERVO_X', 'D3'), ('SERVO_Y', 'D5'), ('SERVO_AUX', 'D7')]):
    n = i + 1
    R(f'R{7+n}', '220', f'{sig}', f'{sig}_OUT', 'servo')
    P(f'J{1+n}', 'Connector_Generic:Conn_01x03', ['SERVO X (TVC)', 'SERVO Y (TVC)', 'SERVO AUX'][i],
      'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
      {'1': f'{sig}_OUT', '2': 'VSERVO', '3': 'GND'}, 'servo', mpn='2.54mm 1x3 male header')

# ---------------- MCU ----------------
nano = {'1': 'NC', '2': 'NC', '3': 'NC', '4': 'GND', '5': 'PYRO1_CMD', '6': 'SERVO_X', '7': 'PYRO2_CMD',
        '8': 'SERVO_Y', '9': 'PYRO3_CMD', '10': 'SERVO_AUX', '11': 'PYRO4_CMD', '12': 'BUZZER_CMD',
        '13': 'SD_CS_5V', '14': 'MOSI_5V', '15': 'MISO', '16': 'SCK_5V', '17': 'NC', '18': 'NC',
        '19': 'CONT1', '20': 'CONT2', '21': 'CONT3', '22': 'CONT4', '23': 'SDA_H', '24': 'SCL_H',
        '25': 'VBAT_SENSE', '26': 'ARM_SENSE', '27': 'NANO_5V', '28': 'NC', '29': 'GND', '30': 'VLOGIC'}
P('A1', 'MCU_Module:Arduino_Nano_v3.x', 'Arduino Nano / Nano ESP32 (socketed)', 'Module:Arduino_Nano',
  nano, 'mcu', mpn='2x 1x15 2.54mm female header (socket)')

# ---------------- PYRO CHANNELS ----------------
PYRO_NAMES = ['ASCENT MOTOR', 'LANDING MOTOR', 'LEG BURN WIRE', 'PARACHUTE']
R('R11', '47k', 'VLOGIC', 'VPYRO', 'pyro')        # continuity bleed (<0.2 mA, far below no-fire)
R('R12', '100k', 'VPYRO', 'ARM_SENSE', 'pyro')
R('R13', '33k', 'ARM_SENSE', 'GND', 'pyro')
C('C14', '10nF', 'ARM_SENSE', 'GND', 'pyro')
P('J5', 'Connector:Screw_Terminal_01x02', 'ARM PLUG (XT30 female)',
  'Connector_AMASS:AMASS_XT30PW-F_1x02_P2.50mm_Horizontal',
  {'1': 'VPYRO', '2': 'VBAT'}, 'pyro', mpn='AMASS XT30PW-F')
C('C15', '10uF 25V', 'VPYRO', 'GND', 'pyro', fp=C0805)
rn = 14; cn = 16
for i in range(4):
    n = i + 1
    P(f'Q{n}', 'Transistor_FET:AO3400A', 'AO3400A', 'Package_TO_SOT_SMD:SOT-23',
      {'1': f'PYRO{n}_G', '2': 'GND', '3': f'PYRO{n}_N'}, 'pyro', mpn='AO3400A', lcsc='C20917')
    R(f'R{rn}', '100', f'PYRO{n}_CMD', f'PYRO{n}_G', 'pyro'); rn += 1
    R(f'R{rn}', '100k', f'PYRO{n}_G', 'GND', 'pyro'); rn += 1          # hold OFF during boot/reset
    R(f'R{rn}', '100k', f'PYRO{n}_N', f'CONT{n}', 'pyro'); rn += 1     # continuity / burn-through sense
    R(f'R{rn}', '33k', f'CONT{n}', 'GND', 'pyro'); rn += 1
    C(f'C{cn}', '10nF', f'CONT{n}', 'GND', 'pyro'); cn += 1
    P(f'J{5+n}', 'Connector:Screw_Terminal_01x02', f'P{n} {PYRO_NAMES[i]}',
      'TerminalBlock_WAGO_local:TerminalBlock_WAGO_2601-3102_1x02_P3.50mm_Vertical',
      {'1': 'VPYRO', '2': f'PYRO{n}_N'}, 'pyro', mpn='WAGO 2601-3102 (lever)', lcsc='C20252913')
# rn is now 30, cn is now 20

# ---------------- BUZZER ----------------
P('Q5', 'Transistor_FET:AO3400A', 'AO3400A', 'Package_TO_SOT_SMD:SOT-23',
  {'1': 'BUZ_G', '2': 'GND', '3': 'BUZ_N'}, 'io', mpn='AO3400A', lcsc='C20917')
R('R30', '100', 'BUZZER_CMD', 'BUZ_G', 'io')
R('R31', '100k', 'BUZ_G', 'GND', 'io')
P('BZ1', 'Device:Buzzer', 'CMT-8504 5V 100dB', 'Buzzer_Beeper:MagneticBuzzer_CUI_CMT-8504-100-SMT',
  {'1': 'VSERVO', '2': 'BUZ_N'}, 'io',
  mpn='Same Sky (CUI) CMT-8504-100-SMT-TR magnetic transducer: drive with tone(D9, 4000)')
P('D3', 'Diode:1N4148W', '1N4148W', 'Diode_SMD:D_SOD-123', {'1': 'VSERVO', '2': 'BUZ_N'}, 'io',
  mpn='1N4148W', lcsc='C81598')

# ---------------- I2C LEVEL SHIFT + SENSORS ----------------
P('Q6', 'Transistor_FET:BSS138', 'BSS138', 'Package_TO_SOT_SMD:SOT-23',
  {'1': '+3V3', '2': 'SDA', '3': 'SDA_H'}, 'sensors', mpn='BSS138')
P('Q7', 'Transistor_FET:BSS138', 'BSS138', 'Package_TO_SOT_SMD:SOT-23',
  {'1': '+3V3', '2': 'SCL', '3': 'SCL_H'}, 'sensors', mpn='BSS138')
R('R32', '4.7k', 'SDA_H', 'NANO_5V', 'sensors')
R('R33', '4.7k', 'SCL_H', 'NANO_5V', 'sensors')
# Nano-side I2C pull-ups: hard-wired to the Nano's 5V (classic ATmega328P Nano wants VIH >= 3.5V on SDA/SCL).
# JP1 ships with 2-3 joined by a copper trace (no soldering). For a Nano ESP32: cut the 2-3 trace, bridge 1-2.
P('JP1', 'Jumper:SolderJumper_3_Open', 'I2C PULLUP 5V (2-3 joined)', 'Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm',
  {'1': '+3V3', '2': 'NANO_5V', '3': 'NANO_5V'}, 'sensors', mpn='solder jumper (no part)')
R('R34', '4.7k', 'SDA', '+3V3', 'sensors')
R('R35', '4.7k', 'SCL', '+3V3', 'sensors')
P('U3', 'Sensor_Motion:LSM6DSL', 'LSM6DSO32', 'Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y',
  {'1': 'GND', '2': 'GND', '3': 'GND', '4': 'NC', '5': '+3V3', '6': 'GND', '7': 'GND', '8': '+3V3',
   '9': 'NC', '10': 'NC', '11': 'NC', '12': '+3V3', '13': 'SCL', '14': 'SDA'}, 'sensors',
  mpn='ST LSM6DSO32TR (+/-32g, 2000dps; pin-compatible with LSM6DSL)')
C('C20', '100nF', '+3V3', 'GND', 'sensors')
C('C21', '100nF', '+3V3', 'GND', 'sensors')
P('U4', 'Sensor_Pressure:MS5607-02BA', 'MS5607-02BA03', 'Package_LGA:LGA-8_3x5mm_P1.25mm',
  {'1': '+3V3', '2': '+3V3', '3': 'GND', '4': 'GND', '5': 'GND', '6': 'NC', '7': 'SDA', '8': 'SCL'},
  'sensors', mpn='TE MS5607-02BA03 (pin-compatible MS5611 family, I2C addr 0x77)', lcsc='C97627')
C('C22', '100nF', '+3V3', 'GND', 'sensors')
P('J11', 'Connector_Generic:Conn_01x04', 'QWIIC (GPS / rangefinder)',
  'Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal',
  {'1': 'GND', '2': '+3V3', '3': 'SDA', '4': 'SCL'}, 'sensors', mpn='JST SM04B-SRSS-TB')

# ---------------- microSD (SPI) ----------------
P('U5', '74xx:74LVC125', '74LVC125A', 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
  {'1': 'GND', '2': 'SCK_5V', '3': 'SD_SCK'}, 'sd', mpn='74LVC125AD (5V-tolerant buffer)', unit=1)
P('U5', '74xx:74LVC125', '74LVC125A', 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
  {'4': 'GND', '5': 'MOSI_5V', '6': 'SD_MOSI'}, 'sd', unit=2)
P('U5', '74xx:74LVC125', '74LVC125A', 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
  {'10': 'GND', '9': 'SD_CS_5V', '8': 'SD_CS'}, 'sd', unit=3)
P('U5', '74xx:74LVC125', '74LVC125A', 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
  {'13': '+3V3', '12': 'GND', '11': 'NC'}, 'sd', unit=4)
P('U5', '74xx:74LVC125', '74LVC125A', 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
  {'14': '+3V3', '7': 'GND'}, 'sd', unit=5)
C('C23', '100nF', '+3V3', 'GND', 'sd')
R('R36', '10k', 'SD_CS_5V', '+3V3', 'sd')
R('R37', '10k', 'SD_CS', '+3V3', 'sd')
R('R38', '10k', 'SD_DAT1', '+3V3', 'sd')
R('R39', '10k', 'SD_DAT2', '+3V3', 'sd')
R('R40', '10k', 'MISO', '+3V3', 'sd')
P('J10', 'Connector:Micro_SD_Card', 'microSD (hinged lid)', 'Connector_Card:microSD_HC_Molex_47219-2001',
  {'1': 'SD_DAT2', '2': 'SD_CS', '3': 'SD_MOSI', '4': '+3V3', '5': 'SD_SCK', '6': 'GND', '7': 'MISO',
   '8': 'SD_DAT1', '9': 'GND'}, 'sd', mpn='Molex 47219-2001 (hinge lid - will not eject on landing)')
C('C24', '10uF 10V', '+3V3', 'GND', 'sd', fp=C0805)

# ---------------- TEST POINTS / MECH ----------------
for i, net in enumerate(['VLOGIC', 'VSERVO', '+3V3', 'GND', 'VBAT']):
    P(f'TP{i+1}', 'Connector:TestPoint', net, 'TestPoint:TestPoint_Pad_D1.5mm', {'1': net}, 'mech')
for i in range(4):
    P(f'H{i+1}', 'Mechanical:MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, 'mech')

# nets needing PWR_FLAG for ERC
PWR_FLAGS = ['GND', 'VBAT', 'VLOGIC', 'VSERVO', 'VPYRO', 'VBAT_D']

POWER_NETS = {  # net: track width mm
    'GND': 0.3, 'VBAT': 1.0, 'VPYRO': 0.8, 'VBAT_D': 0.4, 'VLOGIC': 0.4, 'VSERVO': 1.0,
    'BUCK_SW': 0.6, 'PYRO1_N': 0.8, 'PYRO2_N': 0.8, 'PYRO3_N': 0.8, 'PYRO4_N': 0.8, '+3V3': 0.3,
}

# ---- JLCPCB/LCSC part numbers (verified in stock on jlcpcb.com parts library, 2026-09-28) ----
LCSC_BY_VALUE = {
    ('Device:R', '100k'): 'C25803', ('Device:R', '33k'): 'C4216', ('Device:R', '1k'): 'C21190',
    ('Device:R', '18k'): 'C25810', ('Device:R', '220'): 'C22962', ('Device:R', '47k'): 'C25819',
    ('Device:R', '100'): 'C22775', ('Device:R', '4.7k'): 'C23162', ('Device:R', '10k'): 'C25804',
    ('Device:C', '10nF'): 'C57112', ('Device:C', '100nF'): 'C14663',
    ('Device:C', '10uF 25V'): 'C15850', ('Device:C', '10uF 10V'): 'C15850',
    ('Device:C', '22uF 10V'): 'C45783',
    ('Device:C_Polarized', '220uF 16V'): 'C178534',
}
LCSC_BY_REF = {
    'J1': 'C428721', 'J5': 'C2913282', 'J2': 'C49257', 'J3': 'C49257', 'J4': 'C49257', 'SW1': 'C221662',
    'U2': 'C97253', 'U3': 'C1864162', 'J10': 'C164170', 'BZ1': 'C22359707', 'U5': 'C7661',
    'Q6': 'C40912', 'Q7': 'C40912', 'J11': 'C160404', 'U1': 'C6186',
}
for p in PARTS:
    if not p['lcsc']:
        p['lcsc'] = LCSC_BY_REF.get(p['ref']) or LCSC_BY_VALUE.get((p['lib'], p['value']), '')
for p in PARTS:
    if p['value'] == '10uF 10V': p['value'] = '10uF 25V'
    if p['value'] == '22uF 10V': p['value'] = '22uF 25V'
    if p['ref'] == 'U5': p['mpn'] = 'TI SN74LVC125ADR (5V-tolerant inputs, run at 3.3V)'
    if p['ref'] in ('Q6', 'Q7'): p['mpn'] = 'Diodes BSS138-7-F'
