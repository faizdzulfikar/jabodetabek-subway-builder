"""Generate v3: local-government residential controls, estimated workplace locations.
Published population, reported occupations, business proxies and inferred jobs are
kept separate in the source manifest and administrative audit tables.
"""
from pathlib import Path
import gzip,json,re,csv,collections
import numpy as np
from generate_calibrated_demand import apportion
ROOT=Path(__file__).resolve().parents[1];PATH=ROOT/'assets/JKT';GOV=ROOT/'sources/government'
def norm(s):return re.sub('[^A-Z0-9]','',str(s).upper())
def main():
 cfg=json.loads((ROOT/'config.json').read_text());rng=np.random.default_rng(cfg['seed']);inp=json.load(gzip.open(PATH/'government_inputs.json.gz','rt'));cells=inp['cells'];villages=inp['villages'];proxies=json.loads((GOV/'workplace_proxies.json').read_text())
 names=sorted(set(c['region'] for c in cells));reg=np.array([names.index(c['region']) for c in cells]);loc=np.array([c['location'] for c in cells]);xy=loc*[110600,111200]
 pop=np.array([c['population'] for c in cells]);ind=np.array([c['industrial_m2'] for c in cells]);com=np.array([c['commercial_m2'] for c in cells]);site=np.array([c['official_industry_sites'] for c in cells]);kecs=np.array([norm(villages[c['village']]['kecamatan']) for c in cells])
 # Median reported occupation/population ratio provides an explicit assumption only where occupation data is absent.
 ratios=[v['reported_working_residents']/v['population'] for v in villages if v['reported_working_residents'] is not None and v['population']>0]
 participation=float(np.median(ratios));assert .1<participation<.8
 rawhome=np.array([c['population']*(villages[c['village']]['reported_working_residents']/villages[c['village']]['population'] if villages[c['village']]['reported_working_residents'] is not None and villages[c['village']]['population']>0 else participation) for c in cells])
 total=int(round(rawhome.sum()/100));home_units=apportion([rawhome[reg==i].sum() for i in range(len(names))],total)
 # Historical regional workplace shares are retained where comprehensive official workplace counts are unavailable.
 # Membership at registered Jakarta companies updates the DKI split only, not total employment.
 controls={'Kota Tangerang':614000,'Tangerang':751000,'Kota Tangerang Selatan':376000,'Kota Depok':381000,'Kota Bogor':315000,'Bogor':1414000,'Kota Bekasi':605000,'Bekasi':904000}
 dki=proxies['jakarta_registered_jamsostek_by_city'];controls.update({n:3747000*v/sum(dki.values()) for n,v in dki.items()})
 job_units=apportion([controls[n] for n in names],total)
 secondary={'Kota Tangerang':227/614,'Tangerang':346/751,'Kota Tangerang Selatan':62/376,'Kota Depok':92/381,'Kota Bogor':66/315,'Bogor':437/1414,'Kota Bekasi':170/605,'Bekasi':461/904}
 members=[];rw=[];jw=[];centres=[]
 for i,n in enumerate(names):
  ids=np.where(reg==i)[0];members.append(ids);p=pop[ids]/pop[ids].sum();h=rawhome[ids];rw.append(h/h.sum());industry=ind[ids];industry=industry/industry.sum() if industry.sum() else p.copy();service=com[ids];service=service/service.sum() if service.sum() else p
  if n=='Bekasi' and site[ids].sum():industry=.5*industry+.5*site[ids]/site[ids].sum()
  proxy=proxies['bekasikota_companies_by_kecamatan'] if n=='Kota Bekasi' else proxies['tangerangkota_large_industries_2023'] if n=='Kota Tangerang' else None
  if proxy:
   official=np.zeros(len(ids));denom=sum(proxy.values())
   for kec,value in proxy.items():
    mask=kecs[ids]==kec
    if not mask.any() or value==0:continue
    local=industry[mask];local=local/local.sum() if local.sum() else np.ones(mask.sum())/mask.sum();official[mask]=value/denom*local
   assert official.sum()>.99,(n,official.sum());official/=official.sum();industry=.5*industry+.5*official
  share=secondary.get(n,701/3747);j=share*(.3*p+.7*industry)+(1-share)*(.2*p+.8*service);jw.append(j/j.sum());centres.append(np.average(xy[ids],axis=0,weights=p))
 centres=np.array(centres);dist=np.linalg.norm(centres[:,None]-centres[None,:],axis=2);matrix=np.exp(-dist/18000)*home_units[:,None]*job_units[None,:];matrix/=matrix.sum()
 for _ in range(2000):
  matrix*=home_units[:,None]/matrix.sum(axis=1)[:,None];matrix*=job_units[None,:]/matrix.sum(axis=0)[None,:]
  if np.max(abs(matrix.sum(axis=1)-home_units))<1e-7:break
 integer=np.floor(matrix).astype(int);rows=home_units-integer.sum(axis=1);cols=job_units-integer.sum(axis=0)
 while rows.sum():
  scores=np.where((rows[:,None]>0)&(cols[None,:]>0),matrix-integer,-np.inf);i,j=np.unravel_index(np.argmax(scores),scores.shape);integer[i,j]+=1;rows[i]-=1;cols[j]-=1
 points=[{'id':f'dp_{i:05d}','location':c['location'],'residents':0,'jobs':0,'popIds':[]} for i,c in enumerate(cells)];point_village=[c['village'] for c in cells];clones={};pops=[]
 for i in range(len(names)):
  for j in range(len(names)):
   for a in rng.choice(members[i],int(integer[i,j]),p=rw[i]):
    a=int(a);candidates=rng.choice(members[j],32,p=jw[j]);dd=np.linalg.norm(xy[candidates]-xy[a],axis=1);weights=np.exp(-dd/18000);weights/=weights.sum();b=int(rng.choice(candidates,p=weights))
    if a==b:
     if a not in clones:
      clone=len(points);clones[a]=clone;points.append({'id':f'dp_{clone:05d}','location':points[a]['location'],'residents':0,'jobs':0,'popIds':[]});point_village.append(point_village[a])
     b=clones[a]
    meters=max(100,round(float(np.linalg.norm((np.array(points[a]['location'])-points[b]['location'])*[110600,111200]))*1.35));identifier=f'pop_{len(pops):06d}'
    pops.append({'id':identifier,'size':100,'residenceId':points[a]['id'],'jobId':points[b]['id'],'drivingDistance':meters,'drivingSeconds':round(meters/(24/3.6)+180)})
    points[a]['residents']+=100;points[b]['jobs']+=100;points[a]['popIds'].append(identifier);points[b]['popIds'].append(identifier)
 observed=collections.defaultdict(lambda:[0,0]);region_totals=collections.defaultdict(lambda:[0,0])
 for p,v in zip(points,point_village):
  observed[v][0]+=p['residents'];observed[v][1]+=p['jobs'];n=villages[v]['region'];region_totals[n][0]+=p['residents'];region_totals[n][1]+=p['jobs']
 for i,n in enumerate(names):assert region_totals[n]==[int(home_units[i])*100,int(job_units[i])*100]
 points=[p for p in points if p['popIds']]
 with gzip.open(PATH/'demand_data.json.gz','wt') as f:json.dump({'points':points,'pops':pops},f,separators=(',',':'))
 audit=[]
 for i,v in enumerate(villages):audit.append({**{k:v[k] for k in ['id','region','kecamatan','kelurahan','year','source','population_status']},'population_estimate':round(v['population'],3),'reported_working_residents':v['reported_working_residents'],'model_residents':observed[i][0],'estimated_jobs':observed[i][1],'jobs_status':'estimated; not measured kelurahan jobs'})
 with (GOV/'kelurahan_estimates.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
 stats={'version':3,'status':'local-government residential controls; estimated workplaces and OD','points':len(points),'commuter_groups':len(pops),'commuters':total*100,'seed':cfg['seed'],'grid_m':500,'population_total':inp['population_total'],'official_population_controls':inp['official_controls'],'villages':len(villages),'reported_population_years':sorted(set(v['year'] for v in villages)),'default_participation_ratio_when_missing':participation,'residents_meaning':'Modelled working trip-makers. Working-resident weights use reported SIAK occupations where available; missing areas use the median reported participation ratio. Not total inhabitants.','jobs_meaning':'Estimated workplace capacity; regional JUTPI2018 shares scaled to modelled working residents. DKI city split updated with deduplicated registered Jamsostek202406 membership. Not a current workplace census.','within_region_jobs':'OSM land-use with official Bekasi Regency industrial point locations, Bekasi city company-count kecamatan proxies2025, Tangerang city large-industry kecamatan proxies2023. No per-company staffing invented.','od_model':'Synthetic doubly constrained regional gravity,18km decay; local distance-weighted sampling. No observed home-work links.','driving_model':'1.35 straight-line detour,24km/h plus180s; no road routing or measured congestion.','source_level_population_checks_passed':inp['source_level_checks_passed'],'output_region_checks_passed':True,'region_checks':{n:{'model_residents':region_totals[n][0],'model_jobs':region_totals[n][1]} for n in names},'sources_manifest':'sources/government/source_manifest.json','quality_issues':'sources/government/quality_issues.json','kelurahan_audit':'sources/government/kelurahan_estimates.csv'}
 (PATH/'demand-method.json').write_text(json.dumps(stats,indent=2)+'\n');print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
