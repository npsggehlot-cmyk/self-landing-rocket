import uuid, sexpdata, math
from sexpdata import Symbol as S
from symlib import get_symbol, pins
import design

PROJECT = 'rocket_fc'
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'rocketfc-root'))
def U(*k):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, 'rocketfc-' + '-'.join(map(str, k))))

def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'

GRID = 1.27
def snap(v):
    return round(round(v / GRID) * GRID, 4)

# ---- group regions on an A2 sheet (594 x 420 mm) ----
REGIONS = {
    'power':   (20, 30, 260, 120, 'POWER INPUT, SWITCH, HOLD-UP & 3.3V'),
    'servo':   (300, 30, 280, 120, 'SERVO 5V BUCK & SERVO OUTPUTS'),
    'mcu':     (20, 170, 150, 130, 'ARDUINO NANO (SOCKETED)'),
    'pyro':    (190, 170, 390, 130, 'PYRO CHANNELS (LOW-SIDE, ARM PLUG, CONTINUITY)'),
    'sensors': (20, 318, 240, 95, 'IMU, BAROMETER, I2C LEVEL SHIFT, QWIIC'),
    'sd':      (270, 318, 225, 95, 'microSD LOGGING'),
    'io':      (505, 318, 75, 95, 'BUZZER'),
    'mech':    (20, 2, 320, 26, ''),
}

def label_len(net):
    return len(net) * 1.1 + 3

# Build symbol cache
libsyms = {}
for p in design.PARTS:
    if p['lib'] not in libsyms:
        libsyms[p['lib']] = get_symbol(p['lib'])
libsyms['power:PWR_FLAG'] = get_symbol('power:PWR_FLAG')

ROT_LIBS = {'Device:R', 'Device:C', 'Device:C_Polarized', 'Device:L'}
def rot_of(p):
    return 90 if p['lib'] in ROT_LIBS else 0
def rotpins(ps, r):
    if not r: return ps
    out = []
    c, s_ = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    for x in ps:
        y = dict(x); y['x'] = x['x']*c - x['y']*s_; y['y'] = x['x']*s_ + x['y']*c; y['ang'] = (int(x['ang']) + r) % 360
        out.append(y)
    return out
def sym_extent(p):
    ps = rotpins([x for x in pins(libsyms[p['lib']]) if (p['unit'] is None or x['unit'] in (0, p['unit']))], rot_of(p))
    if not ps:
        return (-3, -3, 3, 3), ps
    xs = [x['x'] for x in ps]; ys = [x['y'] for x in ps]
    # extend by labels
    lx0 = min(xs) - max([label_len(p['pins'].get(x['num'], '')) for x in ps if x['x'] == min(xs)] + [0])
    lx1 = max(xs) + max([label_len(p['pins'].get(x['num'], '')) for x in ps if x['x'] == max(xs)] + [0])
    top = max([x['y'] + label_len(p['pins'].get(x['num'], '')) for x in ps if int(x['ang']) == 270] + [max(ys) + 4])
    bot = min([x['y'] - label_len(p['pins'].get(x['num'], '')) for x in ps if int(x['ang']) == 90] + [min(ys) - 4])
    # extra room above for ref/value on non-vertical symbols
    if not all(abs(x['x']) < 0.01 for x in ps):
        top += 6
    return (min(lx0, -4), bot, max(lx1, 4), top), ps

# ---- place parts: shelf-pack each group, then lay groups out in rows ----
LAYOUT = [  # rows of (group, width)
    [('power', 270), ('servo', 290)],
    [('mcu', 130), ('pyro', 430)],
    [('sensors', 205), ('sd', 240), ('io', 85)],
]
TITLES = {k: v[4] for k, v in REGIONS.items()}
by_group = {}
for p in design.PARTS:
    by_group.setdefault(p['group'], []).append(p)

