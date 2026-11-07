"""Read-only v3 diagnostics. Every output stays in docs/organic-stage-a or scratch."""
from pathlib import Path
import gzip,json,csv,time,collections,hashlib
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-stage-a';OUT.mkdir(exist_ok=True)
CENTERS=[('P0','Sudirman–Thamrin–SCBD',[106.79,-6.245,106.835,-6.175]),('P0','Kuningan–Mega Kuningan–Rasuna Said',[106.818,-6.245,106.845,-6.205]),('P0','Gatot Subroto–Semanggi',[106.79,-6.245,106.852,-6.22]),('P0','TB Simatupang–Cilandak',[106.765,-6.31,106.855,-6.278]),('P0','Cikarang–Cibitung–MM2100–Jababeka',[107.01,-6.375,107.21,-6.225]),('P1','BSD–Serpong',[106.61,-6.325,106.69,-6.265]),('P1','Alam Sutera–Gading Serpong',[106.605,-6.265,106.68,-6.215]),('P1','Sunter–Kelapa Gading',[106.852,-6.19,106.93,-6.12]),('P1','Cakung–Pulogadung',[106.887,-6.235,106.985,-6.16]),('P1','Slipi–Palmerah–Grogol',[106.775,-6.215,106.815,-6.15]),('P1','Pluit–PIK–Penjaringan',[106.70,-6.14,106.805,-6.075]),('P1','Jatiuwung–Batuceper–Balaraja',[106.415,-6.255,106.665,-6.115]),('P2','Margonda–Depok',[106.81,-6.415,106.845,-6.345]),('P2','Bekasi Selatan–Summarecon',[106.975,-6.27,107.035,-6.205]),('P2','Bogor Tengah–Baranangsiang',[106.785,-6.625,106.835,-6.575])]
def readgz(p):return json.load(gzip.open(p,'rt'))
def dump(name,x): (OUT/name).write_text(json.dumps(x,indent=2)+'\n')
def weighted_quantile(values,weights,qs):
 order=np.argsort(values);v=np.array(values)[order];w=np.array(weights)[order];return np.interp(np.array(qs)*w.sum(),np.cumsum(w),v).tolist()
def expected_weights(inp,proxies):
 cells=inp['cells'];vs=inp['villages'];names=sorted(set(c['region'] for c in cells));reg=np.array([names.index(c['region']) for c in cells]);p=np.array([c['population'] for c in cells]);raw=np.array([c['population']*(vs[c['village']]['reported_working_residents']/vs[c['village']]['population'] if vs[c['village']]['reported_working_residents'] is not None and vs[c['village']]['population']>0 else .3891186367704876) for c in cells]);jw=np.zeros(len(cells));rw=np.zeros(len(cells));sec={'Kota Tangerang':227/614,'Tangerang':346/751,'Kota Tangerang Selatan':62/376,'Kota Depok':92/381,'Kota Bogor':66/315,'Bogor':437/1414,'Kota Bekasi':170/605,'Bekasi':461/904};kecs=np.array([''.join(ch for ch in vs[c['village']]['kecamatan'].upper() if ch.isalnum()) for c in cells])
 for i,n in enumerate(names):
  ids=np.where(reg==i)[0];pop=p[ids]/p[ids].sum();rw[ids]=raw[ids]/raw[ids].sum();ind=np.array([cells[q]['industrial_m2'] for q in ids]);com=np.array([cells[q]['commercial_m2'] for q in ids]);site=np.array([cells[q]['official_industry_sites'] for q in ids]);ind=ind/ind.sum() if ind.sum() else pop;com=com/com.sum() if com.sum() else pop
  if n=='Bekasi' and site.sum():ind=.5*ind+.5*site/site.sum()
  proxy=proxies['bekasikota_companies_by_kecamatan'] if n=='Kota Bekasi' else proxies['tangerangkota_large_industries_2023'] if n=='Kota Tangerang' else None
  if proxy:
   off=np.zeros(len(ids))
   for k,v in proxy.items():
    mask=kecs[ids]==k
    if not mask.any() or not v:continue
    w=ind[mask];w=w/w.sum() if w.sum() else np.ones(mask.sum())/mask.sum();off[mask]=v/sum(proxy.values())*w
   off/=off.sum();ind=.5*ind+.5*off
  s=sec.get(n,701/3747);j=s*(.3*pop+.7*ind)+(1-s)*(.2*pop+.8*com);jw[ids]=j/j.sum()
 return names,reg,rw,jw
