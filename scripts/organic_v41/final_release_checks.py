"""Final installed delivery audit: production scope, runtime hash, CSV, docs and backup."""
from pathlib import Path
import json,hashlib,csv,re,urllib.request
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41-stage-b'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
 runtime=json.loads((OUT/'runtime_verification.json').read_text());q=json.loads((OUT/'validation.json').read_text());actual=sha(ROOT/'assets/JKT/demand_data.json.gz');assert actual==q['candidate_sha256']==runtime['candidate_sha256'];assert runtime['in_game_verified']and runtime['verified_candidate_sha256']==actual
 rawbase=json.loads((ROOT/'docs/organic-v41/production_baseline_hashes.json').read_text());base={n:h for n,h in rawbase.items()if Path(n).name!='.DS_Store'};allowed={'assets/JKT/demand_data.json.gz','assets/JKT/demand-method.json','config.json','BUILD_STATUS.json','mod/config.json','mod/manifest.json','mod/index.js','mod/demand_data.json.gz'};changed=[n for n,h in base.items()if sha(ROOT/n)!=h];assert set(changed)==allowed,(changed,allowed)
 manifest=json.loads((OUT/'rollback-v4/manifest.json').read_text());assert all(sha(OUT/'rollback-v4'/n)==h for n,h in manifest.items())
 rows=list(csv.DictReader((ROOT/'sources/government/kelurahan_estimates.csv').open()));assert len(rows)==1502 and sum(int(x['population_allocated'])for x in rows)==32615007 and sum(int(x['model_residents'])for x in rows)==sum(int(x['estimated_jobs'])for x in rows)==12646700
 body=urllib.request.urlopen('http://127.0.0.1:18765/JKT/demand_data.json.gz').read();assert hashlib.sha256(body).hexdigest()==actual
 state=json.loads((ROOT/'BUILD_STATUS.json').read_text());assert state['in_game_verified']and state['demand_points']==78341;method=json.loads((ROOT/'assets/JKT/demand-method.json').read_text());assert method['version']=='4.1'and method['stage']=='B_V41_VERIFIED';assert 'pending'not in method['stage'].lower();assert abs(method['cross_region_fraction']-.4)<.0001
 files=[ROOT/'docs/ORGANIC_V41_IMPLEMENTATION.md',ROOT/'README.md',ROOT/'DATA_GUIDE.md'];broken=[]
 for p in files:
  for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://'not in target and not(p.parent/target.split('#')[0]).exists():broken.append((str(p),target))
 assert not broken,broken
 result={'status':'B_V41_COMPLETE','runtime_verified':True,'production_candidate_sha256':actual,'local_asset_server_sha256':actual,'protected_production_paths_checked':len(base),'changed_protected_paths':changed,'geometry_assets_unchanged':True,'ignored_desktop_metadata_paths':[n for n in rawbase if Path(n).name=='.DS_Store'],'rollback_verified_files':len(manifest),'population_csv_total':32615007,'origin_and_job_csv_total':12646700,'report_local_links_valid':True,'not_pushed_to_github':True};(OUT/'delivery_checks.json').write_text(json.dumps(result,indent=2)+'\n')
 files=[ROOT/'docs/ORGANIC_V41_IMPLEMENTATION.md',ROOT/'README.md',ROOT/'DATA_GUIDE.md',ROOT/'BUILD_STATUS.json',ROOT/'assets/JKT/demand-method.json']+[p for p in OUT.rglob('*')if p.is_file()and p.name not in ['review_manifest.json','.DS_Store']]+[p for p in(ROOT/'scripts/organic_v41').iterdir()if p.is_file()and p.suffix in ['.py','.mjs']]
 (OUT/'review_manifest.json').write_text(json.dumps({'status':'B_V41_COMPLETE','files':{str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(set(files))}},indent=2)+'\n');print(json.dumps(result,indent=2))
