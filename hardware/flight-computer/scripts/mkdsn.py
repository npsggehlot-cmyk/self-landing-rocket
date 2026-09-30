import pcbnew
b=pcbnew.LoadBoard('rocket_fc.kicad_pcb')
pcbnew.ExportSpecctraDSN(b,'rocket_fc.dsn')
s=open('rocket_fc.dsn').read()
s=s.replace('(layer In1.Cu\n      (type signal)','(layer In1.Cu\n      (type power)')
i=s.find('(plane GND (polygon In2.Cu')
if i>0:
    d=0;j=i
    while True:
        if s[j]=='(':d+=1
        elif s[j]==')':
            d-=1
            if d==0:break
        j+=1
    s=s[:i]+s[j+1:]
import re
# shrink the routing boundary so traces keep >=0.45 mm from the board edge
a=s.find('(boundary'); d=0; j=a
while True:
    if s[j]=='(': d+=1
    elif s[j]==')':
        d-=1
        if d==0: break
    j+=1
blk=s[a:j+1]
k=0.0
def sc(m):
    x=float(m.group(1)); y=float(m.group(2))
    cx,cy=100000.0,-100000.0; f=(35.0-0.5)/35.0
    return f' {cx+(x-cx)*f:.1f} {cy+(y-cy)*f:.1f}'
nums=re.sub(r' (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)', sc, blk.split('0',1)[1] if False else blk)
s=s[:a]+nums+s[j+1:]
open('rocket_fc_r.dsn','w').write(s); print('dsn ready')
