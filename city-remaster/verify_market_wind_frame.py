"""Read-only shader-frame checks against exported native instances (Blender Python)."""
from pathlib import Path
import hashlib
import json
import numpy as np
from apply_market_wind_frame import ROOT,REPORT,EDITS,SHADER


def main():
    manifest=json.loads(REPORT.read_text())
    checks={}
    for relative,edits in EDITS.items():
        raw=(ROOT/relative).read_bytes()
        checks[relative+' current hash']=hashlib.sha256(raw).hexdigest()==manifest['files'][relative]['after_sha256']
        newline='\r\n'if b'\r\n'in raw else '\n'
        restored=raw
        for old,new in reversed(edits):
            old=old.replace('\n',newline).encode();new=new.replace('\n',newline).encode()
            assert restored.count(new)==1
            restored=restored.replace(new,old,1)
        checks[relative+' bounded inverse']=hashlib.sha256(restored).hexdigest()==manifest['files'][relative]['before_sha256']
        if relative.endswith('tie_wind.vert'):
            # Everything from the original native projection through fragment
            # colour/UV/fog output is byte-for-byte identical.
            begin=b'  vec4 transformed = -camera[3];'
            checks[relative+' native projection unchanged']=raw[raw.index(begin):]==restored[restored.index(begin):]
    checks['source and active shader identical']=(ROOT/'engine-src'/SHADER).read_bytes()==(ROOT/'data'/SHADER).read_bytes()

    doc=json.loads((ROOT/'city-remaster/market-plants-native.json').read_text())
    instances={(v['geom'],v['tree'],v['instance']):v for v in doc['instance_inventory']if v['tree_type']=='tie_wind'}
    max_error=0.;max_orthogonality=0.;points=0
    for face in doc['faces']:
        if face['tree_type']!='tie_wind':continue
        inst=instances[(face['geom'],face['tree'],face['instance'])]
        columns=np.array(inst['matrix_columns'],dtype=np.float64)
        matrix=columns[:3,:3].T
        origin=np.array(inst['origin_m'])
        for vertex in face['vertices']:
            expected=matrix@np.array(vertex['local_p'])+origin
            max_error=max(max_error,float(np.linalg.norm(expected-vertex['p'])))
            points+=1
    # Anisotropic instance transforms plus representative wind shears: normals
    # must remain orthogonal to BOTH transformed surface tangent directions.
    for inst in instances.values():
        matrix=np.array(inst['matrix_columns'],dtype=np.float64)[:3,:3].T
        for amount in (-.14,0.,.14):
            wind=np.array([[1.,amount,.03],[0.,1.,0.],[-.02,amount*.6,1.]])
            world=wind@matrix
            for normal in (np.array([.3,.7,-.4]),np.array([0.,1.,0.])):
                normal/=np.linalg.norm(normal)
                tangent=np.cross(normal,[1.,0.,0.]);tangent/=np.linalg.norm(tangent)
                bitangent=np.cross(normal,tangent)
                transformed=np.linalg.inv(world).T@normal;transformed/=np.linalg.norm(transformed)
                for v in (world@tangent,world@bitangent):
                    max_orthogonality=max(max_orthogonality,abs(float(np.dot(v/np.linalg.norm(v),transformed))))
    checks['native local to world positions under 0.2mm']=points>0 and max_error<.0002
    checks['anisotropic and sheared normals stay perpendicular']=max_orthogonality<1e-12
    report={'status':'passed'if all(checks.values())else'failed','checks':checks,
            'native_points':points,'native_instances':len(instances),
            'max_position_error_m':max_error,'max_normal_tangent_dot':max_orthogonality,
            'native_visual_validation':False}
    (ROOT/'city-remaster/wind-material-frame-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    assert all(checks.values())


if __name__=='__main__':main()
