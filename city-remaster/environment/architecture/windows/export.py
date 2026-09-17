"""Export repeated hollow metal window frames; keep original glass as reference only."""
from pathlib import Path
from collections import defaultdict,Counter
import hashlib,json,subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BRIDGE=ROOT/'engine-build/bin/Release/palace_mesh_bridge.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def box(fs):
    pts=[v['p']for f in fs for v in f['vertices']]
    return [[fun(p[a]for p in pts)for a in range(3)]for fun in(min,max)]
def main():
    reports={}
    for level in ('wascitya','wascityb'):
        original=ROOT/f'city-remaster/sand-steps/{level}-surfaces.json';d=json.loads(original.read_text())
        window_proto=3 if level=='wascitya' else 10
        selected={(f['tree'],f['instance'])for f in d['faces']if f['tree_type']=='tie'and f['tree']==0 and f['proto']==window_proto and f['material']=='wascity-metal-segments'}
        family=Counter()
        for tree,inst in selected:
            fs=[f for f in d['faces']if f['tree_type']=='tie'and f['tree']==tree and f['instance']==inst]
            assert {f['material']for f in fs}<={'wascity-metal-segments','common-gray-dark'}
            assert sum(f['material']=='wascity-metal-segments'for f in fs)==36
            family[f'{tree}/{fs[0]["proto"]}']+=1
        source=Path(d['selection']['source_fr3']['path']);assert sha(source)==d['source_fr3']['sha256']
        selection={'level':level,'source_fr3':{**d['source_fr3'],'path':str(source)},'tree_types':['tie'],
                   'instances':[{'tree_type':'tie','tree':t,'instance':i}for t,i in sorted(selected)]}
        path=HERE/f'{level}-selection.json';path.write_text(json.dumps(selection,indent=2)+'\n')
        out=HERE/f'{level}-native.json'
        subprocess.run([str(BRIDGE),'--export-selected',str(source),str(path),str(out)],cwd=ROOT,check=True)
        refs={'level':level,'source_fr3':d['source_fr3'],'faces':[f for f in d['faces']if f['tree_type']=='tie'and f['material']in('wascity-window-glass-01','environment-ocean')]}
        (HERE/f'{level}-glass-reference.json').write_text(json.dumps(refs,separators=(',',':')))
        reports[level]={'source_fr3':selection['source_fr3'],'families':dict(family),'frames':len(selected),'export':str(out),'export_sha256':sha(out)}
        print(level,len(selected),'frames',dict(family),flush=True)
    (HERE/'selection-report.json').write_text(json.dumps(reports,indent=2)+'\n')
if __name__=='__main__':main()
