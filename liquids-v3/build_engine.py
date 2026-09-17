"""Build the isolated v0.3.6 runtime with the installed Windows toolchain."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CMAKE = Path('C:/Program Files (x86)/Microsoft Visual Studio/2019/BuildTools/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe')
# The desktop shell can expose both Path and PATH. MSBuild rejects duplicate keys.
env = {key.upper(): value for key, value in os.environ.items()}
env['CL'] = '/MP6'
with (ROOT / 'liquids-v3/build-engine.log').open('w', encoding='utf-8') as log:
    result = subprocess.run([str(CMAKE), '--build', str(ROOT / 'engine-build'),
                             '--config', 'Release', '--target', 'gk', '--parallel', '6'],
                            env=env, stdout=log, stderr=subprocess.STDOUT)
print('\n'.join((ROOT / 'liquids-v3/build-engine.log').read_text(encoding='utf-8', errors='replace').splitlines()[-35:]))
sys.exit(result.returncode)
