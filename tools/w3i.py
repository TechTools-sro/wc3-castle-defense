import struct, sys
class R:
    def __init__(s, b): s.b=b; s.p=0
    def i(s): v=struct.unpack_from('<i',s.b,s.p)[0]; s.p+=4; return v
    def f(s): v=struct.unpack_from('<f',s.b,s.p)[0]; s.p+=4; return v
    def c(s,n=1): v=s.b[s.p:s.p+n]; s.p+=n; return v
    def s(s_):
        e=s_.b.index(b'\0',s_.p); v=s_.b[s_.p:e]; s_.p=e+1; return v.decode('utf8','replace')
def parse(b):
    r=R(b); d={}
    d['ver']=r.i(); d['saves']=r.i(); d['editor']=r.i()
    d['name']=r.s(); d['author']=r.s(); d['desc']=r.s(); d['rec']=r.s()
    d['cambounds']=[r.f() for _ in range(8)]
    d['camcomp']=[r.i() for _ in range(4)]
    d['playW']=r.i(); d['playH']=r.i(); d['flags']=hex(r.i()); d['tileset']=r.c()
    d['loadscr_num']=r.i(); d['loadscr_model']=r.s(); d['ls_text']=r.s(); d['ls_title']=r.s(); d['ls_sub']=r.s()
    d['gamedata']=r.i(); d['pro_path']=r.s(); d['pro_text']=r.s(); d['pro_title']=r.s(); d['pro_sub']=r.s()
    d['fog']=r.i(); d['fogz']=(r.f(),r.f(),r.f()); d['fogc']=r.c(4); d['weather']=r.c(4); d['soundenv']=r.s(); d['light']=r.c(); d['water']=r.c(4)
    n=r.i(); d['players']=[]
    for _ in range(n):
        d['players'].append(dict(num=r.i(),type=r.i(),race=r.i(),fixed=r.i(),name=r.s(),x=r.f(),y=r.f(),allylow=hex(r.i()),allyhigh=hex(r.i())))
    n=r.i(); d['forces']=[]
    for _ in range(n): d['forces'].append(dict(flags=hex(r.i()),mask=hex(r.i()),name=r.s()))
    n=r.i(); d['upgrades']=[(r.i(),r.c(4),r.i(),r.i()) for _ in range(n)]
    n=r.i(); d['tech']=[(r.i(),r.c(4)) for _ in range(n)]
    n=r.i(); d['rut']=n
    assert n==0, 'random unit tables present'
    n=r.i(); d['rit']=n
    if n==0: pass
    d['consumed']=r.p; d['total']=len(b)
    return d
if __name__=='__main__':
    import pprint; pprint.pprint(parse(open(sys.argv[1],'rb').read()), width=150)
