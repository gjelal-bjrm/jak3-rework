from pathlib import Path
import os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
CMAKE='C:/Program Files (x86)/Microsoft Visual Studio/2019/BuildTools/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
env={k.upper():v for k,v in os.environ.items()};env['CL']='/MP6'
with (ROOT/'models-v1/build.log').open('w') as log:
    result=subprocess.run([CMAKE,'-S',str(ROOT/'engine-src'),'-B',str(ROOT/'engine-build')],env=env,stdout=log,stderr=subprocess.STDOUT)
    if not result.returncode:result=subprocess.run([CMAKE,'--build',str(ROOT/'engine-build'),'--config','Release','--target','palace_mesh_bridge','--parallel','6'],env=env,stdout=log,stderr=subprocess.STDOUT)
print('\n'.join((ROOT/'models-v1/build.log').read_text(errors='replace').splitlines()[-12:]))
sys.exit(result.returncode)
