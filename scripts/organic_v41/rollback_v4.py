"""Explicit rollback to the exact pre-v4.1 production snapshot."""
from pathlib import Path
import sys,json,hashlib,shutil,os
ROOT=Path(__file__).resolve().parents[2];BACKUP=ROOT/'docs/organic-v41-stage-b/rollback-v4'
if __name__=='__main__':
 if '--restore'not in sys.argv:raise SystemExit('Read-only by default. Close game and supply --restore to recover original v4 assets.')
 m=json.loads((BACKUP/'manifest.json').read_text())
 for name,h in m.items():assert hashlib.sha256((BACKUP/name).read_bytes()).hexdigest()==h,name
 for name in m:
  target=ROOT/name;temp=target.with_name(target.name+'.rollback.tmp');shutil.copyfile(BACKUP/name,temp);os.replace(temp,target)
 for name,h in m.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 print('Original verified v4 production files restored. Restart game and use the v4 save.')
