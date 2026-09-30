# Hand-placed high-current routes (locked so the autorouter keeps them)
import pcbnew, sys
fn = 'rocket_fc.kicad_pcb'
b = pcbnew.LoadBoard(fn)
MM = 1e6
def P(x, y): return pcbnew.VECTOR2I(int(x * MM), int(y * MM))
def pad(ref, num):
    fp = b.FindFootprintByReference(ref)
    return [p for p in fp.Pads() if p.GetNumber() == num]
def track(pts, layer, w, net):
    n = b.FindNet(net)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if abs(x1 - x2) < 0.02 and abs(y1 - y2) < 0.02: continue
        t = pcbnew.PCB_TRACK(b); t.SetLayer(layer); t.SetWidth(int(w * MM)); t.SetNet(n)
        t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2)); t.SetLocked(True); b.Add(t)
F = pcbnew.F_Cu
def xy(p): return (p.GetPosition().x / MM, p.GetPosition().y / MM)
j1p = xy(pad('J1', '2')[0]); j5b = xy(pad('J5', '2')[0]); j5p = xy(pad('J5', '1')[0])
print('J1+', j1p, 'J5 VBAT', j5b, 'J5 VPYRO', j5p)
# VBAT trunk: battery + -> arm plug, 1.5 mm on bottom copper, west of the Nano pin rows
tx = j5p[0] + 3.05
track([j1p, (tx, j1p[1] + abs(tx - j1p[0])), (tx, j5b[1] - 1.5), (j5b[0] + 1.5, j5b[1]), j5b], pcbnew.B_Cu, 1.5, 'VBAT')
# VPYRO bus on inner layer 2: arm plug -> every WAGO '+' terminal (upper pin-1 pad)
wago = [min((xy(p) for p in pad(r, '1')), key=lambda q: q[1]) for r in ('J9', 'J8', 'J7', 'J6')]  # west -> east
busy = wago[0][1] - 2.4
bx = j5p[0] + 3.1
track([j5p, (bx, j5p[1] + 3.1), (bx, busy), (wago[-1][0], busy)], pcbnew.In2_Cu, 1.5, 'VPYRO')
for r in ('J9', 'J8', 'J7', 'J6'):          # each WAGO pole has two pads: feed the upper, tie the lower
    up, lo = sorted((xy(p) for p in pad(r, '1')), key=lambda q: q[1])
    track([(up[0], busy), up, lo], pcbnew.In2_Cu, 1.5, 'VPYRO')
    up, lo = sorted((xy(p) for p in pad(r, '2')), key=lambda q: q[1])
    track([up, lo], F, 0.8, b.FindFootprintByReference(r).FindPadByNumber('2').GetNetname())
# VSERVO rail across the three servo headers (bottom)
sv = [xy(pad(r, '2')[0]) for r in ('J2', 'J3', 'J4')]
track(sv, pcbnew.B_Cu, 0.8, 'VSERVO')
# power switch: parallel both DPDT poles (pads 2-5 = VBAT_D, 3-4 = VLOGIC) on bottom copper
for a_, c_ in (('2', '5'), ('3', '4')):
    track([xy(pad('SW1', a_)[0]), xy(pad('SW1', c_)[0])], pcbnew.B_Cu, 0.6, b.FindFootprintByReference('SW1').FindPadByNumber(a_).GetNetname())
# servo-rail test point beside the buzzer flyback diode
d3 = xy(pad('D3', '1')[0]); tp2 = xy(pad('TP2', '1')[0])
track([d3, (d3[0] - 0.75, tp2[1]), tp2], F, 0.4, 'VSERVO')
# pyro MOSFET sources and battery GND: full (solid) zone connection
for ref, num in [('Q1', '2'), ('Q2', '2'), ('Q3', '2'), ('Q4', '2'), ('J1', '1')]:
    for p in pad(ref, num):
        p.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

