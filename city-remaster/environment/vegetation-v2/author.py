"""Whole-city cactus/grass author. Blender only; never deploy or edit live FR3."""
from pathlib import Path
from collections import defaultdict
import sys,json,math,random,hashlib,argparse
import bpy
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parent
sys.path[:0]=[str(ROOT/'models-v1'),str(CITY)]
from blender_common import NativeMesh,reset,render_asset
from author_shrubs import Tuft,bezier
GRASS='market-shrub-orange-v1';GREEN='city-cactus-green-v2'

def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def bounds(points):return [[min(p[a]for p in points)for a in range(3)],[max(p[a]for p in points)for a in range(3)]]

def material(name,path):
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;l=m.node_tree.links;s=n.get('Principled BSDF');s.inputs['Roughness'].default_value=.73
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True);tex.image.pack()
    col=n.new('ShaderNodeVertexColor');col.layer_name='LeafShade'
    mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
    l.new(tex.outputs['Color'],mul.inputs[1]);l.new(col.outputs['Color'],mul.inputs[2]);l.new(mul.outputs['Color'],s.inputs['Base Color'])
    return m

class StreetTuft(Tuft):
    def grow(self):
        phase=self.rng.uniform(0,math.tau)
        # Three irregular nested groups. All blades are new closed curved
        # volumes; eight curved spans avoid the angular first prototype.
        for tier,count in enumerate((7,9,5)):
            for i in range(count):
                rng=self.rng;angle=phase+i*2.399963+(.39*tier)+rng.uniform(-.24,.24)
                root=Vector((rng.uniform(-.08,.08),-.08+rng.uniform(0,.008),rng.uniform(-.08,.08)))
                if tier==0:height,reach,drop,width=rng.uniform(1.65,2.13),rng.uniform(.25,.7),rng.uniform(0,.12),rng.uniform(.030,.046)
                elif tier==1:height,reach,drop,width=rng.uniform(1.15,1.65),rng.uniform(.71,1.15),rng.uniform(.10,.34),rng.uniform(.042,.064)
                else:height,reach,drop,width=rng.uniform(.65,1.03),rng.uniform(.9,1.25),rng.uniform(.27,.49),rng.uniform(.025,.043)
                self.leaf(root,angle,reach,height,drop,width,steps=8)

