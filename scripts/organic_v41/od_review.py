"""v4.1 regional sensitivity scenarios; no production asset writes."""
import sys,json,csv,time
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/audit'))
from od_preview import fit,integer_round,samples
OUT=ROOT/'docs/organic-v41'
def main():
 started=time.monotonic();a=np.load(OUT/'proposed_arrays.npz');b=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz');row=b['od'].sum(1)//100;col=b['od'].sum(0)//100;names=b['names'].tolist();reg=a['regions'];xy=a['xy'];hs=[samples(xy[reg==r],a['home'][reg==r])for r in range(13)];js=[samples(xy[reg==r],a['jobs'][reg==r])for r in range(13)];d=[[cdist(h,j)/1000 for j in js]for h in hs];mats={};rows=[]
 for tau in [12,18,30]:
  kernel=np.array([[np.exp(-x/tau).mean()for x in rr]for rr in d])
  for target in [.30,.35,.40]:
   lo,hi=0.,15.
   for _ in range(60):
    v=(lo+hi)/2;k=kernel.copy();k[np.diag_indices(13)]*=np.exp(v);mat=fit(k,row,col)
    if 1-np.trace(mat)/mat.sum()>target:lo=v
    else:hi=v
   boost=float(np.exp((lo+hi)/2));k=kernel.copy();k[np.diag_indices(13)]*=boost;od=integer_round(fit(k,row,col),row,col)*100;key=f'tau{tau}_cross{round(target*100)}';mats[key]=od
   with (OUT/f'od_{key}.csv').open('w')as f:
    w=csv.writer(f,lineterminator='\n');w.writerow(['origin',*names]);w.writerows([[name,*od[i].tolist()]for i,name in enumerate(names)])
   rows.append({'scenario':key,'decay_km':tau,'cross_region_workers':int(od.sum()-od.trace()),'cross_region_fraction':float(1-od.trace()/od.sum()),'regional_origin_residual':int(abs(od.sum(1)-row*100).max()),'regional_job_residual':int(abs(od.sum(0)-col*100).max()),'diagonal_boost':boost,'point_margins':'Only regional in this table; full point transport separately for tau18cross30'})
 np.savez_compressed(OUT/'od_scenarios.npz',**mats)
 report={'scenarios':rows,'minimum_feasible_cross_workers':int(np.maximum(col-row,0).sum()*100),'bps_2023_work_cross_boundary':3614673,'bps_work_number_divided_by_model_worker_total':3614673/12646700,'interpretation':'Illustrative ratio across different reference years and model participation; not an observed share of this model.30% is a review scenario, not automatically a fitted2025 rate. Preserve40% comparison for review.','seconds':time.monotonic()-started};(OUT/'od_sensitivity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
