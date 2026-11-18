"""Construit l'outil palace_mesh_bridge (meme chaine que build_engine.py)."""
from pathlib import Path
import os, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
CMAKE = Path('C:/Program Files (x86)/Microsoft Visual Studio/2019/BuildTools/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe')
env = {key.upper(): value for key, value in os.environ.items()}
env['CL'] = '/MP6'
with (ROOT / 'liquids-v3/build-bridge.log').open('w', encoding='utf-8') as log:
    result = subprocess.run([str(CMAKE), '--build', str(ROOT / 'engine-build'), '--config', 'Release',
                             '--target', 'palace_mesh_bridge', '--parallel', '6'], env=env, stdout=log, stderr=subprocess.STDOUT)
tail = (ROOT / 'liquids-v3/build-bridge.log').read_text(encoding='utf-8', errors='replace').splitlines()[-6:]
print(chr(10).join(tail).encode('ascii', errors='replace').decode())
sys.exit(result.returncode)