class Cactus:
    def __init__(self,asset,matrix,seed):
        self.asset=asset;self.matrix=matrix;self.rng=random.Random(seed)
        self.vertices=[];self.faces=[];self.uvs=[];self.shades=[];self.mats=[]
    def v(self,p,uv,shade=1):
        self.vertices.append(Vector(p));self.uvs.append(uv);self.shades.append(shade);return len(self.vertices)-1
    def face(self,vs,mat=0):self.faces.append(vs);self.mats.append(mat)
    def sphere(self,c,r,mat=0,rows=9,sectors=32,phase=0):
        c=Vector(c);bottom=self.v(c+Vector((0,-r[1],0)),(.5,1),.83);rings=[]
        for j in range(1,rows):
            lat=-math.pi*.5+math.pi*j/rows;ring=[]
            for k in range(sectors):
                a=math.tau*k/sectors;rib=1+(.072*math.cos(a*8+phase) if mat==0 else 0)
                p=c+Vector((r[0]*math.cos(lat)*math.cos(a)*rib,r[1]*math.sin(lat),r[2]*math.cos(lat)*math.sin(a)*rib))
                st=(k/sectors,1-j/rows) if mat==0 else (.5,.5)
                ring.append(self.v(p,st,.88+.12*j/rows))
            rings.append(ring)
        top=self.v(c+Vector((0,r[1],0)),(.5,0)if mat==0 else(.5,.5))
        for k in range(sectors):self.face((bottom,rings[0][k],rings[0][(k+1)%sectors]),mat)
        for a,b in zip(rings,rings[1:]):
            for k in range(sectors):n=(k+1)%sectors;self.face((a[k],b[k],b[n],a[n]),mat)
        for k in range(sectors):self.face((rings[-1][k],top,rings[-1][(k+1)%sectors]),mat)
    def cone(self,root,tip,r=.003):
        root,tip=Vector(root),Vector(tip);axis=(tip-root).normalized();side=axis.cross(Vector((0,1,0)))
        if side.length<.01:side=axis.cross(Vector((1,0,0)))
        side.normalize();other=axis.cross(side).normalized();ids=[]
        for i in range(3):a=math.tau*i/3;ids.append(self.v(root+(side*math.cos(a)+other*math.sin(a))*r,(.13,.08),.96))
        t=self.v(tip,(.13,.08));self.face(tuple(reversed(ids)))
        for k in range(3):self.face((ids[k],ids[(k+1)%3],t))
    def petal(self,c,a,length,width,lift):
        d=Vector((math.cos(a),0,math.sin(a)));side=Vector((-d.z,0,d.x));c=Vector(c)
        c += d*.007
        start_face=len(self.faces)
        controls=[c,c+d*(length*.26)+Vector((0,lift*.7,0)),c+d*(length*.78)+Vector((0,lift*1.4,0)),c+d*length+Vector((0,lift*.72,0))]
        rows=[]
        for j in range(6):
            t=j/5;p=bezier(controls,t);uv=(.5+.42*t*math.cos(a),.5+.42*t*math.sin(a))
            if j==5:rows.append([self.v(p,uv)]);continue
            w=width*(.12+.88*math.sin(math.pi*t)**.7)*(1-t)**.17
            rows.append([self.v(p-side*w,uv,.9),self.v(p+Vector((0,w*.13,0)),uv),self.v(p+side*w,uv,.9),self.v(p-Vector((0,w*.10,0)),uv,.84)])
        for j in range(5):
            for k in range(4):
                n=(k+1)%4
                self.face((rows[j][k],rows[j+1][0],rows[j][n]) if j==4 else(rows[j][k],rows[j+1][k],rows[j+1][n],rows[j][n]),1)
        self.face(tuple(rows[0]),1)
        # Closed petals must face outwards. Their ring traversal is opposite
        # to the cushion latitude rings; do not inherit that winding.
        for i in range(start_face,len(self.faces)):self.faces[i]=tuple(reversed(self.faces[i]))
    def grow(self):
        # Rounded, asymmetrical cactus cushions replace the old intersecting
        # box pads; seven separate upward-curved flowers have actual thickness.
        lobes=[((-.39,.38,-.48),(.38,.38,.33)),((.14,.44,-.35),(.44,.44,.36)),
               ((.64,.28,-.60),(.41,.28,.29)),((.47,.33,.20),(.40,.33,.32)),
               ((-.37,.23,.22),(.37,.23,.28)),((1.04,.16,-.62),(.25,.16,.23)),
               ((-.68,.15,-.98),(.27,.15,.22))]
        for number,(c,r) in enumerate(lobes):
            self.sphere(c,r,phase=self.rng.random()*math.tau)
            for j in range(3):
                lat=-.35+j*.46
                for k in range(9):
                    a=k*math.tau/9+j*.28;normal=Vector((math.cos(lat)*math.cos(a),math.sin(lat),math.cos(lat)*math.sin(a)))
                    base=Vector(c)+Vector((normal.x*r[0],normal.y*r[1],normal.z*r[2]))*1.035
                    self.cone(base,base+normal*self.rng.uniform(.025,.041))
            centre=Vector(c)+Vector((0,r[1]*.95,0));angle=self.rng.random()*math.tau
            for k in range(8):self.petal(centre,angle+k*math.tau/8,.205 if number<5 else .16,.061,.12)
            for k in range(5):self.petal(centre+Vector((0,.022,0)),angle+.4+k*math.tau/5,.072,.028,.091)
            self.sphere(centre+Vector((0,.034,0)),(.042,.029,.042),1,rows=5,sectors=10)
        # Keep the original complete object's dimensions and contact footprint.
        # These affine limits are applied to an entirely new organic mesh.
        old=[self.matrix.inverted()@Vector(v['p'])for f in self.asset.faces for v in f['vertices']]
        lo,hi=bounds(old);nlo,nhi=bounds(self.vertices)
        for i,p in enumerate(self.vertices):self.vertices[i]=Vector([lo[a]+(p[a]-nlo[a])/(nhi[a]-nlo[a])*(hi[a]-lo[a])for a in range(3)])
    def finish(self,mats):
        mesh=bpy.data.meshes.new(self.asset.obj.name+' sculpted cactus cushions and flowers')
        mesh.from_pydata([self.asset.local(self.matrix@p)for p in self.vertices],[],self.faces)
        for m in mats:mesh.materials.append(m)
        uv=mesh.uv_layers.new(name='UVMap');col=mesh.color_attributes.new(name='LeafShade',type='FLOAT_COLOR',domain='POINT')
        for i,s in enumerate(self.shades):col.data[i].color=(s,s,s,1)
        for polygon,mi in zip(mesh.polygons,self.mats):
            polygon.material_index=mi;polygon.use_smooth=True
            for loop,vi in zip(polygon.loop_indices,polygon.vertices):uv.data[loop].uv=self.uvs[vi]
        mesh.update();self.asset.obj.data=mesh;return mesh