if __name__=='__main__':
 t=time.monotonic();d=readgz(ROOT/'assets/JKT/demand_data.json.gz');inp=readgz(ROOT/'assets/JKT/government_inputs.json.gz');ps=d['points'];pops=d['pops'];cells=inp['cells'];vs=inp['villages'];names,reg,rw,jw=expected_weights(inp,json.loads((ROOT/'sources/government/workplace_proxies.json').read_text()))
 coordmap={tuple(c['location']):i for i,c in enumerate(cells)};cellids=np.array([int(p['id'][3:]) if int(p['id'][3:])<len(cells) else coordmap[tuple(p['location'])] for p in ps]);villageids=np.array([cells[c]['village'] for c in cellids]);preg=reg[cellids];locations=np.array([p['location'] for p in ps]);home=np.array([p['residents'] for p in ps]);jobs=np.array([p['jobs'] for p in ps]);xy=np.array(Transformer.from_crs(4326,32748,always_xy=True).transform(*locations.T)).T
 pidx={p['id']:i for i,p in enumerate(ps)};orig=np.array([pidx[p['residenceId']] for p in pops]);dest=np.array([pidx[p['jobId']] for p in pops]);mass=np.array([p['size'] for p in pops]);distance=np.linalg.norm(xy[orig]-xy[dest],axis=1)/1000;seconds=np.array([p['drivingSeconds'] for p in pops]);od=np.zeros((13,13),dtype=np.int64);np.add.at(od,(preg[orig],preg[dest]),mass)
 def phase_stats(a):
  phase=a%500;delta=abs(phase-250);return {'within_2m_cell_center_axis_fraction':float(np.mean(delta<2)),'within_10m_both_axes_fraction':float(np.mean(np.all(delta<10,axis=1))),'phase_histogram_25m':np.histogram(phase.ravel(),bins=np.arange(0,501,25))[0].tolist()}
 duplicate=len(ps)-len({tuple(p['location']) for p in ps});maxid=int(np.argmax(jobs));expectedjobs=jw*np.bincount(preg,weights=jobs,minlength=13)[reg];actualcell=np.bincount(cellids,weights=jobs,minlength=len(cells));tv={n:float(.5*np.abs(actualcell[reg==i]-expectedjobs[reg==i]).sum()/jobs[preg==i].sum()) for i,n in enumerate(names)}
 vh=np.bincount(villageids,weights=home,minlength=len(vs));vj=np.bincount(villageids,weights=jobs,minlength=len(vs));expectedh=rw*np.bincount(preg,weights=home,minlength=13)[reg];evh=np.bincount([c['village'] for c in cells],weights=expectedh,minlength=len(vs));errors=vh-evh
 checks={'stage':'A','production_commit':'824ec8e7f42484c680e7b2467cbb7dccf62df289','points':len(ps),'cells_before_zero_filter':len(cells),'groups':len(pops),'model_tripmakers':int(mass.sum()),'population_control_total':inp['population_total'],'duplicate_coordinate_records':duplicate,'unique_village_count_with_origins':int(np.count_nonzero(vh)),'villages_without_jobs':int(np.sum(vj==0)),'grid_phase':phase_stats(xy),'same_coordinate_trip_fraction':float(mass[np.all(locations[orig]==locations[dest],axis=1)].sum()/mass.sum()),'within_region_trip_fraction':float(np.trace(od)/od.sum()),'distance_km_quantiles_p10_p50_p90_p95_p99':weighted_quantile(distance,mass,[.1,.5,.9,.95,.99]),'cross_region_distance_km_quantiles_p50_p90':weighted_quantile(distance[preg[orig]!=preg[dest]],mass[preg[orig]!=preg[dest]],[.5,.9]),'travel_minutes_quantiles_p50_p90_p95':weighted_quantile(seconds/60,mass,[.5,.9,.95]),'trips_over_50km_fraction':float(mass[distance>50].sum()/mass.sum()),'largest_point_jobs':{'id':ps[maxid]['id'],'jobs':int(jobs[maxid]),'location':locations[maxid].tolist(),'village':vs[villageids[maxid]]['kelurahan']},'top_1_percent_points_job_share':float(np.sort(jobs)[-max(1,len(jobs)//100):].sum()/jobs.sum()),'local_job_target_total_variation_by_region':tv,'max_village_origin_deviation_from_expected':float(abs(errors).max()),'villages_with_origin_deviation_over_10percent':int(np.sum(abs(errors)>np.maximum(100,.1*evh))),'read_and_diagnostics_seconds':time.monotonic()-t,'regional_origins':od.sum(axis=1).tolist(),'regional_destinations':od.sum(axis=0).tolist()};dump('baseline_metrics.json',checks);dump('employment_centers.json',[{'priority':p,'name':n,'bbox':b,'bbox_role':'audit window only; overlapping; never used as a weight or boost'} for p,n,b in CENTERS])
 np.savez_compressed(OUT/'baseline_arrays.npz',locations=locations,xy=xy,home=home,jobs=jobs,cellids=cellids,villageids=villageids,regions=preg,orig=orig,dest=dest,mass=mass,od=od,names=names)
 with (OUT/'regional_od_before.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['origin',*names]);w.writerows([[n,*od[i].tolist()] for i,n in enumerate(names)])
 print(json.dumps(checks,indent=2))
