import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from mpq import Archive
src = sys.argv[1]; out = sys.argv[2]
a = Archive(src)
os.makedirs(out, exist_ok=True)
lf = a.read("(listfile)")
names = lf.decode("latin1").split() if lf else []
for n in ["war3map.j","war3map.w3i","war3map.w3e","war3map.wpm","war3map.doo","war3mapUnits.doo","war3map.shd","war3map.mmp","war3mapMap.blp","war3map.wts","war3map.w3r","war3map.w3c","war3map.w3u","war3map.w3a","war3map.w3t","war3mapMisc.txt","war3map.imp","war3mapPreview.tga","war3mapExtra.txt","war3mapSkin.txt","war3map.wtg","war3map.wct","war3map.w3s", "scripts\\war3map.j"] + names:
    d = a.read(n)
    if d is not None:
        open(os.path.join(out, n.replace("\\","_")), "wb").write(d)
        print(n, len(d))
with open(src,"rb") as f: print("header:", f.read(64))
