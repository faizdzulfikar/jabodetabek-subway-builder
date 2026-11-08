"""Independent StageA completion: consistency, audit handoff, production protection."""
from pathlib import Path
import json,gzip,csv,hashlib,io,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41'
def load(p):return json.loads(p.read_text())
def readgz(p):return json.load(gzip.open(p,'rt'))
def dump(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':
 b=readgz(ROOT/'docs/organic-stage-b/proposed_allocations.json.gz')['points'];p=readgz(OUT/'proposed_allocations.json.gz')['points'];pilot=readgz(OUT/'pilot_allocations.json.gz')['points'];rows=[]
 for i,x in enumerate(p):
  y=b[i]if i<len(b)else{'population':0,'model_residents':0,'jobs':0,'relative_employment_capacity':0};rows.append({'anchor_id':x['id'],'source_anchor_id':x['source_anchor_id'],'anchor_kind':x['anchor_kind'],'admin_id':x['admin_id'],'longitude':x['location'][0],'latitude':x['location'][1],'population_current':y['population'],'population_proposed_S0':x['population'],'working_origins_current':y['model_residents'],'working_origins_proposed_S0':x['model_residents'],'jobs_current':y['jobs'],'jobs_proposed_S0':x['jobs'],'jobs_pilot_S1':pilot[i]['jobs'],'relative_job_capacity_current':y['relative_employment_capacity'],'relative_job_capacity_S0':x['relative_employment_capacity'],'anchor_function':x['anchor_function'],'function_flag_observed':x['function_observed'],'levels_flag_observed':x['anchor_levels_observed'],'confidence':'Footprint/anchor verified; staffing inferred; flags not staffing observations'})
 s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 with gzip.GzipFile(filename=str(OUT/'point_comparison.csv.gz'),mode='wb',mtime=0)as f:f.write(s.getvalue().encode())
 functionrows=[]
 for cat in sorted(set(x['anchor_function']for x in p)):
  ix=[i for i,x in enumerate(p)if x['anchor_function']==cat];oi=[i for i in ix if i<len(b)];functionrows.append({'anchor_class':cat,'jobs_current':sum(b[i]['jobs']for i in oi),'jobs_S0':sum(p[i]['jobs']for i in ix),'jobs_S1':sum(pilot[i]['jobs']for i in ix),'population_current':sum(b[i]['population']for i in oi),'population_S0':sum(p[i]['population']for i in ix),'warning':'Anchor/cluster class; jobs estimates, NOT measured staff by economic sector'})
 with (OUT/'function_comparison.csv').open('w')as f:w=csv.DictWriter(f,fieldnames=list(functionrows[0]),lineterminator='\n');w.writeheader();w.writerows(functionrows)
 protected=load(OUT/'production_baseline_hashes.json');changed=[n for n,h in protected.items()if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h];assert not changed,changed
 val=load(OUT/'validation.json');assert val['official_population_controls_exact']==446 and val['all_engine_point_margins_exact']and not any(val['mapped_mask_hits'].values())
 checks=load(OUT/'audit_checks.json');assert checks['population_village_margins_unchanged']and checks['working_origin_village_margins_unchanged']and checks['regional_job_margins_unchanged']
 di=load(OUT/'diagnostic_checks.json');assert all(di[k]for k in ['all_district_population_margins_exact','all_district_origin_margins_exact','capacity_scenarios_conserve_regions','airport_roles_no_double_count'])
 # Verify40% control separately to isolate spatial corrections from the30% OD scenario.
 aa=np.load(OUT/'proposed_arrays.npz');od40=np.load(OUT/'od40/od_pairs.npz');assert np.array_equal(np.bincount(od40['origin'],weights=od40['units']*100,minlength=len(p)),aa['home']);assert np.array_equal(np.bincount(od40['destination'],weights=od40['units']*100,minlength=len(p)),aa['jobs'])
 totals=[sum(x['population']for x in p),sum(x['model_residents']for x in p),sum(x['jobs']for x in p)];assert totals==[32615007,12646700,12646700]
 v={x['id']:x for x in b};new={x['id']:x for x in p};popmoved=sum(abs(x['population']-(v[x['id']]['population']if x['id']in v else 0))for x in p)//2
 runtime=load(ROOT/'docs/organic-stage-b/runtime_verification.json');assert runtime['in_game_verified']
 result={'stage':'A_COMPLETE_PROPOSAL_ONLY','production_unchanged':True,'protected_asset_paths_checked':len(protected),'production_changed_paths':changed,'baseline_runtime_verified':True,'proposal_runtime_verified':False,'candidate_static_gate':'passed','official_controls_exact':446,'all_village_population_and_worker_origin_totals_unchanged':True,'regional_job_totals_unchanged':True,'full_point_od_scenarios_verified':[.30,.40],'capacity_and_regional_od_sensitivity_tables':'passed exact marginal checks','total_population':totals[0],'total_working_tripmakers':totals[1],'total_jobs':totals[2],'population_relocated':popmoved,'production_demand_sha256':protected['assets/JKT/demand_data.json.gz'],'proposed_demand_sha256':hashlib.sha256((OUT/'candidate-demand.json.gz').read_bytes()).hexdigest(),'approval_required_before_install':True,'expected_next_action':'User selects spatial S0 and OD30/40; S1 capacity pilot not recommended without stronger facility evidence'}
 dump('completion_checks.json',result);print(json.dumps(result,indent=2))
