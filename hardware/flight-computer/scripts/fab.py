# Regenerate every fabrication output from rocket_fc.kicad_pcb
import pcbnew, subprocess, csv, os, re, shutil, zipfile, collections
os.makedirs('fab/gerbers', exist_ok=True)
for f in os.listdir('fab/gerbers'): os.remove(os.path.join('fab/gerbers', f))
PCB = 'rocket_fc.kicad_pcb'
L = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts'
subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers', '-l', L, '--subtract-soldermask', '-o', 'fab/gerbers/', PCB], check=True, capture_output=True)
subprocess.run(['kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th', '--excellon-units', 'mm',
                '-o', 'fab/gerbers/', PCB], check=True, capture_output=True)
for z, pat in (('fab/RocketFC_Gerbers.zip', None), ('fab/RocketFC_Gerbers_min.zip', r'Paste|job')):
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir('fab/gerbers')):
            if pat and re.search(pat, f): continue
            zf.write(os.path.join('fab/gerbers', f), f)
# JLC rotation offsets (kicad-jlcpcb-tools convention); JLC also reviews placement ("Confirm parts placement")
ROT = [(r'^SOT-223', 180), (r'^SOT-23', 180), (r'^SOIC-', 270)]   # CP_Elec checked in JLC's 3D viewer: no offset
THT_ROT = [(r'^PinHeader_1x03', 90), (r'^AMASS_XT30PW-F', 180)]   # verified against JLC's 3D placement preview
b = pcbnew.LoadBoard(PCB)
SMD_ONLY = os.environ.get('SMD_ONLY') == '1'; SUF = '_SMD_only' if SMD_ONLY else ''
bom = collections.OrderedDict(); cpl = []; mpn = {}
for fp in sorted(b.GetFootprints(), key=lambda f: (re.sub(r'\d', '', f.GetReference()), int(re.sub(r'\D', '', f.GetReference()) or 0))):
    lcsc = fp.GetProperty('LCSC') if fp.HasProperty('LCSC') else ''
    if not lcsc: continue          # only the Nano itself (A1), jumper, holes and test points are left off
    if SMD_ONLY and fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE: continue
    name = fp.GetFPID().GetLibItemName().wx_str()
    key = (name, lcsc)
    bom.setdefault(key, []).append((fp.GetReference(), fp.GetValue()))
    mpn[key] = fp.GetProperty('MPN') if fp.HasProperty('MPN') else ''
    rot = fp.GetOrientationDegrees()
    tht = bool(fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE)
    if not tht:
        for pat, off in ROT:
            if re.match(pat, name): rot += off; break
        pos = fp.GetPosition(); x, y = pos.x / 1e6, pos.y / 1e6
    else:                          # through-hole: use the body (courtyard) centre, not pin 1
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        c = (cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)).Centre(); x, y = c.x / 1e6, c.y / 1e6
        for pat, off in THT_ROT:
            if re.match(pat, name): rot += off; break
        if name.startswith('AMASS_XT30PW-F'):   # JLC's 3D model origin sits 3.3 mm closer to the pins than the courtyard centre
            px = sum(p.GetPosition().x for p in fp.Pads() if p.GetNumber()) / 2e6; py = sum(p.GetPosition().y for p in fp.Pads() if p.GetNumber()) / 2e6
            d = ((px - x) ** 2 + (py - y) ** 2) ** 0.5; x += (px - x) / d * 3.3; y += (py - y) / d * 3.3
    cpl.append([fp.GetReference(), f'{x:.3f}mm', f'{-y:.3f}mm', 'Bottom' if fp.IsFlipped() else 'Top', f'{rot % 360:g}'])
# Arduino Nano sockets: two 1x15 female headers under the Nano's pin rows (bottom side); the Nano itself is not assembled
a1 = b.FindFootprintByReference('A1')
for i, row in [] if SMD_ONLY else enumerate(sorted({round(p.GetPosition().y / 1e6, 2) for p in a1.Pads()})):
    xs = [p.GetPosition().x / 1e6 for p in a1.Pads() if abs(p.GetPosition().y / 1e6 - row) < 0.05]
    ref = f'A1_S{i + 1}'
    bom.setdefault(('PinSocket_1x15_P2.54mm_Vertical', 'C41417327'), []).append((ref, 'Nano socket 1x15 female 2.54mm'))
    cpl.append([ref, f'{(min(xs) + max(xs)) / 2:.3f}mm', f'{-row:.3f}mm', 'Bottom', '0'])
with open(f'fab/RocketFC_BOM_JLCPCB{SUF}.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
    for (name, lcsc), items in bom.items():
        vals = {v for _, v in items}
        w.writerow([vals.pop() if len(vals) == 1 else (mpn[(name, lcsc)] or name), ','.join(r for r, _ in items), name, lcsc])
with open(f'fab/RocketFC_CPL_JLCPCB{SUF}.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation']); w.writerows(cpl)
print('gerbers', len(os.listdir('fab/gerbers')), 'bom lines', len(bom), 'placements', len(cpl))
