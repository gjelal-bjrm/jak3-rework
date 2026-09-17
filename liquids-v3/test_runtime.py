"""Start the development renderer after shader edits, without snapshot mutations."""
from pathlib import Path
import argparse
import shutil
import subprocess
import os

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--scene', choices=('arena','palace'), default='arena')
args = parser.parse_args()
profile = ROOT/'profiles'/('v3-'+args.scene)
settings = profile/'OpenGOAL/jak3/settings'
if not settings.exists():
    shutil.copytree(ROOT/'profiles/remaster/OpenGOAL/jak3/settings', settings)
shutil.copy2(ROOT/'routes/remaster'/args.scene/'GAME.CGO', ROOT/'data/out/jak3/iso/GAME.CGO')
subprocess.run(['python',str(ROOT/'liquids-v3/apply_materials.py')],check=True)
with (ROOT/'liquids-v3'/f'{args.scene}-runtime.log').open('w') as log:
    proc = subprocess.Popen([str(ROOT/'engine-build/bin/Release/gk.exe'),
        '--game','jak3','--proj-path',str(ROOT/'data'),'--config-path',str(profile),
        '--disable-ansi','--','-fakeiso','-boot','-debug'],cwd=ROOT,
        stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENGOAL_TEST_MUTE':'1'},
        creationflags=subprocess.CREATE_NO_WINDOW)
    (ROOT/'liquids-v3/runtime.pid').write_text(str(proc.pid))
    print(f'V3 {args.scene}: PID {proc.pid}',flush=True)
    raise SystemExit(proc.wait())