def records(asset,shades,texture_by_mat):
    mesh=asset.obj.data;mesh.calc_loop_triangles();sources={};cache={}
    for mi,mat in enumerate(asset.materials):
        verts=[v for f in asset.faces if f['material']==mat for v in f['vertices']]
        kd=KDTree(len(verts))
        for i,v in enumerate(verts):kd.insert(asset.local(v['p']),i)
        kd.balance();sources[mi]=(verts,kd)
    vertices=[]
    for v in mesh.vertices:
        p=[round(x,6)for x in asset.world(v.co)];n=v.normal
        vertices.append((p,[round(n.x,6),round(n.z,6),round(-n.y,6)]))
    added=[]
    for tri in mesh.loop_triangles:
        mi=tri.material_index;source,kd=sources[mi];base=next(f for f in asset.faces if f['material']==asset.materials[mi])
        row={k:base[k]for k in ('tree_type','geom','tree','draw','group')};row['vertices']=[]
        if texture_by_mat[mi]:row['texture']=texture_by_mat[mi]
        for vi,loop in zip(tri.vertices,tri.loops):
            key=(vi,mi)
            if key not in cache:
                _,index,_=kd.find(mesh.vertices[vi].co);native=source[index];color=native['color']
                p,n=vertices[vi];shade=shades[vi]
                cache[key]={'p':p,'normal':n,'color_indices':[color,color,color],'color_weights':[1,0,0],
                            'rgba':[max(0,min(255,round(x*shade)))for x in native['rgba'][:3]]+native['rgba'][3:]}
            uv=mesh.uv_layers.active.data[loop].uv
            row['vertices'].append({**cache[key],'uv':[round(uv.x*4096,5),round((1-uv.y)*4096,5)]})
        added.append(row)
    return added