def pack(parts, width):
    res = []; cx = 5; cy = 12; rh = 0
    for p in parts:
        (ex0, ey0, ex1, ey1), ps = sym_extent(p)
        vert = ps and all(abs(x['x']) < 0.01 for x in ps)
        fw = max(len(p['ref']), len(p['value'])) * 1.1 + 3 if vert else 0
        cw = ex1 - ex0 + 4 + fw; ch = ey1 - ey0 + 6
        if cx + cw > width and cx > 5:
            cx = 5; cy += rh; rh = 0
        res.append((p, cx - ex0, cy + ey1, ps))
        cx += cw; rh = max(rh, ch)
    return res, cy + rh + 3

placed = []
REG = {}
y = 34
for row in LAYOUT:
    x = 15; rowh = 0; packs = []
    for g, w in row:
        res, h = pack(by_group[g], w)
        packs.append((g, w, res, h)); rowh = max(rowh, h)
    for g, w, res, h in packs:
        REG[g] = (x, y, w, rowh, TITLES[g])
        for p, dx, dy, ps in res:
            placed.append((p, snap(x + dx), snap(y + dy), ps))
        x += w + 8
    y += rowh + 12
res, h = pack(by_group['mech'], 300)
for p, dx, dy, ps in res:
    placed.append((p, snap(15 + dx), snap(2 + dy), ps))
PAGE_H = y + 10
print('content height', PAGE_H)
REGIONS = REG
out = []
out.append(f'(kicad_sch (version 20230121) (generator eeschema)\n  (uuid {ROOT_UUID})\n  (paper "A2")\n')
out.append('  (title_block (title "Self-Landing Rocket Flight Computer") (rev "1.0") (company "Naivedhya") '
           '(comment 1 "2S LiPo | Arduino Nano socket | TVC servos | 4 pyro | IMU + baro + microSD"))\n')
# lib_symbols
out.append('  (lib_symbols\n')
for lib, sym in libsyms.items():
    s = list(sym); s[1] = lib
    out.append('    ' + sexpdata.dumps(s) + '\n')
out.append('  )\n')

def label(net, x, y, ang):
    just = {0: 'left bottom', 180: 'right bottom', 90: 'left bottom', 270: 'right bottom'}[ang]
    return (f'  (label {q(net)} (at {x} {y} {ang}) (fields_autoplaced)\n'
            f'    (effects (font (size 1.27 1.27)) (justify {just}))\n    (uuid {U("lbl", net, x, y)}))\n')

LBL_ANG = {0: 180, 180: 0, 90: 270, 270: 90}  # pin angle -> label angle

def symbol_inst(libid, ref, value, fp, X, Y, unit, props, pinlist, key, fieldpos=None, rot=0):
    s = [f'  (symbol (lib_id {q(libid)}) (at {X} {Y} {rot}) (unit {unit})\n'
         f'    (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced)\n    (uuid {U("sym", key)})\n']
    fields = [('Reference', ref, True), ('Value', value, True), ('Footprint', fp, False), ('Datasheet', '~', False)]
    fields += [(k, v, False) for k, v in props.items() if v]
    fx, fy, fjust = fieldpos if fieldpos else (X, Y - 6, None)
    for i, (k, v, vis) in enumerate(fields):
        hide = '' if vis else ' hide'
        just = f' (justify {fjust})' if fjust else ''
        yy = round(fy + i*2.54, 2) if fjust else round(fy - (1 - i)*2.54, 2)
        s.append(f'    (property {q(k)} {q(v)} (at {round(fx,2) if vis else X} {yy if vis else Y} {rot})\n'
                 f'      (effects (font (size 1.27 1.27)){just}{hide}))\n')
    for pn in pinlist:
        s.append(f'    (pin {q(pn)} (uuid {U("pin", key, pn)}))\n')
    s.append(f'    (instances (project {q(PROJECT)} (path "/{ROOT_UUID}" (reference {q(ref)}) (unit {unit}))))\n  )\n')
    return ''.join(s)

