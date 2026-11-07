"""Deterministic staged rebuild. Run from workspace; --install replaces verified assets.
Raw OSM inventory and WorldCover tile remain offline scratch, not game payload.
"""
from pathlib import Path
import sys,subprocess,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=ROOT/'docs/organic-stage-b';DB=Path('work/organic-audit/inventory.sqlite')
def run(name,*args):subprocess.run([sys.executable,str(HERE/name),*map(str,args)],check=True)
if __name__=='__main__':
 assert Path('work/demand-v2/crop.tif').exists(),'Prepare the WorldPop2025crop described in sources/worldpop.json.'
 assert (ROOT/'sources/organic/coverage_support.json').exists(),'Retain frozen coverage-support inputs for reproducibility.'
 assert DB.exists(),'Prepare full OSM inventory following StageA reproduction instructions.'
 assert Path('work/organic-stage-b/worldcover2021_S09E105.tif').exists(),'Download ESA WorldCover tile recorded in fallback_coverage.json.'
 run('enrich.py',DB);run('fallback.py');run('allocate.py',DB,'--reuse')
 for _ in range(3):
  if not json.loads((OUT/'proposal_checks.json').read_text())['unlocated_village_count']:break
  run('fallback.py');run('allocate.py',DB,'--reuse')
 assert not json.loads((OUT/'proposal_checks.json').read_text())['unlocated_village_count']
 run('calibrate_jobs.py');run('demand.py');sha=lambda:hashlib.sha256((OUT/'candidate-demand.json.gz').read_bytes()).hexdigest();h=sha();run('demand.py');assert h==sha();(OUT/'reproducibility.json').write_text(json.dumps({'candidate_sha256':h,'previous_candidate_sha256':h,'two_demand_generations_byte_identical':True,'seed':20261107},indent=2));run('verify.py');run('route_sample.py');run('visualize.py',DB);run('finish_diagnostics.py')
 if '--install'in sys.argv:run('install_release.py');subprocess.run([sys.executable,str(ROOT/'scripts/validate.py')],check=True)
 print('Staged rebuild passed. Runtime checks must be repeated after installation; never mark in-game verified from this script.')
