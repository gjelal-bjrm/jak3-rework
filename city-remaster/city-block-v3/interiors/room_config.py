"""One physical room per apartment; apertures reference the shared room."""
import hashlib
SHARED=('wca-house1-west-room','wca-house1-east-room')
def rooms_for(windows):
    by_id={w['id']:w for w in windows}
    assert len(by_id)==len(windows)
    rooms=[];assigned=set()
    if all(name in by_id for name in SHARED):
        rooms.append({'id':'wca-house1-corner-apartment','anchor':SHARED[0],
          'windows':list(SHARED),'mesh':'corner-conversation','scale':[1,1,1],
          'lamp':[.55,2.8,-1.7],'actors':[
            {'mesh':'conversing-male','position':[.25,.058,-2.15],'yaw':2.214297435588181,'phase':0},
            {'mesh':'conversing-female','position':[1.45,.058,-3.05],'yaw':-0.9272952180016122,'phase':0}]})
        assigned.update(SHARED)
    for w in windows:
        if w['id'] in assigned:continue
        depth=min(1.,w.get('room_depth',3.65)/3.65)
        height=(w['height']+.6)/3.65
        width=(w['width']+.7)/4.3
        # Stable variety belongs to the apartment and never depends on camera/index.
        sitting=depth>.8 and hashlib.sha256(w['id'].encode()).digest()[0]%2==0
        actors=[]
        if w['inhabited']:
            actors=[{'mesh':'sitting-male','position':[0,.09,-2.5*depth],'yaw':0,'phase':.7}] if sitting else [
                {'mesh':'conversing-male','position':[-.68*width,.058,-1.8*depth],'yaw':1.5707963267948966,'phase':0},
                {'mesh':'conversing-female','position':[.68*width,.058,-1.8*depth],'yaw':-1.5707963267948966,'phase':0}]
        rooms.append({'id':w['id']+'-apartment','anchor':w['id'],'windows':[w['id']],
          'mesh':'lounge' if sitting else 'conversation','scale':[width,height,depth],
          'lamp':[0,2.94,-1.65],'actors':actors})
        assigned.add(w['id'])
    assert assigned==set(by_id)
    return rooms
