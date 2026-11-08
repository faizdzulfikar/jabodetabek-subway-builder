"""Install approved S0+OD40 only after independent gates and byte reproducibility."""
from pathlib import Path
import json,gzip,hashlib,shutil,os,csv,collections
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41-stage-b'
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def readgz(p):return json.load(gzip.open(p,'rt'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
 q=load(OUT/'validation.json');d=load(OUT/'demand_checks.json');repro=load(OUT/'reproducibility.json');build=load(OUT/'build_checks.json');assert q['stage']=='B_V41_RELEASE_GATE_PASSED'and q['official_population_controls_exact']==446 and not any(q['mapped_mask_hits'].values());assert sha(OUT/'candidate-demand.json.gz')==q['candidate_sha256'];assert sha(OUT/'proposed_allocations.json.gz')==q['allocation_sha256'];assert repro['allocation_byte_identical']and repro['demand_byte_identical'];assert build['approved']=='S0+OD40'and build['exact_village_population']and build['exact_village_origins'];assert abs(d['cross_region_fraction']-.4)<.0001
 names=['assets/JKT/demand_data.json.gz','assets/JKT/demand-method.json','BUILD_STATUS.json','config.json','mod/config.json','mod/manifest.json','mod/index.js','sources/government/kelurahan_estimates.csv','README.md','DATA_GUIDE.md','sources/government/COVERAGE.md'];rollback=OUT/'rollback-v4';rollback.mkdir(exist_ok=True);manifest={}
 for name in names:
  src=ROOT/name;dest=rollback/name;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(src,dest)
  manifest[name]=sha(dest)
 save(rollback/'manifest.json',manifest)
 dest=ROOT/'assets/JKT/demand_data.json.gz';temp=dest.with_suffix('.gz.tmp');shutil.copyfile(OUT/'candidate-demand.json.gz',temp);os.replace(temp,dest)
 previous=load(rollback/'assets/JKT/demand-method.json');routing=load(OUT/'route_sample.json');method={**previous,**d,'version':'4.1','stage':'B_V41_INSTALLED_RUNTIME_PENDING','approved_scenario':'S0+OD40','points':d['engine_points'],'commuters':d['workers'],'allocation_provenance':'docs/organic-v41-stage-b/proposed_allocations.json.gz','spatial_validation':'docs/organic-v41-stage-b/validation.json','runtime_verification':'docs/organic-v41-stage-b/runtime_verification.json','parameters':'docs/organic-v41-stage-b/parameters.json','capacity_regularization':'v4 ceiling2 retained; corrected constituent functions with existing function priors; no S1 intensity changes','coordinate_method':'unchanged v4 real-feature anchors outside33targetedclusters; individual actual-building interiors for reviewed members; six hangars and named airport operations anchored toward mapped non-airside local road','limitations':[x for x in previous['limitations']if 'Final UI'not in x and not x.startswith('Driving times remain proxy')]+[f"Driving times remain proxy; current96-pair road sample {routing['reachable_pairs']}/96 reachable, median detour {routing['detour_ratio_median_p90'][0]:.2f}; no measured congestion",'Staff-side access inferred from mapped roads, not surveyed staff gates; private roads/shift staffing uncertain','S0 does not resolve all unclassified airport/residential/workplace coverage; noS1 or demographic/regional-total increase','v4.1 final UI verification pending']};save(ROOT/'assets/JKT/demand-method.json',method)
 cfg=load(ROOT/'config.json');cfg.update(demand_version='4.1',notes='Organic demand v4.1 S0+OD40. Corrected constituent nonresidential functions;6restored hangars. All village population/worker and regional job totals unchanged. Lightweight map geometry unchanged.');save(ROOT/'config.json',cfg)
 for name in ['mod/config.json','mod/manifest.json']:
  obj=load(ROOT/name);obj['version']='0.2.2';obj['description']='Lightweight Jabodetabek organic demand v4.1 S0+OD40; official population controls; workplaces/OD remain estimates.';save(ROOT/name,obj)
 p=ROOT/'mod/index.js';js=p.read_text().replace('Jabodetabek v4: organic demand; population controls conserved.','Jabodetabek v4.1 S0: corrected organic demand; population controls conserved.')
 credit="                                    [' © ESA WorldCover2021','https://esa-worldcover.org/en/data-access'],\n"
 while js.count(credit)>0:js=js.replace(credit,'',1)
 # Final array entry remains as the single attribution; remove only duplicate entries.
 p.write_text(js)
 inp=readgz(ROOT/'assets/JKT/government_inputs.json.gz');alloc=readgz(OUT/'proposed_allocations.json.gz');byadmin=collections.defaultdict(list)
 for point in alloc['points']:byadmin[point['admin_id']].append(point)
 rows=[]
 for v in inp['villages']:
  pp=byadmin[v['id']];rows.append({**{k:v[k]for k in ['id','region','kecamatan','kelurahan','year','source','population_status']},'population_estimate':round(v['population'],3),'population_allocated':sum(p['population']for p in pp),'reported_working_residents':v['reported_working_residents'],'model_residents':sum(p['model_residents']for p in pp),'estimated_jobs':sum(p['jobs']for p in pp),'jobs_status':'modelled organic v4.1 S0; not measured workplace counts'})
 with(ROOT/'sources/government/kelurahan_estimates.csv').open('w')as f:w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
 st=load(ROOT/'BUILD_STATUS.json');st.update(status='organic demand v4.1 S0+OD40 installed; final runtime checks pending',demand_version='4.1',demand_points=d['engine_points'],synthetic_commuters=d['workers'],in_game_verified=False,in_game_checks=[],organic_validation='docs/organic-v41-stage-b/validation.json',runtime_verification='docs/organic-v41-stage-b/runtime_verification.json',rollback='docs/organic-v41-stage-b/rollback-v4',game_assets_bytes=sum(p.stat().st_size for p in(ROOT/'assets').rglob('*')if p.is_file()));save(ROOT/'BUILD_STATUS.json',st)
 save(OUT/'runtime_verification.json',{'status':'PENDING','in_game_verified':False,'candidate_sha256':q['candidate_sha256'],'verified_candidate_sha256':None,'game_version':'1.7.2','mod_version':'0.2.2','verified_in_ui':[],'save_name':None})
 params={'version':'4.1','approval':'User said lanjut after recommendationS0+OD40','stage':'B_INSTALLED_PENDING_UI','regional_and_village_margins':'v4 unchanged','OD_cross_region':.4,'decay_km':18,'cost_noise_km':6,'floor_ceiling':2,'function_intensities':'existing v4 priors only; S1 excluded','rebuild':'33identified clusters expanded to individual member building interiors to avoid nonresidential source/facility aggregation','access':'mapped local-road side inferred; not surveyed entrance','source_model':'docs/organic-stage-b/organic_parameters.json'};save(OUT/'parameters.json',params)
 p=ROOT/'README.md';s=p.read_text();i=s.index('## Status');j=s.index('## Data and limitations');s=s[:i]+'''## Status

Organic demand v4.1 S0+OD40 (mod 0.2.2) is installed and passed independent
spatial/statistical/schema gates. Final game render and save/load checks are pending.
All population, village working-origin and regional job totals are unchanged.
See [v4.1 release report](docs/ORGANIC_V41_IMPLEMENTATION.md) and
[runtime evidence](docs/organic-v41-stage-b/runtime_verification.json).
Keep the local tile server running while playing. Workplaces and OD remain estimates.

'''+s[j:];p.write_text(s)
 p=ROOT/'DATA_GUIDE.md';s=p.read_text();marker='# Jabodetabek Subway Builder — data index';s=s[s.index(marker):];s='''# Organic demand v4.1 — current release

Approved S0+OD40: corrected constituent nonresidential functions and six restored
hangars. All32,615,007inhabitants,446population controls and12,646,700working
tripmakers/jobs conserved. Regional jobs and all village origins unchanged.

Start with [release report](docs/ORGANIC_V41_IMPLEMENTATION.md),
[allocation](docs/organic-v41-stage-b/proposed_allocations.json.gz),
[validation](docs/organic-v41-stage-b/validation.json),
[runtime](docs/organic-v41-stage-b/runtime_verification.json) and
[rollbackv4](docs/organic-v41-stage-b/rollback-v4/manifest.json).
S1 intensities and OD30 were not installed. StageA reports remain an archived proposal.

'''+s;p.write_text(s)
 p=ROOT/'sources/government/COVERAGE.md';text=p.read_text().replace('Versi 3 memakai data pemda untuk penduduk.', 'Versi 4.1 mempertahankan kontrol penduduk pemda yang disiapkan sejak v3.').replace('Hasilnya diringkas ke grid500 m.', 'Sel v3 500m dipertahankan sebagai arsip persiapan; koordinat demand aktif v4.1 mengikuti bangunan/parcel nyata, tanpa grid final.');p.write_text(text)
 print('Installed S0+OD40:',q['candidate_sha256'],'rollbackv4 ready; runtime pending')
