import pcbnew, json, math, sys, design
from collections import defaultdict
M = pcbnew.FromMM
CX, CY, RAD = 100.0, 100.0, 35.0
FPDIR = '/usr/share/kicad/footprints/'
LOCAL = {'TerminalBlock_WAGO_local': 'lib/TerminalBlock_WAGO_local.pretty'}
from placement import PLACE

sym_uuids = json.load(open('sym_uuids.json'))

# merge multi-unit parts
parts = {}
for p in design.PARTS:
    if p['ref'] in parts:
        parts[p['ref']]['pins'].update(p['pins'])
    else:
        q = dict(p); q['pins'] = dict(p['pins']); parts[p['ref']] = q

board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
ds = board.GetDesignSettings()
ds.SetBoardThickness(M(1.6))

nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); nets[name] = n
    return nets[name]
for p in parts.values():
    for v in p['pins'].values():
        if v != 'NC': net(v)

fps = {}
for ref, p in parts.items():
    lib, name = p['fp'].split(':')
    path = LOCAL.get(lib, FPDIR + lib + '.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        sys.exit(f'missing footprint {p["fp"]}')
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref); fp.SetValue(p['value'])
    fp.SetPath(pcbnew.KIID_PATH('/' + sym_uuids[ref]))
    try:
        fp.SetProperty('Sheetfile', 'rocket_fc.kicad_sch'); fp.SetProperty('Sheetname', '')
        if p['mpn']: fp.SetProperty('MPN', p['mpn'])
        if p['lcsc']: fp.SetProperty('LCSC', p['lcsc'])
    except Exception as e:
        pass
    for pad in fp.Pads():
        n = p['pins'].get(pad.GetNumber())
        if n and n != 'NC':
            pad.SetNet(net(n))
    board.Add(fp)
    fps[ref] = fp

def place(ref, dx, dy, rot=0, side='F'):
    """Anchor every part at the centre of its courtyard bounding box."""
    fp = fps[ref]
    fp.SetOrientationDegrees(0)
    if side == 'B' and not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), False)
    fp.SetOrientationDegrees(rot)
    fp.BuildCourtyardCaches()
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    c = bb.Centre()
    off = fp.GetPosition() - c
    fp.SetPosition(pcbnew.VECTOR2I(M(CX + dx), M(CY + dy)) + off)

missing = [r for r in fps if r not in PLACE]
if missing:
    print('UNPLACED:', missing)
for ref, v in PLACE.items():
    place(ref, *v)

# board outline: circle
c = pcbnew.PCB_SHAPE(board); c.SetShape(pcbnew.SHAPE_T_CIRCLE); c.SetLayer(pcbnew.Edge_Cuts)
c.SetCenter(pcbnew.VECTOR2I(M(CX), M(CY))); c.SetEnd(pcbnew.VECTOR2I(M(CX + RAD), M(CY))); c.SetWidth(M(0.1))
board.Add(c)

def text(s, x, y, size=1.0, layer=pcbnew.F_SilkS, angle=0, bold=False):
    t = pcbnew.PCB_TEXT(board); t.SetText(s); t.SetPosition(pcbnew.VECTOR2I(M(CX + x), M(CY + y)))
    t.SetLayer(layer); t.SetTextSize(pcbnew.VECTOR2I(M(size), M(size))); t.SetTextThickness(M(size * 0.15 if not bold else size*0.2))
    t.SetTextAngleDegrees(angle)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Cu): t.SetMirrored(True)
    board.Add(t)
from placement import SILK
for args in SILK:
    text(*args)

def circle_poly(r, n=96):
    pts = pcbnew.VECTOR_VECTOR2I()
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append(pcbnew.VECTOR2I(M(CX + r * math.cos(a)), M(CY + r * math.sin(a))))
    return pts
def add_zone(layer, netname, r=RAD - 0.4, prio=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer); z.SetNet(net(netname))
    z.Outline().NewOutline()
    for p in circle_poly(r):
        z.Outline().Append(p.x, p.y)
    z.SetMinThickness(M(0.2)); z.SetLocalClearance(M(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(M(0.3)); z.SetThermalReliefSpokeWidth(M(0.45))
    z.SetAssignedPriority(prio)
    board.Add(z)
    return z
if '--no-zones' not in sys.argv:
    add_zone(pcbnew.In1_Cu, 'GND')
    add_zone(pcbnew.In2_Cu, 'GND')
pcbnew.SaveBoard('rocket_fc.kicad_pcb', board)
print('saved', len(fps), 'footprints,', len(nets), 'nets')
