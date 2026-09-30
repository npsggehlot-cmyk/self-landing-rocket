import pcbnew, sys, math, re, sexpdata
from sexpdata import Symbol as S
src = sys.argv[1] if len(sys.argv) > 1 else 'rocket_fc.kicad_pcb'
ses = sys.argv[2] if len(sys.argv) > 2 else 'rocket_fc.ses'
out = sys.argv[3] if len(sys.argv) > 3 else 'rocket_fc_routed.kicad_pcb'
b = pcbnew.LoadBoard(src)
# base board holds only the locked pre-routes; SES supplies everything else
t = sexpdata.loads(open(ses).read())
def find(e, name): return [x for x in e if isinstance(x, list) and x and x[0] == S(name)]
routes = find(t, 'routes')[0]
res = find(routes, 'resolution')[0]; scale = {'um': 1e-3, 'mil': 0.0254, 'mm': 1.0}[str(res[1])] / res[2]
M = lambda v: pcbnew.FromMM(v * scale)
layers = {b.GetLayerName(i): i for i in range(pcbnew.PCB_LAYER_ID_COUNT)}
nw = find(routes, 'network_out')[0]
import math as _m
LOCKED = [(t.GetNetname(), t.GetLayer(), t.GetStart().x / 1e6, t.GetStart().y / 1e6, t.GetEnd().x / 1e6, t.GetEnd().y / 1e6)
          for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.IsLocked()]
print('locked tracks:', len(LOCKED))
def on_seg(px, py, ax, ay, bx, by, tol=0.02):
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    u = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return _m.hypot(ax + u * dx - px, ay + u * dy - py) < tol
def covered(net, L, p, q):
    return any(n == net and l == L and on_seg(*p, a, b_, c, d) and on_seg(*q, a, b_, c, d) for n, l, a, b_, c, d in LOCKED)
ntr = nvia = 0
for n in find(nw, 'net'):
    name = str(n[1].value() if hasattr(n[1], 'value') else n[1])
    net = b.FindNet(name)
    for w in find(n, 'wire'):
        for p in find(w, 'path'):
            L = layers[str(p[1])]; wd = p[2]; pts = p[3:]
            xy = [(pts[i], pts[i+1]) for i in range(0, len(pts) - 1, 2)]
            for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
                if abs(x1 - x2) * scale < 0.005 and abs(y1 - y2) * scale < 0.005: continue
                if covered(name, L, (x1 * scale, -y1 * scale), (x2 * scale, -y2 * scale)): continue
                tr = pcbnew.PCB_TRACK(b); tr.SetLayer(L); tr.SetWidth(M(wd))
                tr.SetStart(pcbnew.VECTOR2I(M(x1), M(-y1))); tr.SetEnd(pcbnew.VECTOR2I(M(x2), M(-y2)))
                tr.SetNet(net); b.Add(tr); ntr += 1
    for v in find(n, 'via'):
        m = re.search(r'_(\d+):(\d+)_um', str(v[1]))
        dia, drl = int(m.group(1)) / 1000, int(m.group(2)) / 1000
        via = pcbnew.PCB_VIA(b); via.SetPosition(pcbnew.VECTOR2I(M(v[2]), M(-v[3])))
        via.SetWidth(pcbnew.FromMM(dia)); via.SetDrill(pcbnew.FromMM(drl)); via.SetNet(net)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); b.Add(via); nvia += 1
print('tracks', ntr, 'vias', nvia)
# ground pours on all copper layers
CX = CY = 100; RAD = 35
gnd = b.FindNet('GND')
have = {pcbnew.In1_Cu, pcbnew.In2_Cu}   # created by gen_pcb.py
for L in [pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu]:
    if L in have: continue
    z = pcbnew.ZONE(b); z.SetLayer(L); z.SetNet(gnd); z.Outline().NewOutline()
    for i in range(96):
        a = 2 * math.pi * i / 96
        z.Outline().Append(pcbnew.FromMM(CX + (RAD - 0.4) * math.cos(a)), pcbnew.FromMM(CY + (RAD - 0.4) * math.sin(a)))
    z.SetMinThickness(pcbnew.FromMM(0.2)); z.SetLocalClearance(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.3)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.45))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)
filler = pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
b.BuildConnectivity()
print('unconnected items:', b.GetConnectivity().GetUnconnectedCount(False))
pcbnew.SaveBoard(out, b)
