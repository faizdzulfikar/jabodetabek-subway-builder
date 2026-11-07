"""Regional OD scenarios using building anchors. Explicitly NOT point-level transport."""
from baseline import *
from scipy.optimize import linprog
from scipy.spatial.distance import cdist
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def fit(k,row,col):
 a=k.copy()
 for it in range(20000):
  a*= (row/a.sum(1))[:,None];a*=(col/a.sum(0))[None,:]
  if abs(a.sum(1)-row).max()<1e-7:break
 assert abs(a.sum(1)-row).max()<1e-5
 return a

def integer_round(a,row,col):
 b=np.floor(a+1e-10).astype(int);r=row-b.sum(1);c=col-b.sum(0);A=np.zeros((26,169))
 for i in range(13):A[i,i*13:(i+1)*13]=1;A[13+i,i::13]=1
 result=linprog(-(a-b).ravel(),A_eq=A,b_eq=np.r_[r,c],bounds=(0,1),method='highs');assert result.success
 b+=np.rint(result.x.reshape(13,13)).astype(int);assert np.array_equal(b.sum(1),row) and np.array_equal(b.sum(0),col);return b

def samples(x,w,n=256):
 good=w>0;x=x[good];w=w[good];p=np.cumsum(w/w.sum());idx=np.searchsorted(p,(np.arange(n)+.5)/n);return x[np.minimum(idx,len(x)-1)]

if __name__=='__main__':
 b=np.load(OUT/'baseline_arrays.npz');a=np.load(OUT/'proposed_arrays.npz');names=b['names'].tolist();row=b['od'].sum(1)//100;col=b['od'].sum(0)//100
 hh=[samples(a['xy'][a['regions']==r],a['home'][a['regions']==r]) for r in range(13)];jj=[samples(a['xy'][a['regions']==r],a['jobs'][a['regions']==r]) for r in range(13)];ds=[[cdist(hh[i],jj[j])/1000 for j in range(13)] for i in range(13)];scenarios=[];matrices={}
 for tau in [12,18,30]:
  kernel=np.array([[np.exp(-d/tau).mean() for d in dr] for dr in ds]);raw=fit(kernel,row,col)
  for target in [None,.3,.4,.5]:
   boost=1.
   if target is not None:
    lo,hi=0.,15.
    for _ in range(60):
     v=(lo+hi)/2;k=kernel.copy();k[np.diag_indices(13)]*=np.exp(v);f=fit(k,row,col);cross=1-np.trace(f)/f.sum()
     if cross>target:lo=v
     else:hi=v
    boost=float(np.exp((lo+hi)/2));kernel2=kernel.copy();kernel2[np.diag_indices(13)]*=boost;raw=fit(kernel2,row,col)
   else:raw=fit(kernel,row,col)
   od=integer_round(raw,row,col)*100;key=f'tau{tau}_'+('unadjusted' if target is None else f'cross{int(target*100)}');matrices[key]=od
   distances=[];weights=[]
   for i in range(13):
    for j in range(13):
     d=ds[i][j].ravel();w=np.exp(-d/tau);w=w/w.sum()*od[i,j];distances.append(d);weights.append(w)
   distances=np.concatenate(distances);weights=np.concatenate(weights)
   scenarios.append({'id':key,'distance_decay_km':tau,'diagonal_multiplier':boost,'cross_region_fraction':float(1-np.trace(od)/od.sum()),'total':int(od.sum()),'max_origin_residual':int(abs(od.sum(1)-b['od'].sum(1)).max()),'max_job_residual':int(abs(od.sum(0)-b['od'].sum(0)).max()),'conditional_sample_distance_km_p50_p90':weighted_quantile(distances,weights,[.5,.9]),'distance_diagnostic_warning':'Conditional pair samples do NOT preserve point marginals; regional conservation only.'})
   with (OUT/f'od_{key}.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['origin',*names]);w.writerows([[n,*od[i].tolist()] for i,n in enumerate(names)])
 np.savez_compressed(OUT/'od_scenarios.npz',**matrices);dump('od_scenarios.json',{'status':'A_sensitivity_only_not_validated_OD','regional_minimum_cross_workers':int(np.maximum(col-row,0).sum()*100),'sample_size_per_region_and_role':256,'sample_method':'systematic probability-proportional-to-size over deterministic anchor order','scenarios':scenarios,'survey_comparison':{'reported_2023_commuters_all_activities':4414914,'reported_work_fraction_rounded':.819,'approx_work_commuters':4414914*.819,'scope_warning':'Cross-kab/kota persons, age5+, work and study; survey reference2023, model controls mixed2022/2025. Do not equate commuter total to all worker trips.'},'recommended_review_scenario':'tau18_cross40','recommendation_warning':'40% is a sensitivity compromise, NOT an observed or fitted current cross-boundary commuting rate. Final rate requires comparable BPS worker OD tables and physical-workplace controls.'})
 fig,axs=plt.subplots(1,3,figsize=(18,7),layout='constrained');short=['Kab Bekasi','Kab Bogor','Kota Bekasi','Kota Bogor','Depok','Jak Barat','Jak Pusat','Jak Selatan','Jak Timur','Jak Utara','Kota Tangerang','Tangsel','Kab Tangerang'];before=b['od'];after=matrices['tau18_cross40'];vmax=max(before.max(),after.max())/1000
 for ax,z,title in zip(axs,[before,after,after-before],['Existing synthetic OD','Review scenario: 18 km + 40% cross-region','Change from existing']):
  delta='Change'in title;im=ax.imshow(z/1000,cmap='RdBu_r' if delta else 'magma',vmin=-abs(after-before).max()/1000 if delta else 0,vmax=abs(after-before).max()/1000 if delta else vmax);ax.set_xticks(range(13),short,rotation=90,fontsize=8);ax.set_yticks(range(13),short,fontsize=8);ax.set_title(title,fontsize=11);ax.set_xlabel('Workplace region');ax.set_ylabel('Residence region');fig.colorbar(im,ax=ax,shrink=.6,label='Thousand workers')
 fig.suptitle('Stage A — exact regional margins; point-level assignment remains to be built',fontsize=14);fig.savefig(OUT/'regional_od_comparison.png',dpi=170);plt.close(fig)
 print(json.dumps(scenarios,indent=2))