sym_uuid_by_ref = {}
for p, X, Y, ps in placed:
    unit = p['unit'] or 1
    key = f"{p['ref']}_{unit}"
    sym_uuid_by_ref.setdefault(p['ref'], U('sym', key))
    props = {'MPN': p['mpn'], 'LCSC': p['lcsc']}
    if p['lib'] in ('Device:R', 'Device:C'):
        props = {'LCSC': p['lcsc']}
    pinnums = [x['num'] for x in ps]
    xs = [x['x'] for x in ps] or [0]; ys = [x['y'] for x in ps] or [0]
    if rot_of(p):
        fieldpos = (X, Y - 3.2, None)
    elif ps and all(abs(x['x']) < 0.01 for x in ps):      # vertical 2-pin part: fields to the right
        fieldpos = (X + 2.54, Y - 1.27, 'left')
    else:
        toplab = max([label_len(p['pins'].get(x['num'], '')) for x in ps if x['ang'] == 270] + [0])
        fieldpos = (X, Y - max(ys + [3]) - toplab - 1.5, None)
    out.append(symbol_inst(p['lib'], p['ref'], p['value'], p['fp'], X, Y, unit, props, pinnums, key, fieldpos, rot_of(p)))
    for x in ps:
        net = p['pins'].get(x['num'])
        px = round(X + x['x'], 4); py = round(Y - x['y'], 4)
        if net is None:
            raise SystemExit(f"unassigned pin {p['ref']}.{x['num']} ({x['name']})")
        if net == 'NC':
            out.append(f'  (no_connect (at {px} {py}) (uuid {U("nc", p["ref"], x["num"])}))\n')
        else:
            out.append(label(net, px, py, LBL_ANG[int(x['ang'])]))

# power flags
fx = 350
for i, net in enumerate(design.PWR_FLAGS):
    X = snap(fx + i * 30); Y = snap(18)
    key = f'flag{i}'
    out.append(symbol_inst('power:PWR_FLAG', f'#FLG0{i+1}', 'PWR_FLAG', '', X, Y, 1, {}, ['1'], key)
               .replace('(in_bom yes)', '(in_bom yes)'))
    out.append(label(net, X, Y, 270))

# region titles / boxes
for g, (x0, y0, w, h, title) in REGIONS.items():
    if not title or g == 'mech':
        continue
    out.append(f'  (rectangle (start {x0} {y0}) (end {x0+w} {y0+h}) (stroke (width 0.3) (type dash) (color 0 0 0 0)) '
               f'(fill (type none)) (uuid {U("rect", g)}))\n')
    out.append(f'  (text {q(title)} (at {x0+3} {y0+5} 0) (effects (font (size 2.5 2.5) (thickness 0.5) bold) (justify left bottom)) '
               f'(uuid {U("title", g)}))\n')

notes = {
    'pyro': ['SAFETY: pyros cannot fire until the XT30 ARM PLUG (J5) is inserted. R11 (47k) lets the Nano read continuity while DISARMED (<0.2 mA, far below no-fire).',
             'Every MOSFET gate has a 100k pull-down: channels stay OFF while the Nano boots/resets/is unplugged. CONTx drops to 0V when the igniter burns through = exact ignition time.'],
    'power': ['Power switch feeds logic through D1 into 470uF hold-up cap C1, so igniter current (5-12 A) sagging the LiPo cannot reset the Nano.'],
    'servo': ['Servos have their own 5V/3A buck (U2) straight from the battery: servo stall current never touches the logic supply.'],
    'sensors': ['BSS138 shifters keep a 5V classic Nano from over-driving the 3.3V sensors; transparent for a 3.3V Nano ESP32.'],
    'sd': ['74LVC125 converts 5V SPI down to 3.3V for the card. Hinged-lid socket so the card cannot eject on landing.'],
}
for g, lines in notes.items():
    x0, y0, w, h, _ = REGIONS[g]
    for i, t in enumerate(lines):
        out.append(f'  (text {q(t)} (at {x0} {round(y0 + h + 4 + i*3.5, 2)} 0) (effects (font (size 1.5 1.5)) (justify left bottom)) (uuid {U("note", g, i)}))\n')

out.append(f'  (sheet_instances (path "/" (page "1")))\n)\n')
open(f'{PROJECT}.kicad_sch', 'w').write(''.join(out))

import json
json.dump(sym_uuid_by_ref, open('sym_uuids.json', 'w'), indent=1)
print('schematic written,', len(placed), 'symbol units')