def ground_contact(asset):
    """Keep exact native ground contact, including strongly inclined plants.

    Local reconstruction preserves the native root and matrix. Rounded shapes
    can nevertheless protrude lower after rotation, so gently deform only the
    lowest world-space band rather than translating the plant or its top.
    """
    old_min=min(v['p'][1]for f in asset.faces for v in f['vertices'])
    points=[asset.world(v.co)for v in asset.obj.data.vertices]
    low=min(p[1]for p in points);delta=old_min-low
    band=max(.5,abs(delta)*3.0)
    for vertex,p in zip(asset.obj.data.vertices,points):
        t=max(0.,1.-(p[1]-low)/band)
        p[1]+=delta*t*t
        vertex.co=asset.local(p)
    asset.obj.data.update()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');parser.add_argument('--level',choices=['wascitya','wascityb'])
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else[])
    for level in ([args.level]if args.level else['wascitya','wascityb']):
        reset();d=json.loads((HERE/(level+'-native.json')).read_text());groups=defaultdict(list)
        for f in d['faces']:groups[f['instance']].append(f)
        inv={i['instance']:i for i in d['instance_inventory']};selected=sorted(groups)
        if args.sample:selected=[next(i for i in selected if len(groups[i])==38),next(i for i in selected if len(groups[i])==228)]
        grassmat=material(GRASS,CITY/'market-shrub-orange-hd.png')
        greenmat=material(GREEN,HERE/'cactus-skin-hd.png')
        flower=material('native pink cactus flowers',ROOT/'data/decompiler_out/jak3/textures/wascitya-vis-shrub/wascity-cactus-flower.png')
        textures=[{'name':GRASS,'page':'remaster-market-plants','width':1254,'height':1254,'rgba_file':str(CITY/'market-shrub-orange-hd.rgba')},
                  {'name':GREEN,'page':'remaster-city-vegetation','width':1254,'height':1254,'rgba_file':str(HERE/'cactus-skin-hd.rgba')}]
        for t in textures:assert Path(t['rgba_file']).stat().st_size==t['width']*t['height']*4
        suffix='-sample'if args.sample else'';outpath=HERE/(level+suffix+'-patch.json')
        removed=[{**{k:f[k]for k in ('tree_type','geom','tree','draw','group','stream_index')},'original_positions':[v['p']for v in f['vertices']]}for i in selected for f in groups[i]]
        header={'level':level,'source_fr3':d['source_fr3'],'description':'Complete native street grass and flowering cactus replacements; preserve accepted palms and market shrubs','preserve_bvh':True,'new_textures':textures,'remove':removed}
        report={'level':level,'source_fr3':d['source_fr3'],'source_export_sha256':sha(HERE/(level+'-native.json')),'instances':[],
                'grass_material':GRASS,'grass_uv':'native V4096 root -> V0 tip, monotone; bases anchored for passage bending/recovery',
                'preserved_palms':True,'preserved_market_69_shrubs':True,'live_modified':False,'native_visual_validation':False}
        first=True;seen=set();origin=Vector((2100,20,-160))
        with outpath.open('w')as out:
            out.write(json.dumps(header,separators=(',',':'))[:-1]+',"add":[')
            for number,i in enumerate(selected):
                fs=groups[i];instance=inv[i];cols=instance['matrix_columns'];foot=instance['origin_m']
                matrix=Matrix([[cols[c][r]for c in range(3)]+[foot[r]]for r in range(3)]+[[0,0,0,1]])
                isgrass=len(fs)==38;kind='grass'if isgrass else'cactus';assert isgrass or len(fs)==228
                a=NativeMesh(level+' '+kind+' '+str(i),fs,foot)
                if isgrass:
                    builder=StreetTuft(a,matrix,random.Random(i*797+(33 if level=='wascitya' else 71)));builder.grow();builder.finish(grassmat);tx=[GRASS]
                else:
                    builder=Cactus(a,matrix,i*541);builder.grow();builder.finish([greenmat,flower])
                    # NativeMesh sorts cactus-flower before cactus-green; our
                    # authored mesh slots are explicitly green then flower.
                    a.materials=['wascity-cactus-green','wascity-cactus-flower'];tx=[GREEN,None]
                ground_contact(a)
                added=records(a,builder.shades,tx)
                if not first:out.write(',')
                out.write(json.dumps(added,separators=(',',':'))[1:-1]);first=False
                oldpoints=[v['p']for f in fs for v in f['vertices']];points=[a.world(v.co)for v in a.obj.data.vertices]
                oldbounds=bounds(oldpoints);newbounds=bounds(points)
                radius=lambda ps:max(math.hypot(p[0]-foot[0],p[2]-foot[2])for p in ps)
                a.obj['native_instance']=i;a.obj['native_root_m']=foot;a.obj['native_matrix_columns']=json.dumps(cols);a.obj['type']=kind
                delta=Vector(foot)-origin;a.obj.location=(delta.x,-delta.z,delta.y)
                report['instances'].append({'instance':i,'kind':kind,'origin_m':foot,'matrix_columns':cols,'original_triangles':len(fs),'triangles':len(added),
                    'original_bounds':oldbounds,'authored_bounds':newbounds,'radius_ratio':radius(points)/radius(oldpoints),'base_y_change_m':newbounds[0][1]-oldbounds[0][1],
                    'vertices':len(a.obj.data.vertices),'closed_components':builder.leaves if isgrass else 294})
                if kind not in seen:
                    bpy.context.view_layer.update();render_asset(a.obj,HERE/(level+'-'+kind+'-preview.png'),resolution=1000);seen.add(kind)
                if number%100==0:print(level,number+1,'/',len(selected),kind,'triangles',len(added),flush=True)
            out.write(']}')
        report.update({'removed_triangles':len(removed),'added_triangles':sum(i['triangles']for i in report['instances']),
            'grass_count':sum(i['kind']=='grass'for i in report['instances']),'cactus_count':sum(i['kind']=='cactus'for i in report['instances']),
            'patch_sha256':sha(outpath),'textures':[dict(t,sha256=sha(t['rgba_file']))for t in textures]})
        write(HERE/(level+suffix+'-report.json'),report)
        for obj in bpy.context.scene.objects:obj.hide_render=False
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(level+suffix+'-plants.blend')))
        print(json.dumps({k:report[k]for k in ('level','grass_count','cactus_count','removed_triangles','added_triangles','patch_sha256')}),flush=True)

if __name__=='__main__':main()
