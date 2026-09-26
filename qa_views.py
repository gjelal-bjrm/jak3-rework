"""Captures a points de vue fixes (camera libre) pour comparer avant/apres au meme cadrage.
  python qa_views.py [--variant original] <scene> <prefixe> "EX,EY,EZ/TX,TY,TZ" ["..."]
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
args = sys.argv[1:]; variant = ['--variant', 'remaster']
if args[0] == '--variant': variant = ['--variant', args[1]]; args = args[2:]
scene, prefix, views = args[0], args[1], args[2:]
for i, v in enumerate(views):
    subprocess.run([sys.executable, str(ROOT / 'qa_live.py'), scene, f'{prefix}-{i}', '--freecam', v, '--keep-freecam', '--wait', '1.5'] + variant,
                   capture_output=True)
subprocess.run([sys.executable, str(ROOT / 'qa_live.py'), scene, f'{prefix}-reset', '--eval',
                "(remove-setting-by-arg0 *setting-control* 'mode-name)", '--wait', '0.3'] + variant, capture_output=True)
print('ok', len(views))
