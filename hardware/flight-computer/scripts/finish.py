import pcbnew
fn = 'rocket_fc.kicad_pcb'
b = pcbnew.LoadBoard(fn)
MM = 1e6
def P(x, y): return pcbnew.VECTOR2I(int(x * MM), int(y * MM))
def text(s, x, y, size=0.9, bottom=False, angle=0, bold=False, layer=None):
    t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetPosition(P(x, y))
    t.SetLayer(layer if layer is not None else (pcbnew.B_SilkS if bottom else pcbnew.F_SilkS))
    size = max(size, 0.8)
    t.SetTextSize(pcbnew.VECTOR2I(int(size * MM), int(size * MM)))
    t.SetTextThickness(int(max(0.15, size * (0.2 if bold else 0.15)) * MM))
    t.SetTextAngleDegrees(angle)
    if bottom: t.SetMirrored(True)
    b.Add(t)
# mounting holes exactly on the 45.000 mm square (courtyard-centred placement leaves a few-micron offset)
for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
    b.FindFootprintByReference(f'H{i + 1}').SetPosition(P(100 + 22.5 * sx, 100 + 22.5 * sy))
# hide reference designators on silk (kept on the Fab/assembly layer)
for fp in b.GetFootprints():
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
C = 100.0
def T(s_, dx, dy, size=0.7, **k): text(s_, C + dx, C + dy, size, **k)
# the ARM plug is a shorting jumper, not a battery input: drop the footprint's +/- marks
for g in list(b.FindFootprintByReference('J5').GraphicalItems()):
    if g.GetClass() in ('PCB_TEXT', 'FP_TEXT') and g.GetText() in ('+', '-'):
        g.SetVisible(False)
# ---- top side ----
T('ROCKET FC v2.0', -22.0, 9.2, 0.8, bold=True)
T('2S LiPo', -19.0, -7.0, 0.7, bold=True)
T('POWER', 7.2, -30.6, 0.7, bold=True)
for dx, dy, lab in [(-16.4, 25.9, 'VLOG'), (-13.0, 30.4, 'VSRV'), (6.3, 31.6, '3V3'), (12.6, 27.9, 'GND'), (16.2, 25.5, 'VBAT')]:
    T(lab, dx, dy, 0.6)
for dx, lab in [(20.6, 'X'), (24.2, 'Y'), (27.8, 'AUX')]:
    T(lab, dx, 18.0, 0.7, bold=True)
for dy, lab in [(10.67, 'S'), (13.22, '+'), (15.75, '-')]:
    T(lab, 30.0, dy, 0.7)
T('3V3', 9.6, 6.0, 0.8); T('5V', 11.2, 1.9, 0.8, angle=90)   # JP1: bridge centre pad to ONE side
# ---- bottom side (hand-soldered connector side) ----
names = {'J6': 'P1 ASCENT', 'J7': 'P2 LANDING', 'J8': 'P3 LEGS', 'J9': 'P4 CHUTE'}
for ref, lab in names.items():
    fpx = sum(p.GetPosition().x for p in b.FindFootprintByReference(ref).Pads()) / 4 / MM
    text(lab, fpx, C + 26.9, 0.8, bottom=True, bold=True)
T('E-MATCH: LIFT LEVER, INSERT WIRE, CLOSE', 0.0, 29.0, 0.6, bottom=True)
T('ARM PLUG', -23.5, 9.6, 0.9, bottom=True, bold=True)
T('SHORTED XT30 MALE = ARMED', -23.5, 11.3, 0.55, bottom=True)
T('SERVOS', 24.2, 18.1, 0.8, bottom=True, bold=True)
T('< USB   ARDUINO NANO (pin 1 = square pad)', 4.0, 0.0, 0.9, bottom=True, bold=True)
T('SELF-LANDING ROCKET FC  v2.0', 0.0, -20.0, 1.0, bottom=True, bold=True)
T('70 mm DIA - FITS APOGEE 3in COUPLER (AC-74)', 0.0, -18.0, 0.65, bottom=True)
T('4x M3 ON 45 x 45 mm SQUARE', 0.0, -16.4, 0.65, bottom=True)
tb = b.GetTitleBlock(); tb.SetTitle('Self-Landing Rocket Flight Computer'); tb.SetRevision('2.0'); tb.SetCompany('Naivedhya')
tb.SetDate('2026-09-29')
filler = pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
pcbnew.SaveBoard(fn, b)
print('finished')
