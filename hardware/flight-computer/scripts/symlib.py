import sexpdata, os, copy
from sexpdata import Symbol as S
SYMDIR='/usr/share/kicad/symbols'
_cache={}
def load_lib(lib):
    if lib not in _cache:
        _cache[lib]=sexpdata.loads(open(f'{SYMDIR}/{lib}.kicad_sym').read())
    return _cache[lib]
def find(tree,name):
    for e in tree[1:]:
        if isinstance(e,list) and e and e[0]==S('symbol') and e[1]==name: return e
def get_symbol(libid):
    lib,name=libid.split(':')
    t=load_lib(lib); sym=copy.deepcopy(find(t,name))
    ext=[e for e in sym if isinstance(e,list) and e and e[0]==S('extends')]
    if ext:
        parent=get_symbol(lib+':'+ext[0][1])
        # parent sub-units renamed
        pname=parent[1]
        props={e[1]:e for e in sym if isinstance(e,list) and e and e[0]==S('property')}
        new=[S('symbol'),name]
        for e in parent[2:]:
            if isinstance(e,list) and e and e[0]==S('property') and e[1] in props:
                new.append(props.pop(e[1]))
            elif isinstance(e,list) and e and e[0]==S('symbol'):
                e=copy.deepcopy(e); e[1]=e[1].replace(pname,name,1); new.append(e)
            else: new.append(e)
        for p in props.values(): new.append(p)
        sym=new
    return sym
def pins(sym):
    out=[]
    def walk(e,unit):
        for x in e:
            if isinstance(x,list) and x and x[0]==S('symbol'):
                parts=x[1].rsplit('_',2); walk(x,int(parts[-2]))
            elif isinstance(x,list) and x and x[0]==S('pin'):
                at=[y for y in x if isinstance(y,list) and y[0]==S('at')][0]
                ln=[y for y in x if isinstance(y,list) and y[0]==S('length')][0][1]
                nm=[y for y in x if isinstance(y,list) and y[0]==S('name')][0][1]
                num=[y for y in x if isinstance(y,list) and y[0]==S('number')][0][1]
                hidden=any(y==S('hide') for y in x)
                out.append(dict(unit=unit,type=str(x[1]),name=nm,num=num,x=at[1],y=at[2],ang=at[3] if len(at)>3 else 0,len=ln,hidden=hidden))
    walk(sym,0); return out
