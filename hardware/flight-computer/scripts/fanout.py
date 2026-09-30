# Add a GND via next to every SMD GND pad so the ground planes connect directly.
import pcbnew, math, sys
from shapely.geometry import Point, box, Polygon, LineString
from shapely.ops import unary_union
from shapely import affinity
fn = sys.argv[1] if len(sys.argv) > 1 else 'rocket_fc.kicad_pcb'
b = pcbnew.LoadBoard(fn)
MM = 1e6; CX = CY = 100; RAD = 35
VIA_D, VIA_DR, CLR = 0.6, 0.3, 0.2
gnd = b.FindNet('GND')
def pad_poly(p, grow=0.0):
    sh = p.GetEffectivePolygon()  # SHAPE_POLY_SET in board coords
    pts = []
    o = sh.COutline(0)
    for i in range(o.PointCount()):
        v = o.CPoint(i); pts.append((v.x / MM, v.y / MM))
    poly = Polygon(pts)
    return poly.buffer(grow) if grow else poly
obst_F, obst_B, crt = [], [], []
for fp in b.GetFootprints():
    for side in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        cy = fp.GetCourtyard(side)
        if cy.OutlineCount():
            o = cy.COutline(0); pts = [(o.CPoint(i).x / MM, o.CPoint(i).y / MM) for i in range(o.PointCount())]
            if len(pts) > 2:
                crt.append((fp.GetReference(), 'F' if side == pcbnew.F_CrtYd else 'B', Polygon(pts).buffer(0)))
    for p in fp.Pads():
        tht = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        isg = p.GetNetname() == 'GND'
        poly = pad_poly(p)
        if tht or p.IsOnLayer(pcbnew.F_Cu): obst_F.append((poly, isg, fp.GetReference()))
        if tht or p.IsOnLayer(pcbnew.B_Cu): obst_B.append((poly, isg, fp.GetReference()))
vias = []
# existing (pre-routed) tracks are obstacles on every layer for vias
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        c0 = Point(t.GetPosition().x / MM, t.GetPosition().y / MM).buffer(t.GetWidth() / MM / 2)
        vias.append((t.GetPosition().x / MM, t.GetPosition().y / MM)); continue
    if t.GetNetname() == 'GND': continue
    ln = LineString([(t.GetStart().x / MM, t.GetStart().y / MM), (t.GetEnd().x / MM, t.GetEnd().y / MM)]).buffer(t.GetWidth() / MM / 2)
    obst_F.append((ln, False, 'trk')); obst_B.append((ln, False, 'trk'))
added = 0; failed = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname() != 'GND' or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        if fp.GetReference() in ('U2', 'C8', 'C6', 'C7', 'R5', 'R7', 'C10', 'C11', 'C12'):
            continue
        layer = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        obst = obst_F if layer == pcbnew.F_Cu else obst_B
        ppoly = pad_poly(p)
        c = ppoly.centroid
        best = None
        for dist in (0.55, 0.75, 1.0, 1.3, 1.7):
            for k in range(16):
                a = 2 * math.pi * k / 16
                # start from pad edge in this direction
                far = Point(c.x + 10 * math.cos(a), c.y + 10 * math.sin(a))
                edge_d = ppoly.exterior.distance(Point(c.x, c.y))
                # distance from centroid to boundary along direction
                lo, hi = 0.0, 10.0
                for _ in range(30):
                    mid = (lo + hi) / 2
                    if ppoly.contains(Point(c.x + mid * math.cos(a), c.y + mid * math.sin(a))): lo = mid
                    else: hi = mid
                r = hi + dist + VIA_D / 2
                vx, vy = c.x + r * math.cos(a), c.y + r * math.sin(a)
                vc = Point(vx, vy).buffer(VIA_D / 2 + CLR)
                if math.hypot(vx - CX, vy - CY) > RAD - 0.8: continue
                bad = False
                seg = LineString([(c.x, c.y), (vx, vy)]).buffer(0.15 + CLR)
                for poly, isg, ref in obst_F + obst_B:
                    if not isg and vc.intersects(poly): bad = True; break
                for poly, isg, ref in obst:
                    if not isg and seg.intersects(poly): bad = True; break
                    if isg and poly.contains(Point(vx, vy)): bad = True; break
                if bad: continue
                for (x2, y2) in vias:
                    if math.hypot(vx - x2, vy - y2) < VIA_D + 0.25: bad = True; break
                if bad: continue
                # stay out of other parts' courtyards (and never under sensors/SD/Nano headers)
                for ref, side, poly in crt:
                    if ref == fp.GetReference(): continue
                    if ref.startswith(('A', 'J', 'H')) and side == 'B': continue  # bottom THT bodies are fine for tented vias
                    if poly.contains(Point(vx, vy)): bad = True; break
                if bad: continue
                best = (vx, vy, dist); break
            if best: break
        if not best:
            failed.append(f'{fp.GetReference()}.{p.GetNumber()}'); continue
        vx, vy, _ = best
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(int(vx * MM), int(vy * MM)))
        v.SetWidth(int(VIA_D * MM)); v.SetDrill(int(VIA_DR * MM)); v.SetNet(gnd); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        b.Add(v)
        t = pcbnew.PCB_TRACK(b); t.SetLayer(layer); t.SetWidth(int(0.3 * MM)); t.SetNet(gnd)
        t.SetStart(p.GetPosition()); t.SetEnd(v.GetPosition()); b.Add(t)
        vias.append((vx, vy)); added += 1
        obst_F.append((Point(vx, vy).buffer(VIA_D / 2), True, 'via')); obst_B.append((Point(vx, vy).buffer(VIA_D / 2), True, 'via'))
print('GND fanout vias added:', added, 'failed:', failed)
pcbnew.SaveBoard(fn, b)
