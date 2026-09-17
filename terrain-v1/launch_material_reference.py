"""Native reference: real previous FR3 files and shaders, with accepted water/fire."""
from pathlib import Path
import json,shutil,subprocess,msvcrt
import os
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'terrain-v1/native-audit'
lock=(ROOT/'prototype.lock').open('a+b');lock.seek(0)
msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
files=['out/jak3/fr3/waspala.fr3','out/jak3/fr3/game.fr3']
files += ['game/graphics/opengl_renderer/shaders/'+name for name in
          ['tfrag3.frag','tie_wind.frag','etie_base.frag','shrub.frag','shrub.vert']]
try:
    for relative in files:
        source=ROOT/'variants/remaster-before-palace'/relative
        if not source.exists():source=ROOT/'terrain-v1/shaders-before-palace'/Path(relative).name
        shutil.copy2(source,ROOT/'data'/relative)
    with (HERE/'reference-runtime.log').open('w') as log:
        process=subprocess.Popen([str(ROOT/'runtime/liquids-v3/gk.exe'),'--game','jak3',
          '--proj-path',str(ROOT/'data'),'--config-path',str(ROOT/'profiles/remaster-palace'),
          '--disable-ansi','--','-fakeiso','-boot','-debug'],cwd=ROOT,stdout=log,
          stderr=subprocess.STDOUT,env={**os.environ,'OPENGOAL_TEST_MUTE':'1'},
          creationflags=subprocess.CREATE_NO_WINDOW)
        (HERE/'reference.pid').write_text(str(process.pid))
        print('Native material reference running, PID',process.pid,flush=True)
        process.wait()
finally:
    for relative in files:shutil.copy2(ROOT/'variants/remaster'/relative,ROOT/'data'/relative)
