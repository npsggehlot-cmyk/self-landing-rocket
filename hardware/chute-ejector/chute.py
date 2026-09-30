# Servo-latched spring parachute ejector for the RocketFC rocket (Apogee 3" / 74 mm body tube).
# Units mm. +Z = forward (nose). z = 0 is the underside of the bulkhead plate.
#
#  nose cone ─┐
#  parachute  │  chute bay (plain body tube above the piston)
#  PISTON  ───┤  pushed by one compression spring, pulled down by the STEM
#  spring     │
#  BULKHEAD ──┤  4x M3 radial screws into the tube (same scheme as the avionics bay)
#  LATCH CUP  │  rotates 90 deg on the servo: slot aligned = release, crossed = locked
#  SERVO      ┘  MG90S micro servo, hangs under the bulkhead
import cadquery as cq, math

TUBE_ID, TUBE_OD = 74.47, 76.20
R = 37.0                  # bulkhead OD 74.0
PIST_R = 36.7             # piston OD 73.4 (0.5 mm radial slide clearance)
PLATE_T = 5.0
BAND_H = 11.0             # screw band below the plate
INSERT_D, INSERT_L = 4.0, 6.0

# latch geometry
SLOT_L, SLOT_W = 17.0, 9.0        # keyhole slot in the bulkhead (x-long)
KEY_W, KEY_T = 16.0, 8.0          # T-head / stem bar width and thickness (bar fits inside the spring)
NECK_W = 7.0
CUP_SLOT = (17.5, 9.5)
CUP_CAV_D, CUP_OD = 20.6, 23.6
CUP_TOP, CUP_CAV, CUP_BOT = 3.0, 7.0, 5.0
HORN_SLOT_W, HORN_SLOT_D = 6.5, 4.0
T_HEAD_H = 6.0

# spring: 22 mm OD, 1.4-1.5 mm wire, 100 mm free, compressed to 35 mm (k ~0.4-0.55 N/mm -> 26-36 N preload)
SPRING_OD, SPRING_FREE, SPRING_COMP = 22.0, 100.0, 35.0
POCKET_D, POCKET_H = 23.0, 2.0
Z_SPRING0 = PLATE_T - POCKET_H              # spring seat
Z_PIST = Z_SPRING0 + SPRING_COMP            # piston plate underside when armed
PIST_TOP_T, SKIRT_H, SKIRT_T = 3.0, 15.0, 1.6

# servo (MG90S / SG90 class): spline top at z = SPLINE_Z
SPLINE_Z = -12.5
SERVO_BOT = SPLINE_Z - 29.0
EAR_TOP = SERVO_BOT + 18.4
SERVO_L, SERVO_W, SHAFT_OFF, EAR_PITCH = 22.8, 12.3, 5.5, 27.8
SHELF_T = 3.0

def cyl(x, y, r, z0, z1):
    return cq.Workplane('XY').workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def ring(z0, z1, r0, r1):
    return cq.Workplane('XY').workplane(offset=z0).circle(r1).circle(r0).extrude(z1 - z0).rotate((0, 0, 0), (0, 0, 1), 7)
def arc_sector(r0, r1, a0, a1, z0, z1):
    ann = cq.Workplane('XY').workplane(offset=z0).circle(r1).circle(r0).extrude(z1 - z0)
    big = 3 * r1; m = math.radians((a0 + a1) / 2); h = math.radians((a1 - a0) / 2)
    pts = [(0, 0)] + [(big * math.cos(m + t), big * math.sin(m + t)) for t in (-h, -h / 2, 0, h / 2, h)]
    return ann.intersect(cq.Workplane('XY').workplane(offset=z0 - 1).polyline(pts).close().extrude(z1 - z0 + 2))
def radial_insert(angle, z):
    bore = cq.Workplane('YZ').circle(INSERT_D / 2).extrude(INSERT_L + 0.5).translate((R - INSERT_L, 0, z))
    tip = cq.Workplane('YZ').circle(1.4).extrude(1.5).translate((R - INSERT_L - 1.0, 0, z))
    return bore.union(tip).rotate((0, 0, 0), (0, 0, 1), angle)

# ================= 1. BULKHEAD + SERVO FRAME (one print, plate face down) =================
bh = cyl(0, 0, R, 0, PLATE_T).rotate((0, 0, 0), (0, 0, 1), 7)
bh = bh.union(ring(-BAND_H, 0, 32.0, R))
for a in (0, 90, 180, 270):
    bh = bh.union(arc_sector(29.0, R, a - 7, a + 7, -BAND_H, 0))
# servo frame: two side walls + ear shelf
FX0, FX1, WY0, WY1 = -24.0, 13.0, 14.0, 17.0
for s in (1, -1):
    bh = bh.union(box(FX0, FX1, min(s * WY0, s * WY1), max(s * WY0, s * WY1), EAR_TOP, 0))
