# Avionics bay sled for the RocketFC v2 board in an Apogee 3" (74 mm) body tube.
# Units mm.  +Z = forward (nose).  X/Y match the PCB top view: +Y = 12 o'clock (power switch),
# +X = 3 o'clock (Nano USB), -X = 9 o'clock (ARM plug), -Y = 6 o'clock (e-match terminals).
import cadquery as cq, math, json

# ---------------- parameters ----------------
TUBE_ID = 74.47            # Apogee 3.0" body tube ID (2.932")
TUBE_OD = 76.20            # 3.000"
R = 37.0                   # sled outer radius (74.0 mm dia -> 0.24 mm radial clearance)
RING_IN = 28.0             # ring inner radius (open centre); tie-rod columns sit fully inside the ring
RING_H = 8.0
PCB_R = 35.0
HOLE = 22.5                # PCB M3 holes on a 45 x 45 square
BOSS_R = 3.2
ZB = 30.0                  # PCB bottom face (aft side)
PCB_T = 1.6
ZT = ZB + PCB_T            # PCB top face (forward side)
UP_BOSS_H = 6.0
SLEEVE_IN = (36.5, 19.5)   # battery pocket (fits ~35 x 18 mm 2S packs, e.g. 1000 mAh)
SLEEVE_C = (-2.5, -4.0)    # pocket centre (clear of the XT30, servo plugs and C13)
WALL = 1.8
FLOOR_Z = ZT + 4.0
ZTOP = ZT + 64.0           # forward face of the bay
RIB_Z0 = ZT + 26.0         # ribs start above the servo plugs / battery plug
INSERT_D, INSERT_L = 4.0, 6.0   # M3 heat-set insert (e.g. 4.0 mm hole x 5.7 mm)
M3_CLR = 3.3
ROD_CLR = 3.4              # M3 threaded rod / M3x100 screw
NUT_AF, NUT_H = 5.7, 2.6   # M3 hex nut trap in the aft face
COL_R = 3.5               # forward spacer columns

def arc_sector(r0, r1, a0, a1, z0, z1):
    """annular sector r0..r1, angles a0..a1 (deg), z0..z1 -- true cylindrical faces"""
    ann = cq.Workplane('XY').workplane(offset=z0).circle(r1).circle(r0).extrude(z1 - z0)
    big = 3 * r1
    m = math.radians((a0 + a1) / 2); h = math.radians((a1 - a0) / 2)
    pts = [(0, 0)] + [(big * math.cos(m + t), big * math.sin(m + t)) for t in (-h, -h / 2, 0, h / 2, h)]
    wedge = cq.Workplane('XY').workplane(offset=z0 - 1).polyline(pts).close().extrude(z1 - z0 + 2)
    return ann.intersect(wedge)

def ring(z0, z1, r0=RING_IN, r1=R):
    # rotated 7 deg so the cylinder seam never lands on a radial screw hole (Parasolid flags that as a fault)
    return cq.Workplane('XY').workplane(offset=z0).circle(r1).circle(r0).extrude(z1 - z0).rotate((0, 0, 0), (0, 0, 1), 7)

def cyl(x, y, r, z0, z1):
    return cq.Workplane('XY').workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def radial_insert(angle, z):
    """heat-set insert bore entering from the outside at `angle`, centred at height z"""
    a = math.radians(angle)
    bore = cq.Workplane('YZ').circle(INSERT_D / 2).extrude(INSERT_L + 0.5).translate((R - INSERT_L, 0, z))
    tip = cq.Workplane('YZ').circle(1.4).extrude(1.5).translate((R - INSERT_L - 1.0, 0, z))   # stops 1 mm short of the ring bore
    return bore.union(tip).rotate((0, 0, 0), (0, 0, 1), angle)

def rib(p0, p1, z0, z1, t=2.4):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0); ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    return (cq.Workplane('XY').box(L, t, z1 - z0, centered=(False, True, False))
            .rotate((0, 0, 0), (0, 0, 1), ang).translate((x0, y0, z0)))

CORNERS = [(HOLE, HOLE), (-HOLE, HOLE), (-HOLE, -HOLE), (HOLE, -HOLE)]
SCREW_ANG = [0, 90, 180, 270]          # radial tube screws (both rings)

# ================= AFT SECTION (holds PCB from below, e-match / servo wires exit aft) =================
aft = ring(0, RING_H)
for a in (45, 135, 225, 315):
    aft = aft.union(arc_sector(33.5, R, a - 8, a + 8, 0, ZB))
for x, y in CORNERS:
    aft = aft.union(cyl(x, y, BOSS_R, RING_H - 1, ZB))
    aft = aft.cut(cyl(x, y, ROD_CLR / 2, -1, ZB + 1))                  # M3 tie-rod passes straight through
    aft = aft.cut(cq.Workplane('XY').workplane(offset=-1).center(x, y).polygon(6, NUT_AF / math.cos(math.pi / 6)).extrude(NUT_H + 1))
for a in SCREW_ANG:
    aft = aft.cut(radial_insert(a, RING_H / 2))
for a in (22.5, 157.5, 202.5, 337.5):                                 # wire channels along the tube wall
    aft = aft.cut(arc_sector(32.5, R + 1, a - 9, a + 9, -1, RING_H + 1))

# ================= FORWARD SECTION (clamps PCB from above, carries the battery) =================
PLATE_T = 3.0
cx, cy = SLEEVE_C
ix, iy = SLEEVE_IN[0] / 2, SLEEVE_IN[1] / 2
ox, oy = ix + WALL, iy + WALL
fwd = cyl(0, 0, R, ZTOP - PLATE_T, ZTOP).rotate((0, 0, 0), (0, 0, 1), 7)          # forward bulkhead plate
fwd = fwd.union(ring(ZTOP - RING_H, ZTOP, r0=33.0))                                    # outer band for the tube screws
for a in SCREW_ANG:                                                                    # thick pads behind each radial screw
    fwd = fwd.union(arc_sector(29.0, R, a - 6, a + 6, ZTOP - RING_H, ZTOP))
