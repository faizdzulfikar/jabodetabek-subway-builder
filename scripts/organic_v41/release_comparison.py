"""Compare approved member-level release with frozen v4 baseline and StageA preview."""
from pathlib import Path
import json,gzip,csv,numpy as np,shapely
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41-stage-b'
def readgz(p):return json.load(gzip.open(p,'rt'))
def csvout(n,rr):
 with(OUT/n).open('w')as f:w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
if __name__=='__main__':
 b=readgz(ROOT/'docs/organic-stage-b/proposed_allocations.json.gz')['points'];p=readgz(OUT/'proposed_allocations.json.gz')['points'];ba=np.load(ROOT/'docs/organic-stage-b/proposed_arrays.npz');raw=np.load(OUT/'proposed_arrays.npz');a={k:raw[k]for k in raw.files};oldby={x['source_anchor_id']:x for x in b};newby={x['source_anchor_id']:x for x in p};keys=set(oldby)|set(newby);vpop=sum(abs(oldby.get(k,{}).get('population',0)-newby.get(k,{}).get('population',0))for k in keys)//2;vhome=sum(abs(oldby.get(k,{}).get('model_residents',0)-newby.get(k,{}).get('model_residents',0))for k in keys)//2;vjobs=sum(abs(oldby.get(k,{}).get('jobs',0)-newby.get(k,{}).get('jobs',0))for k in keys)//2
 changes=[]
 for k in sorted(keys):
  old=oldby.get(k);new=newby.get(k)
  if old and new and all(old[t]==new[t]for t in ['location','population','model_residents','jobs']):continue
  changes.append({'source_anchor_id':k,'population_v4':old['population']if old else 0,'population_v41':new['population']if new else 0,'origins_v4':old['model_residents']if old else 0,'origins_v41':new['model_residents']if new else 0,'jobs_v4':old['jobs']if old else 0,'jobs_v41':new['jobs']if new else 0,'anchor_v4':str(old['location'])if old else'','anchor_v41':str(new['location'])if new else'','function_v41':new['anchor_function']if new else'excluded'})
 csvout('changed_source_anchors.csv',changes)
 area=[];geo=readgz(ROOT/'docs/organic-v41/audit_boundaries.geojson.gz');bloc=ba['locations'];loc=a['locations']
 for f in geo['features']:
  g=shapely.geometry.shape(f['geometry']);i=shapely.intersects_xy(g,*bloc.T);j=shapely.intersects_xy(g,*loc.T);area.append({'area':f['properties']['name'],'kind':f['properties']['kind'],'population_v4':int(ba['population'][i].sum()),'population_v41':int(a['population'][j].sum()),'working_origins_v4':int(ba['home'][i].sum()),'working_origins_v41':int(a['home'][j].sum()),'jobs_v4':int(ba['jobs'][i].sum()),'jobs_v41':int(a['jobs'][j].sum()),'boundary_confidence':f['properties']['confidence']})
 csvout('area_comparison.csv',area)
 names=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz')['names'].tolist();regional=[]
 for r,name in enumerate(names):
  i=ba['regions']==r;j=a['regions']==r;regional.append({'region':name,'population_v4':int(ba['population'][i].sum()),'population_v41':int(a['population'][j].sum()),'working_origins_v4':int(ba['home'][i].sum()),'working_origins_v41':int(a['home'][j].sum()),'jobs_v4':int(ba['jobs'][i].sum()),'jobs_v41':int(a['jobs'][j].sum())})
 assert all(x['population_v4']==x['population_v41']and x['working_origins_v4']==x['working_origins_v41']and x['jobs_v4']==x['jobs_v41']for x in regional);csvout('regional_comparison.csv',regional)
 led=list(csv.DictReader((OUT/'member_reclassification.csv').open()));bad=[x for x in led if x['reason']!='retain_existing_member_prior'];badset={x['osm_id']for x in bad};assert all(x['population']==x['model_residents']==0 for x in p if x['osm_id']in badset)
 hangars={x['osm_id']for x in csv.DictReader((OUT/'facility_access.csv').open())if x['type']=='hangar'};report={'population_moved_between_source_anchors_half_l1':vpop,'worker_origins_moved_half_l1':vhome,'jobs_moved_half_l1':vjobs,'positively_reclassified_constituents':len(bad),'all_reclassified_nonresidential_origins_and_population_zero':True,'restored_hangar_jobs':sum(x['jobs']for x in p if x['osm_id']in hangars),'airport':next(x for x in area if x['kind']=='airport'),'unchanged_regional_margins':True,'different_from_stageA_preview':'Member-level split retains residential neighbors, corrects primary service function, and selects mapped-road-side interiors. StageA preview numbers are not final release numbers.'};(OUT/'comparison_summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
