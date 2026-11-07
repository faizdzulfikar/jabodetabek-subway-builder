"""Exact point and regional OD margins, followed by compatible 1.7.2 demand staging."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
from od_preview import integer_round,samples
from scipy.spatial.distance import cdist
from scipy.spatial import cKDTree
from ortools.graph.python import min_cost_flow
OUT=ROOT/'docs/organic-stage-b';SCR=Path('work/organic-stage-b')

def fit(k,row,col):
 a=k.copy();a=np.maximum(a,1e-200)
 for it in range(20000):
  a*=np.divide(row,a.sum(1),out=np.zeros(len(row)),where=a.sum(1)>0)[:,None];a*=np.divide(col,a.sum(0),out=np.zeros(len(col)),where=a.sum(0)>0)[None,:]
  if np.max(abs(a.sum(1)-row))<1e-7:break
 assert np.max(abs(a.sum(1)-row))<1e-5
 return a

def round_transport(a,row,col,rng):
 b=np.floor(a+1e-10).astype(np.int64);r=row-b.sum(1);c=col-b.sum(0);n,m=a.shape;frac=np.maximum(a-b,1e-15);starts=np.repeat(np.arange(n),m);ends=n+np.tile(np.arange(m),n);cost=np.rint(-np.log(frac.ravel())*100-rng.gumbel(0,60,n*m)).astype(np.int64);mc=min_cost_flow.SimpleMinCostFlow();arc=mc.add_arcs_with_capacity_and_unit_cost(starts,ends,np.ones(n*m,dtype=np.int64),cost);mc.set_nodes_supplies(np.arange(n+m),np.r_[r,-c]);assert mc.solve()==mc.OPTIMAL;b+=mc.flows(arc).reshape(n,m);assert np.array_equal(b.sum(1),row)and np.array_equal(b.sum(0),col);return b

def kernel_to_samples(xy,targets,tau=18000):
 return np.column_stack([np.exp(-cdist(xy,p)/tau).mean(1)for p in targets])

def pair_transport(oi,du,supply,demand,xy,rng):
 n,m=len(oi),len(du)
 for k in [32,96,256,1024]:
  kk=min(k,m);_,near=cKDTree(xy[du]).query(xy[oi],k=kk)
  if near.ndim==1:near=near[:,None]
  rand=np.searchsorted(np.cumsum(demand)/demand.sum(),rng.random((n,min(k,64))));rr=np.repeat(np.arange(n),near.shape[1]+rand.shape[1]);cc=np.column_stack([near,rand]).ravel();reverse=min(8,n);_,rn=cKDTree(xy[oi]).query(xy[du],k=reverse)
  if rn.ndim==1:rn=rn[:,None]
  rr=np.r_[rr,rn.ravel()];cc=np.r_[cc,np.repeat(np.arange(m),reverse)];key=np.unique(rr.astype(np.int64)*m+cc);rr=key//m;cc=key%m;distance=np.linalg.norm(xy[oi[rr]]-xy[du[cc]],axis=1);cost=np.rint(distance/10-rng.gumbel(0,600,len(rr))).astype(np.int64)
  mc=min_cost_flow.SimpleMinCostFlow();arcs=mc.add_arcs_with_capacity_and_unit_cost(rr,n+cc,np.minimum(supply[rr],demand[cc]).astype(np.int64),cost);mc.set_nodes_supplies(np.arange(n+m),np.r_[supply,-demand]);status=mc.solve()
  if status==mc.OPTIMAL:
   flow=mc.flows(arcs);keep=flow>0;assert flow.sum()==supply.sum();return oi[rr[keep]],du[cc[keep]],flow[keep],k
 raise RuntimeError(f'Sparse transport infeasible at {n}x{m}, expand graph rather than lose workers')

def gzsave(path,obj):
 with gzip.GzipFile(filename=str(path),mode='wb',mtime=0)as f:f.write(json.dumps(obj,separators=(',',':')).encode())

if __name__=='__main__':
 started=time.monotonic();a=np.load(OUT/'proposed_arrays.npz');alloc=readgz(OUT/'proposed_allocations.json.gz');assert not alloc['unlocated_allocations'];base=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz');xy=a['xy'];loc=a['locations'];home=a['home']//100;jobs=a['jobs']//100;reg=a['regions'];names=base['names'].tolist();row=base['od'].sum(1)//100;col=base['od'].sum(0)//100;rng=np.random.default_rng(20261107)
 hs=[samples(xy[reg==r],home[reg==r],256)for r in range(13)];js=[samples(xy[reg==r],jobs[reg==r],256)for r in range(13)];kernel=np.array([[np.exp(-cdist(hs[i],js[j])/18000).mean()for j in range(13)]for i in range(13)]);lo,hi=0.,15.
 for _ in range(60):
  v=(lo+hi)/2;k=kernel.copy();k[np.diag_indices(13)]*=np.exp(v);mat=fit(k,row,col)
  if 1-np.trace(mat)/mat.sum()>.4:lo=v
  else:hi=v
 boost=np.exp((lo+hi)/2);kernel[np.diag_indices(13)]*=boost;od=integer_round(fit(kernel,row,col),row,col);np.save(OUT/'regional_od_units.npy',od)
 origins=[];destinations=[]
 for r in range(13):
  oi=np.flatnonzero((reg==r)&(home>0));di=np.flatnonzero((reg==r)&(jobs>0));origins.append((oi,round_transport(fit(kernel_to_samples(xy[oi],js),home[oi],od[r]),home[oi],od[r],rng)));destinations.append((di,round_transport(fit(kernel_to_samples(xy[di],hs),jobs[di],od[:,r]),jobs[di],od[:,r],rng)));print('regional point margins',r,flush=True)
 aa=[];bb=[];mass=[];ks=[]
 for r in range(13):
  for s in range(13):
   oi,os=origins[r];di,dd=destinations[s];om=os[:,s]>0;dm=dd[:,r]>0
   if not om.any():continue
   pa,pb,pm,kk=pair_transport(oi[om],di[dm],os[om,s],dd[dm,r],xy,rng);aa.extend(pa.tolist());bb.extend(pb.tolist());mass.extend(pm.tolist());ks.append(kk)
  print('matched origin region',r,flush=True)
 aa=np.array(aa);bb=np.array(bb);mass=np.array(mass);assert np.array_equal(np.bincount(aa,weights=mass,minlength=len(xy)),home);assert np.array_equal(np.bincount(bb,weights=mass,minlength=len(xy)),jobs);actual=np.zeros((13,13),np.int64);np.add.at(actual,(reg[aa],reg[bb]),mass);assert np.array_equal(actual,od)
 # Every group remains100 workers. On-site travel gets a distinct destination ID at the same valid feature.
 points=[{'id':f'o{i:06d}','location':p['location'],'residents':int(home[i]*100),'jobs':int(jobs[i]*100),'popIds':[]}for i,p in enumerate(alloc['points'])];pops=[];clones={};point_source=list(range(len(points)))
 distances=[];seconds=[];weights=[]
 for u,v,units in zip(aa,bb,mass):
  u=int(u);v=int(v);vv=v;straight=float(np.linalg.norm(xy[u]-xy[v]));meters=max(100,round(straight*1.35));secs=round(meters/(24/3.6)+180)
  if u==v:
   if v not in clones:clones[v]=len(points);points.append({'id':points[v]['id']+'_onsite','location':points[v]['location'],'residents':0,'jobs':0,'popIds':[]});point_source.append(v)
   vv=clones[v];points[v]['jobs']-=int(units*100);points[vv]['jobs']+=int(units*100)
  for _ in range(int(units)):
   pid=f'pop_{len(pops):06d}';pops.append({'id':pid,'size':100,'residenceId':points[u]['id'],'jobId':points[vv]['id'],'drivingDistance':meters,'drivingSeconds':secs});points[u]['popIds'].append(pid);points[vv]['popIds'].append(pid)
  distances.append(straight/1000);seconds.append(secs/60);weights.append(int(units*100))
 sources={p['id']:int(src)for p,src in zip(points,point_source)if p['popIds']};points=[p for p in points if p['popIds']];candidate=OUT/'candidate-demand.json.gz';gzsave(candidate,{'points':points,'pops':pops});gzsave(OUT/'engine_point_sources.json.gz',sources);np.savez_compressed(OUT/'od_pairs.npz',origin=aa,destination=bb,units=mass)
 with (OUT/'regional_od.csv').open('w')as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['origin',*names]);w.writerows([[n,*(od[i]*100).tolist()]for i,n in enumerate(names)])
 report={'version':4,'stage':'B_STAGED','seed':20261107,'population':int(a['population'].sum()),'allocation_anchors':len(xy),'engine_points':len(points),'onsite_clone_points':len(clones),'groups':len(pops),'workers':len(pops)*100,'regional_origins_exact':True,'regional_destinations_exact':True,'all_point_origins_exact':True,'all_point_jobs_exact':True,'cross_region_workers':int((od.sum()-od.trace())*100),'cross_region_fraction':float(1-od.trace()/od.sum()),'decay_km':18,'diagonal_preference':float(boost),'within_region_distance_noise_km':6,'sparse_candidate_k_max':max(ks),'straight_distance_km_p10_p50_p90_p95_p99':weighted_quantile(distances,weights,[.1,.5,.9,.95,.99]),'proxy_travel_minutes_p50_p90_p95':weighted_quantile(seconds,weights,[.5,.9,.95]),'onsite_worker_fraction':float(np.array(weights)[aa==bb].sum()/sum(weights)),'candidate_gzip_bytes':candidate.stat().st_size,'seconds':time.monotonic()-started,'travel_time_status':'Proxy:1.35*straight distance,24km/h+180s; network-routing sample audited separately, not measured congestion','od_status':'Synthetic reviewed40% cross-region scenario, not an observed2026 OD census','transport_method':'Entropy-kernel IPF + integer min-cost rounding for point-to-region marginals; perturbed sparse min-cost matching within each regional pair. All point and regional margins exact.'};(OUT/'demand_checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
