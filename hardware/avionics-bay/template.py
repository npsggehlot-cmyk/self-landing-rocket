import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as pa
import avbay as A
W, H = 279.4, 215.9                       # US letter landscape, mm
C = 3.14159265 * A.TUBE_OD                # wrap length on the tube OD
fig = plt.figure(figsize=(W / 25.4, H / 25.4)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')
x0, y0 = 20, 45                           # template origin (left edge = 225 deg, top = forward face of bay)
L = A.ZTOP
def X(ang): return x0 + ((ang - 225) % 360) / 360 * C
def Y(z): return y0 + (L - z)
ax.add_patch(pa.Rectangle((x0, y0), C, L, fill=False, lw=0.6))
ax.text(x0 + C - 1, y0 - 2, 'edges meet here (239.4 mm)', fontsize=6, color='0.4', ha='right')
for ang, lab in ((270, '6 o\'clock\n(e-match terminals)'), (0, '3 o\'clock\n(Nano USB)'), (90, '12 o\'clock\n(power switch)'), (180, '9 o\'clock\n(ARM plug)')):
    ax.plot([X(ang)] * 2, [y0 - 3, y0 + L + 3], lw=0.3, ls=(0, (3, 3)), color='0.4')
    ax.text(X(ang), y0 + L + 9, lab, ha='center', va='top', fontsize=7)
    for z in (A.RING_H / 2, A.ZTOP - A.RING_H / 2):                       # 8x M3 screw holes
        ax.add_patch(pa.Circle((X(ang), Y(z)), 1.6, fill=False, lw=0.6)); ax.plot([X(ang) - 3, X(ang) + 3], [Y(z)] * 2, lw=0.3, color='k'); ax.plot([X(ang)] * 2, [Y(z) - 3, Y(z) + 3], lw=0.3, color='k')
def win(ang, zc, w, h, lab):
    ax.add_patch(pa.Rectangle((X(ang) - w / 2, Y(zc) - h / 2), w, h, fill=False, lw=0.8, hatch='///', color='0.3'))
    ax.text(X(ang) + w / 2 + 1.5, Y(zc), lab, fontsize=6.5, va='center')
win(0, 18.0, 13, 10, 'USB cut-out 13 x 10')
win(180, 27.0, 12, 8, 'ARM plug cut-out 12 x 8')
win(90, A.ZT + 2.2, 9, 5, 'switch slot 9 x 5')
ax.text(x0, y0 - 6, 'FORWARD (nose) end of the bay', fontsize=8, weight='bold')
ax.text(x0, y0 + L + 2.5, 'AFT end of the bay', fontsize=8, weight='bold', va='top')
ax.text(x0, 12, 'RocketFC v2 avionics bay - tube drilling template (Apogee 3.0" / 74 mm body tube, OD 76.2 mm)', fontsize=11, weight='bold')
ax.text(x0, 19, 'Print at 100 % (no "fit to page"), check the 50 mm bar, cut on the outline, wrap it around the tube printed side out, FORWARD edge toward the nose, left and right edges meeting.\n'
        '8 small circles = 3.2 mm drill for M3 x 8 button-head screws into the heat-set inserts. Hatched boxes = openings to cut (USB, ARM plug, power switch).\n'
        'Slide the bay in from the forward end with the power switch at 12 o\'clock and line its screw holes up with the tube before drilling full size.', fontsize=7, va='top')
ax.plot([x0, x0 + 50], [H - 12, H - 12], lw=1.5, color='k'); ax.text(x0 + 52, H - 12, '50 mm check bar', fontsize=7, va='center')
fig.savefig('AvBay_Tube_Drill_Template.pdf'); fig.savefig('AvBay_Tube_Drill_Template.png', dpi=110)
print('C', round(C, 1))