# ---------------- servo buck (TPS563200) hand layout ----------------
def pp(ref, num): return xy(pad(ref, num)[0])
def via(x, y, net, d=0.6, dr=0.3):
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(x, y)); v.SetWidth(int(d * MM)); v.SetDrill(int(dr * MM))
    v.SetNet(b.FindNet(net)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetLocked(True); b.Add(v)
sw = pp('U2', '2'); l1a = pp('L1', '1'); l1b = pp('L1', '2')
track([sw, (l1a[0], sw[1])], F, 0.8, 'BUCK_SW')
c9b = pp('C9', '2'); track([c9b, (l1a[0] - 0.7, c9b[1])], F, 0.5, 'BUCK_SW')
u6 = pp('U2', '6'); c9a = pp('C9', '1'); track([u6, (u6[0] + 0.5, u6[1] + 0.55), c9a], F, 0.3, 'BUCK_BST')
u3 = pp('U2', '3'); c8a = pp('C8', '1'); c6a = pp('C6', '1'); c7a = pp('C7', '1')
track([u3, (u3[0], c8a[1]), c8a, c6a, c7a], F, 0.6, 'VBAT')
c8b = pp('C8', '2'); c6b = pp('C6', '2'); c7b = pp('C7', '2')
track([c8b, c6b, c7b], F, 0.5, 'GND')
for q in (c6b, c7b):
    track([q, (q[0] + 0.95, q[1])], F, 0.5, 'GND'); via(q[0] + 0.95, q[1], 'GND')
u1 = pp('U2', '1'); track([u1, (u1[0] + 1.15, u1[1] + 0.25)], F, 0.4, 'GND'); via(u1[0] + 1.15, u1[1] + 0.25, 'GND')
u4 = pp('U2', '4'); r5a = pp('R5', '1'); r4b = pp('R4', '2')
track([u4, (r5a[0], u4[1] - 0.4), r5a, r4b], F, 0.25, 'BUCK_FB')
r5b = pp('R5', '2'); track([r5b, (r5b[0], r5b[1] - 0.95)], F, 0.3, 'GND'); via(r5b[0], r5b[1] - 0.95, 'GND')
u5 = pp('U2', '5'); r6b = pp('R6', '2'); r7a = pp('R7', '1')
ex = u5[0] - 0.96
track([u5, (ex, u5[1]), (ex, r6b[1]), r6b], F, 0.25, 'BUCK_EN')
track([r7a, (ex, r7a[1])], F, 0.25, 'BUCK_EN')
r7b = pp('R7', '2'); track([r7b, (r7b[0], r7b[1] - 0.9)], F, 0.3, 'GND'); via(r7b[0], r7b[1] - 0.9, 'GND')
c10a = pp('C10', '1'); c11a = pp('C11', '1'); c12a = pp('C12', '1')
track([l1b, (c10a[0], l1b[1]), c10a], F, 0.8, 'VSERVO'); track([c10a, c11a], F, 0.8, 'VSERVO')
track([c12a, (l1b[0], c12a[1] + 1.4)], F, 0.6, 'VSERVO')
for r in ('C10', 'C11'):
    g = pp(r, '2'); track([g, (g[0] + 1.0, g[1])], F, 0.4, 'GND'); via(g[0] + 1.0, g[1], 'GND')
c12b = pp('C12', '2'); track([c12b, (c12b[0] - 0.9, c12b[1] - 0.6)], F, 0.4, 'GND'); via(c12b[0] - 0.9, c12b[1] - 0.6, 'GND')

# buck input: battery straight to U2/C6/C7 on bottom copper (1.5 mm), three vias up to the input caps
c6a = pp('C6', '1'); c7a = pp('C7', '1'); vx = c6a[0] - 1.05
track([j1p, (j1p[0] + 1.5, j1p[1] + 1.5), (vx - 2.3, j1p[1] + 1.5), (vx, j1p[1] - 0.8), (vx, c7a[1])], pcbnew.B_Cu, 1.2, 'VBAT')
for y in (c6a[1], (c6a[1] + c7a[1]) / 2, c7a[1]):
    via(vx, y, 'VBAT', 0.8, 0.4)
track([(vx, c6a[1]), c6a], F, 0.8, 'VBAT'); track([(vx, c7a[1]), c7a], F, 0.8, 'VBAT'); track([(vx, c6a[1]), (vx, c7a[1])], F, 0.8, 'VBAT')
# AMS1117 tab: small +3V3 copper pour for heat spreading
z = pcbnew.ZONE(b); z.SetLayer(F); z.SetNet(b.FindNet('+3V3')); z.SetAssignedPriority(2)
z.SetMinThickness(int(0.2 * MM)); z.SetLocalClearance(int(0.25 * MM)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
tab = [xy(p) for p in pad('U1', '2')]; tx_ = max(t[0] for t in tab)
for (x, y) in [(tx_ - 2.4, -13.9 + 100), (tx_ + 2.2, -13.9 + 100), (tx_ + 2.2, -7.2 + 100), (tx_ - 2.4, -7.2 + 100)]:
    z.AppendCorner(P(x, y), -1)
b.Add(z)
# pyro columns: gate network, continuity divider link, and the firing path drain -> WAGO '-'
for q, rg, rpd, rs1, rs2, cc, j in [('Q1','R14','R15','R16','R17','C16','J6'), ('Q2','R18','R19','R20','R21','C17','J7'),
                                   ('Q3','R22','R23','R24','R25','C18','J8'), ('Q4','R26','R27','R28','R29','C19','J9')]:
    net = lambda r, n: b.FindFootprintByReference(r).FindPadByNumber(n).GetNetname()
    g = pp(rg, '2'); pd = pp(rpd, '1'); qg = pp(q, '1'); yb = g[1] + 1.2
    track([pd, g, (g[0], yb), (qg[0], yb), qg], F, 0.25, net(q, '1'))
    track([pp(rs1, '2'), pp(rs2, '1'), pp(cc, '1')], F, 0.25, net(rs1, '2'))
    dr = pp(q, '3'); jn = min((xy(p) for p in pad(j, '2')), key=lambda t: t[1]); r1 = pp(rs1, '1')
    yj = jn[1] - 1.7
    track([dr, (jn[0], yj), jn], F, 0.8, net(q, '3'))
    track([r1, (r1[0], yj), (jn[0], yj)], F, 0.3, net(q, '3'))
pcbnew.SaveBoard(fn, b)
print('pre-routes added')
