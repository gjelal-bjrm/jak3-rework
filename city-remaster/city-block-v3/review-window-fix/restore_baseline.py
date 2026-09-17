"""Restore the exact map/config preserved before temporary native captures."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent
R=H.parents[2]
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
record=json.loads((H/'baseline/setup.json').read_text())
for relative,item in record['restore'].items():
 assert sha(item['backup'])==item['sha256']
 shutil.copy2(item['backup'],R/'data'/relative)
 assert sha(R/'data'/relative)==item['sha256']
print('Exact pre-capture live map/config restored')