bh = bh.union(box(FX0, FX1, -WY1, WY1, EAR_TOP, EAR_TOP + SHELF_T))
cx = -SHAFT_OFF
bh = bh.cut(box(cx - SERVO_L / 2 - 0.3, cx + SERVO_L / 2 + 0.3, -SERVO_W / 2 - 0.3, SERVO_W / 2 + 0.3, EAR_TOP - 1, EAR_TOP + SHELF_T + 1))
for ex in (cx - EAR_PITCH / 2, cx + EAR_PITCH / 2):
    bh = bh.cut(cyl(ex, 0, 0.9, EAR_TOP - 1, EAR_TOP + SHELF_T + 1))            # M2 self-tapping into the shelf
# plate features
bh = bh.cut(box(-SLOT_L / 2, SLOT_L / 2, -SLOT_W / 2, SLOT_W / 2, -1, PLATE_T + 1))   # keyhole slot
bh = bh.cut(cyl(0, 0, POCKET_D / 2, Z_SPRING0, PLATE_T + 1))                        # spring seat pocket
for x in (17.0, -17.0):
    bh = bh.cut(cyl(x, 0, 4.0, -1, PLATE_T + 1))                                  # air vents (piston must not suck a vacuum)
for sy in (1, -1):
    for x in (-5.0, 5.0):
        bh = bh.cut(cyl(x, sy * 25.0, 2.2, -1, PLATE_T + 1))                       # Kevlar shock-cord anchor holes
for a in (0, 90, 180, 270):
    bh = bh.cut(radial_insert(a, -BAND_H / 2))
bh = bh.cut(box(-1.0, 1.0, SLOT_W / 2 + 1.0, SLOT_W / 2 + 4.0, PLATE_T - 0.6, PLATE_T + 1))   # alignment tick next to slot

# ================= 2. LATCH CUP (on the servo horn) =================
z_ct = -0.2                       # cup top face when loaded (0.2 mm under the bulkhead; spring load presses it up)
cz0 = z_ct - (CUP_TOP + CUP_CAV + CUP_BOT)
cup = cyl(0, 0, CUP_OD / 2, cz0, z_ct)
cup = cup.cut(cyl(0, 0, CUP_CAV_D / 2, cz0 + CUP_BOT, z_ct - CUP_TOP))            # cavity for the T-head
cup = cup.cut(box(-CUP_SLOT[1] / 2, CUP_SLOT[1] / 2, -CUP_SLOT[0] / 2, CUP_SLOT[0] / 2, z_ct - CUP_TOP - 1, z_ct + 1))   # slot (drawn LOCKED: y-long)
cup = cup.cut(box(-CUP_OD, CUP_OD, -HORN_SLOT_W / 2, HORN_SLOT_W / 2, cz0 - 1, cz0 + HORN_SLOT_D))   # servo-horn arm slot
cup = cup.cut(cyl(0, 0, 4.2, cz0 - 1, cz0 + HORN_SLOT_D))                                            # horn hub
cup = cup.cut(box(-0.8, 0.8, CUP_OD / 2 - 1.2, CUP_OD / 2 + 1, z_ct - 1.5, z_ct + 1))                 # slot-direction notch

# ================= 3. STEM / LATCH KEY (printed flat, 8 mm thick) =================
zt_bot = z_ct - CUP_TOP - T_HEAD_H - 0.1           # T-head sits just under the cup top plate
z_neck0, z_neck1 = z_ct - CUP_TOP - 0.1, 0.0
z_cap0 = Z_PIST + PIST_TOP_T
hw, nw = KEY_W / 2, NECK_W / 2
prof = [(-hw, zt_bot), (hw, zt_bot), (hw, z_neck0), (nw, z_neck0), (nw, z_neck1), (hw, z_neck1), (hw, z_cap0),
        (11.0, z_cap0), (11.0, z_cap0 + 3.0), (-11.0, z_cap0 + 3.0), (-11.0, z_cap0), (-hw, z_cap0), (-hw, z_neck1),
        (-nw, z_neck1), (-nw, z_neck0), (-hw, z_neck0)]
stem = cq.Workplane('XZ').polyline(prof).close().extrude(KEY_T / 2, both=True)

# ================= 4. PISTON (printed top plate down) =================
pis = cyl(0, 0, PIST_R, Z_PIST - 1.5, Z_PIST + PIST_TOP_T)
pis = pis.union(ring(Z_PIST - 1.5 - SKIRT_H, Z_PIST - 1.5, PIST_R - SKIRT_T, PIST_R))
pis = pis.cut(cyl(0, 0, POCKET_D / 2, Z_PIST - 2.0, Z_PIST))                        # spring seat recess
pis = pis.cut(box(-KEY_W / 2 - 0.25, KEY_W / 2 + 0.25, -KEY_T / 2 - 0.25, KEY_T / 2 + 0.25, Z_PIST - 7, Z_PIST + PIST_TOP_T + 1))  # stem slot
for sy in (1, -1):
    pis = pis.cut(cyl(0, sy * 22.0, 2.6, Z_PIST - 3, Z_PIST + PIST_TOP_T + 1))    # chute bridle / shock cord
