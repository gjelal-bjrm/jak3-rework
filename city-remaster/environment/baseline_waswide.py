"""Freeze WASWIDE's verified original before its first texture-only descendant.

This creates snapshots and absent variant copies, never changes the live level,
and leaves the shared variant registry for the explicit ENV deployment.
"""
from common import *

def main():
    level='waswide';rel=relative(level);folder=HERE/'baselines/waswide'
    manifest=folder/'baseline.json'
    if manifest.exists():
        record=read(manifest)
        for entry in record['snapshots']+record['variants']:
            assert sha(entry['path'])==entry['sha256'], 'Existing baseline copy changed'
        print(json.dumps({'status':'already_frozen','manifest':str(manifest),'sha256':record['output_sha256']}));return
    live=ROOT/'data'/rel;active=ROOT.parent.parent/'active/jak3/data'/rel
    live_hash=sha(live);active_hash=sha(active)
    # This initialisation is deliberately strict: a different live file must
    # have separately traced provenance, not be labelled an untouched original.
    assert live_hash==active_hash, 'WASWIDE differs from active original; trace that earlier change before baselining'
    folder.mkdir(parents=True,exist_ok=True)
    snapshots=[]
    for source,name,role in ((active,'active-original.fr3','active_original'),(live,'before.fr3','live_before')):
        dest=folder/name
        if dest.exists():assert sha(dest)==live_hash
        else:copy(source,dest)
        snapshots.append({'role':role,'path':str(dest),'sha256':sha(dest),'source_path':str(source),'source_sha256':sha(source)})
    variants=[]
    for variant in ('original','remaster-v1','remaster'):
        dest=ROOT/'variants'/variant/rel
        if dest.exists():assert sha(dest)==live_hash, 'Do not overwrite an existing variant'
        else:copy(active,dest)
        variants.append({'variant':variant,'path':str(dest),'sha256':sha(dest)})
    assert sha(live)==sha(active)==live_hash
    record={'status':'verified_original_baseline','level':level,'path':rel,'output_sha256':live_hash,
        'bytes':live.stat().st_size,'live_equals_active_original':True,
        'snapshots':snapshots,'variants':variants,'registry_updated':False,
        'scope':'Read-only live comparison and copied baseline; no geometry or texture changes'}
    write(manifest,record)
    print(json.dumps({'manifest':str(manifest),'sha256':live_hash,'live_changed':False,'registry_updated':False},indent=2))

if __name__=='__main__':main()