for x, y in CORNERS:                                                                   # spacer columns: clamp PCB, carry tie-rods
    fwd = fwd.union(cyl(x, y, COL_R, ZT, ZTOP))
sleeve = box(cx - ox, cx + ox, cy - oy, cy + oy, FLOOR_Z, ZTOP).cut(box(cx - ix, cx + ix, cy - iy, cy + iy, FLOOR_Z + 2, ZTOP + 1))
sleeve = sleeve.cut(box(cx - ix + 1.5, cx - ix + 13.5, cy + iy - 1, cy + oy + 1, FLOOR_Z + 2, FLOOR_Z + 16))   # battery lead window -> J1
sleeve = sleeve.cut(box(cx - 12, cx + 12, cy - 5, cy + 5, FLOOR_Z - 1, FLOOR_Z + 3))       # floor lightening / airflow
fwd = fwd.union(sleeve)
for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):                                   # ribs: battery pocket -> columns
    p0 = (cx + sx * ox, cy + sy * oy)
    fwd = fwd.union(rib(p0, (sx * HOLE, sy * HOLE), RIB_Z0, ZTOP - PLATE_T))
fwd = fwd.cut(box(cx - ix, cx + ix, cy - iy, cy + iy, ZTOP - PLATE_T - 1, ZTOP + 1))   # battery goes in through the plate
for y0, y1 in ((cy + oy + 1.0, cy + oy + 3.0), (cy + oy + 5.0, cy + oy + 7.0),       # velcro strap slots north + south
               (cy - oy - 3.0, cy - oy - 1.0), (cy - oy - 7.0, cy - oy - 5.0)):         # (a 2 mm bar each side)
    fwd = fwd.cut(box(cx - 8, cx + 8, y0, y1, ZTOP - PLATE_T - 1, ZTOP + 1))
for ang in (67.5, 112.5):                                                              # wire pass-throughs (chute / forward wiring)
    fwd = fwd.cut(cyl(25 * math.cos(math.radians(ang)), 25 * math.sin(math.radians(ang)), 6.0, ZTOP - PLATE_T - 1, ZTOP + 1))
for x, y in CORNERS:
    fwd = fwd.cut(cyl(x, y, ROD_CLR / 2, ZT - 1, ZTOP + 1))
for a in SCREW_ANG:
    fwd = fwd.cut(radial_insert(a, ZTOP - RING_H / 2))

# ================= reference bodies (for fit check / Onshape context only) =================
pcb = cyl(0, 0, PCB_R, ZB, ZT)
for x, y in CORNERS:
    pcb = pcb.cut(cyl(x, y, 1.6, ZB - 1, ZT + 1))
parts = json.load(open('/home/claude/avbay/parts.json'))
comps = None
for p in parts:
    z0, z1 = (ZT, ZT + p['h']) if p['side'] == 'F' else (ZB - p['h'], ZB)
    b = box(p['x0'], p['x1'], p['y0'], p['y1'], z0, z1)
    comps = b if comps is None else comps.union(b)
battery = box(cx - 17.5, cx + 17.5, cy - 9, cy + 9, FLOOR_Z + 2, FLOOR_Z + 2 + 70)
tube = cq.Workplane('XY').workplane(offset=-10).circle(TUBE_OD / 2).circle(TUBE_ID / 2).extrude(ZTOP + 40)

if __name__ == '__main__':
    import sys
    aft = aft.clean(); fwd = fwd.clean()
    aft = cq.Workplane('XY').add(aft.val().fix()); fwd = cq.Workplane('XY').add(fwd.val().fix())
    cq.exporters.export(aft, '/home/claude/avbay/AvBay_Aft.step')
    cq.exporters.export(fwd, '/home/claude/avbay/AvBay_Forward.step')
    cq.exporters.export(aft, '/home/claude/avbay/AvBay_Aft.stl', tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(fwd, '/home/claude/avbay/AvBay_Forward.stl', tolerance=0.02, angularTolerance=0.1)
    asm = cq.Assembly(name='RocketFC_AvBay')
    asm.add(aft, name='Sled_Aft', color=cq.Color(0.95, 0.55, 0.1))
    asm.add(fwd, name='Sled_Forward', color=cq.Color(0.2, 0.45, 0.85))
    asm.add(pcb, name='PCB_RocketFC_v2', color=cq.Color(0.1, 0.5, 0.2))
    asm.add(comps, name='PCB_component_envelopes', color=cq.Color(0.3, 0.3, 0.3))
    asm.add(battery, name='Battery_2S_1000mAh_70x35x18', color=cq.Color(0.8, 0.1, 0.1))
    asm.save('/home/claude/avbay/AvBay_Assembly.step')
    # fit checks
    def vol(s): return s.val().Volume() if s.vals() else 0.0
    for nm, part in (('aft', aft), ('fwd', fwd)):
        print(nm, 'vol %.1f cm3' % (part.val().Volume() / 1000), 'x comps %.2f' % vol(part.intersect(comps)),
              'x battery %.2f' % vol(part.intersect(battery)), 'x pcb %.2f' % vol(part.intersect(pcb)))
    print('aft x fwd %.2f' % vol(aft.intersect(fwd)), 'battery x comps %.2f' % vol(battery.intersect(comps)))
    bb = fwd.union(aft).val().BoundingBox(); print('bbox', round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2))