for a in range(45, 360, 90):
    pis = pis.cut(cyl(28 * math.cos(math.radians(a)), 28 * math.sin(math.radians(a)), 3.0, Z_PIST - 3, Z_PIST + PIST_TOP_T + 1))  # lightening

# ================= reference bodies =================
servo = box(cx - SERVO_L / 2, cx + SERVO_L / 2, -SERVO_W / 2, SERVO_W / 2, SERVO_BOT, EAR_TOP + 4.3)
servo = servo.union(box(cx - 16.25, cx + 16.25, -SERVO_W / 2, SERVO_W / 2, EAR_TOP - 2.5, EAR_TOP))
servo = servo.union(cyl(0, 0, 5.9, EAR_TOP + 4.3, SPLINE_Z - 4.0))
horn = cyl(0, 0, 3.5, SPLINE_Z - 3.5, SPLINE_Z + 0.5).union(box(-2.8, 16, -2.8, 2.8, SPLINE_Z - 1.0, SPLINE_Z + 0.5))
spring_body = cyl(0, 0, SPRING_OD / 2, Z_SPRING0, Z_PIST).cut(cyl(0, 0, SPRING_OD / 2 - 1.5, Z_SPRING0 - 1, Z_PIST + 1))
tube = cq.Workplane('XY').workplane(offset=-60).circle(TUBE_OD / 2).circle(TUBE_ID / 2).extrude(200)

def vol(s): return s.val().Volume() if s.vals() else 0.0

if __name__ == '__main__':
    parts = {'bulkhead': bh, 'cup': cup, 'stem': stem, 'piston': pis}
    for n, p in parts.items():
        s = p.clean().val(); print(n, 'valid', s.isValid(), 'vol %.1f cm3' % (s.Volume() / 1000), 'min edge %.2f' % min(e.Length() for e in s.Edges()))
    checks = [('stem x bulkhead', stem, bh), ('stem x cup', stem, cup), ('stem x piston', stem, pis), ('cup x bulkhead', cup, bh),
              ('cup x servo', cup, servo), ('cup x horn(in slot ok)', cup, horn), ('servo x bulkhead', servo, bh), ('piston x bulkhead', pis, bh),
              ('spring x stem', spring_body, stem), ('spring x piston', spring_body, pis), ('spring x bulkhead', spring_body, bh)]
    for n, a, b in checks:
        print('%-26s %.3f' % (n, vol(a.intersect(b))))
    # latch geometry checks
    cup_open = cup.rotate((0, 0, 0), (0, 0, 1), 90)
    head = box(-KEY_W / 2, KEY_W / 2, -KEY_T / 2, KEY_T / 2, zt_bot, zt_bot + T_HEAD_H)
    print('T-head sweep through OPEN cup slot (should be 0):', round(vol(head.translate((0, 0, 3.5)).intersect(cup_open)), 3))
    print('T-head bearing when LOCKED (should be >0, head raised 0.2):', round(vol(head.translate((0, 0, 0.2)).intersect(cup)), 3))
    print('T-head through bulkhead slot (0):', round(vol(head.translate((0, 0, 10)).intersect(bh)), 3))
    for n, p in parts.items():
        cq.exporters.export(p.clean(), f'/home/claude/avbay/ChuteEjector_{n}.step')
    # print-orientation STLs
    cq.exporters.export(bh.clean().rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, PLATE_T)), '/home/claude/avbay/Print_Chute_Bulkhead.stl', tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(cup.clean().translate((0, 0, -cz0)), '/home/claude/avbay/Print_Chute_LatchCup.stl', tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(stem.clean().rotate((0, 0, 0), (1, 0, 0), 90), '/home/claude/avbay/Print_Chute_Stem.stl', tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(pis.clean().rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, Z_PIST + PIST_TOP_T)), '/home/claude/avbay/Print_Chute_Piston.stl', tolerance=0.02, angularTolerance=0.1)
    asm = cq.Assembly(name='RocketFC_ChuteEjector')
    asm.add(bh.clean(), name='Bulkhead_ServoFrame', color=cq.Color(0.95, 0.55, 0.1))
    asm.add(cup.clean(), name='Latch_Cup', color=cq.Color(0.85, 0.15, 0.15))
    asm.add(stem.clean(), name='Latch_Stem', color=cq.Color(0.2, 0.2, 0.2))
    asm.add(pis.clean(), name='Piston', color=cq.Color(0.2, 0.45, 0.85))
    asm.add(servo, name='REF_MG90S_servo', color=cq.Color(0.1, 0.1, 0.4))
    asm.add(horn, name='REF_servo_horn', color=cq.Color(0.9, 0.9, 0.9))
    asm.add(spring_body, name='REF_spring_20OD_x_100free', color=cq.Color(0.7, 0.7, 0.7))
    asm.save('/home/claude/avbay/RocketFC_Chute_Ejector.step')
    print('saved')
