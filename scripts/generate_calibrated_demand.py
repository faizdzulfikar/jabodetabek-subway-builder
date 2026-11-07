"""Calibrated marginal totals with synthetic, doubly constrained gravity OD.

Residents in the game are modelled trip-makers, not the entire WorldPop population.
No claim of observed 500m employment or survey-derived OD is made.
"""
from pathlib import Path
import gzip,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def apportion(weights,total):
 v=np.asarray(weights,dtype=float); v=v/v.sum()*total
 out=np.floor(v).astype(int); out[np.argsort(-(v-out),kind='stable')[:total-int(out.sum())]]+=1
 return out
def main():
 cfg=json.loads((ROOT/'config.json').read_text()); rng=np.random.default_rng(cfg['seed'])
 path=ROOT/'assets/JKT'; inputs=json.load(gzip.open(path/'calibration_inputs.json.gz','rt'));cells=inputs['cells']
 names=sorted(inputs['population_in_map']); idx={n:i for i,n in enumerate(names)}
 # JUTPI2 Annex04 Table39, 2018 workplace counts, thousands. Use counts, not inconsistent printed percentages.
 controls={'Kota Tangerang':614000,'Tangerang':751000,'Kota Tangerang Selatan':376000,'Kota Depok':381000,'Kota Bogor':315000,'Bogor':1414000,'Kota Bekasi':605000,'Bekasi':904000}
 # Split JUTPI's DKI aggregate using BPS SE2016 workplace employment proportions.
 dki={'Kota Jakarta Selatan':2295822,'Kota Jakarta Timur':1557232,'Kota Jakarta Pusat':1160448,'Kota Jakarta Barat':1332810,'Kota Jakarta Utara':1001477}
 controls.update({n:3747000*v/sum(dki.values()) for n,v in dki.items()})
 coverage={n:inputs['population_in_map'][n]/inputs['population_full_regions'][n] for n in names}
 # Population coverage is an explicit proxy for workplaces outside the rectangular game extent.
 job_units=np.rint([controls[n]*coverage[n]/100 for n in names]).astype(int)
 total=int(job_units.sum()); pop=np.array([c['population'] for c in cells]); reg=np.array([idx[c['region']] for c in cells])
 home_units=apportion([inputs['population_in_map'][n] for n in names],total)
 loc=np.array([c['location'] for c in cells]); xy=loc*[110600,111200]
 industrial=np.array([c['industrial_m2'] for c in cells]); commercial=np.array([c['commercial_m2'] for c in cells])
 # Secondary-sector shares in Table39; remaining jobs use commercial/service areas plus dispersed employment.
 secondary={'Kota Tangerang':227/614,'Tangerang':346/751,'Kota Tangerang Selatan':62/376,'Kota Depok':92/381,'Kota Bogor':66/315,'Bogor':437/1414,'Kota Bekasi':170/605,'Bekasi':461/904}
 rw=[];jw=[];members=[];centres=[]
 for n in names:
  ids=np.where(reg==idx[n])[0];members.append(ids)
  p=pop[ids];p=p/p.sum();ind=industrial[ids];com=commercial[ids]
  ind=ind/ind.sum() if ind.sum() else p;com=com/com.sum() if com.sum() else p
  share=secondary.get(n,701/3747)
  j=share*(.3*p+.7*ind)+(1-share)*(.2*p+.8*com)
  rw.append(p);jw.append(j/j.sum());centres.append(np.average(xy[ids],axis=0,weights=p))
 centres=np.array(centres);dist=np.linalg.norm(centres[:,None]-centres[None,:],axis=2)
 matrix=np.exp(-dist/18000)*home_units[:,None]*job_units[None,:]; matrix/=matrix.sum()
 for _ in range(2000):
  matrix*=home_units[:,None]/matrix.sum(axis=1)[:,None]
  matrix*=job_units[None,:]/matrix.sum(axis=0)[None,:]
  if np.max(abs(matrix.sum(axis=1)-home_units))<1e-7:break
 integer=np.floor(matrix).astype(int); row=home_units-integer.sum(axis=1);col=job_units-integer.sum(axis=0)
 while row.sum():
  choices=np.where((row[:,None]>0)&(col[None,:]>0),matrix-integer,-np.inf)
  i,j=np.unravel_index(np.argmax(choices),choices.shape);integer[i,j]+=1;row[i]-=1;col[j]-=1
 points=[{'id':f'dp_{i:05d}','location':c['location'],'residents':0,'jobs':0,'popIds':[]} for i,c in enumerate(cells)]
 pops=[]
 for i in range(len(names)):
  for j in range(len(names)):
   count=int(integer[i,j]); origins=rng.choice(members[i],count,p=rw[i]);destinations=[]
   for origin in origins:
    candidates=rng.choice(members[j],32,p=jw[j])
    distances=np.linalg.norm(xy[candidates]-xy[origin],axis=1)
    weights=np.exp(-distances/18000); weights/=weights.sum()
    destinations.append(rng.choice(candidates,p=weights))
   for a,b in zip(origins,destinations):
    a=int(a);b=int(b)
    # Separate co-located origin/destination records permit same-cell jobs without dropping trips.
    if a==b:
     b=len(points); points.append({'id':f'dp_{b:05d}','location':points[a]['location'],'residents':0,'jobs':0,'popIds':[]})
    meters=max(100,round(float(np.linalg.norm((np.array(points[a]['location'])-points[b]['location'])*[110600,111200]))*1.35))
    identifier=f'pop_{len(pops):06d}'
    pops.append({'id':identifier,'size':100,'residenceId':points[a]['id'],'jobId':points[b]['id'],'drivingDistance':meters,'drivingSeconds':round(meters/(24/3.6)+180)})
    points[a]['residents']+=100;points[b]['jobs']+=100;points[a]['popIds'].append(identifier);points[b]['popIds'].append(identifier)
 points=[p for p in points if p['popIds']]
 with gzip.open(path/'demand_data.json.gz','wt') as f:json.dump({'points':points,'pops':pops},f,separators=(',',':'))
 stats={'status':'WorldPop residential weights; region-calibrated historical workplace model; synthetic OD','version':2,'seed':cfg['seed'],'grid_m':500,'points':len(points),'commuter_groups':len(pops),'commuters':total*100,'worldpop_population_in_map':sum(inputs['population_in_map'].values()),'residents_meaning':'Modelled workers/trip-makers, not all inhabitants. Origins proportional to WorldPop 2025; uniform regional participation assumption.','jobs_meaning':'JUTPI2 2018 workplace counts scaled by population coverage of map; DKI split by BPS SE2016 workplace shares. Not 2025 job counts.','within_region_jobs':'OSM industry/commercial areas plus population fallback; not measured 500m employment.','od_model':'Doubly constrained regional gravity, 18km decay, IPF; within-region distance-weighted sampling of workplace candidates (18km decay); point jobs remain modelled. NOT calibrated to BPS commuter OD.','driving_model':'1.35 times straight-line distance, 24km/h plus180s; no road routing or measured congestion.','sources':{'population':'https://api.stac.worldpop.org/collections/IDN/items/idn_pop_2025_CN_100m_R2025A_v1','workplace':'https://openjicareport.jica.go.jp/pdf/12356382.pdf (Table39, printed p60)','dki_split':'https://jakarta.bps.go.id/id/statistics-table/2/OTQ5IzI%3D/banyaknya-tenaga-kerja-menurut-wilayah-dan-skala-usaha--provinsi-dki-jakarta-hasil-se2016-.html','boundaries':'https://www.geoboundaries.org/api/current/gbOpen/IDN/ADM2/'},'region_checks':{n:{'population_in_map':round(inputs['population_in_map'][n]),'coverage':round(coverage[n],6),'model_residents':int(home_units[i])*100,'model_jobs':int(job_units[i])*100} for i,n in enumerate(names)},'marginal_checks':{'origin_rows_exact':bool(np.array_equal(integer.sum(axis=1),home_units)),'job_columns_exact':bool(np.array_equal(integer.sum(axis=0),job_units))}}
 (path/'demand-method.json').write_text(json.dumps(stats,indent=2)+'\n');print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
