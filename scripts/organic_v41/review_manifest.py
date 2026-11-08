"""Hash final review artifacts, check links and prove production untouched."""
from pathlib import Path
import json,hashlib,sys,importlib.metadata as metadata,re,subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41'
required=['ORGANIC_V41_MASTER_AUDIT.md','SUBURBAN_RESIDENTIAL_AUDIT.md','EMPLOYMENT_DENSITY_AUDIT.md','AIRPORT_INDUSTRIAL_EMPLOYMENT_AUDIT.md','POPULATION_DEMAND_GAP_AUDIT.md','ORGANIC_V41_CALIBRATION_PROPOSAL.md']
# Offline source caches are evidence inputs, NOT runtime map deliverables.
inputs=['work/organic-audit/inventory.sqlite','work/organic-audit/jabodetabek.osm.pbf','work/organic-audit/packaged_water.wkb','work/organic-stage-b/building_candidates.npz','work/organic-stage-b/cluster_members.npz','work/organic-stage-b/worldcover2021_S09E105.tif','work/demand-v3/jakarta-worker-all.json.gz']
manifest={'stage':'A_AUDIT_AND_PROPOSAL','python':sys.version,'packages':{n:metadata.version(n)for n in ['numpy','scipy','shapely','pyproj','rasterio','osmium','ortools','matplotlib']},'cached_inputs':{},'limitations':'Inputs reproduce cached model stages; no claim all web pages or full fresh OSM extract can be recreated from repo alone. Sources include archived primary metadata and access limitations.'}
for name in inputs:
 p=Path(name);h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 manifest['cached_inputs'][name]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
(OUT/'reproduction_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
files=[ROOT/'docs'/n for n in required]+list(OUT.rglob('*'))+[p for p in (ROOT/'scripts/organic_v41').iterdir() if p.suffix in ['.py','.mjs']];files=[p for p in files if p.is_file()and p.name not in ['review_manifest.json','.DS_Store']and '__pycache__'not in p.parts]
broken=[]
for p in files:
 if p.suffix=='.md':
  for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://'not in target and not(p.parent/target.split('#')[0]).exists():broken.append((str(p),target))
assert not broken,broken
hashes=json.loads((OUT/'production_baseline_hashes.json').read_text());assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
for name in required:assert (ROOT/'docs'/name).exists()
review={'stage':'A_COMPLETE_PROPOSAL_ONLY','production_assets_unchanged':True,'proposal_not_installed':True,'proposal_not_game_verified':True,'required_reports':required,'local_markdown_links':'passed','files':{str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(set(files))}}
(OUT/'review_manifest.json').write_text(json.dumps(review,indent=2)+'\n');print('Review manifest:',len(review['files']),'files; all links valid; production hashes unchanged.')
