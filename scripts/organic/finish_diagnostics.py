"""Final before/after OD plots and capacity-prior sensitivity; never engine writes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from calibrate_jobs import apportion
OUT=ROOT/'docs/organic-stage-b'
if __name__=='__main__':
 a=np.load(OUT/'proposed_arrays.npz');b=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz');od=np.load(OUT/'regional_od_units.npy')*100;short=['Kab Bekasi','Kab Bogor','Kota Bekasi','Kota Bogor','Depok','Jak Barat','Jak Pusat','Jak Selatan','Jak Timur','Jak Utara','Kota Tangerang','Tangsel','Kab Tangerang'];fig,axs=plt.subplots(1,3,figsize=(18,7),layout='constrained');vmax=max(od.max(),b['od'].max())/1000;delta=od-b['od'];maxdelta=abs(delta).max()/1000
 for ax,z,title in zip(axs,[b['od'],od,delta],['Existing v3','Organic v4 — exact point/regional margins','Change']):
  change=title=='Change';im=ax.imshow(z/1000,cmap='RdBu_r'if change else'magma',vmin=-maxdelta if change else 0,vmax=maxdelta if change else vmax);ax.set_xticks(range(13),short,rotation=90,fontsize=8);ax.set_yticks(range(13),short,fontsize=8);ax.set_title(title);ax.set_xlabel('Work region');ax.set_ylabel('Home region');fig.colorbar(im,ax=ax,shrink=.65,label='Thousand workers')
 fig.suptitle('Synthetic commuting scenario — source regional totals unchanged');fig.savefig(OUT/'regional_od_comparison.png',dpi=170);plt.close(fig)
 pairs=np.load(OUT/'od_pairs.npz');dnew=np.linalg.norm(a['xy'][pairs['origin']]-a['xy'][pairs['destination']],axis=1)/1000;dold=np.linalg.norm(b['xy'][b['orig']]-b['xy'][b['dest']],axis=1)/1000;fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
 for dist,w,label in [(dold,b['mass'],'v3'),(dnew,pairs['units']*100,'organic v4')]:
  ix=np.argsort(dist);ax.plot(dist[ix],np.cumsum(w[ix])/sum(w),label=label)
 ax.set(xlabel='Straight-line home–work km',ylabel='Cumulative worker share',xlim=(0,65),title='Actual generated OD pairs — not a survey fit');ax.legend();fig.savefig(OUT/'od_distance_comparison.png',dpi=170);plt.close(fig)
 alloc=readgz(OUT/'proposed_allocations.json.gz');cap=np.array([p['relative_employment_capacity']for p in alloc['points']]);res=np.array([p['relative_residential_capacity']for p in alloc['points']]);reg=a['regions'];sens=[]
 for multiplier in [1.5,2.,3.]:
  for local_min in [.1,.2,.3]:
   jobs=np.zeros(len(res),np.int64);shares=[]
   for r in range(13):
    ids=np.flatnonzero(reg==r);total=int(b['od'].sum(0)[r]);component=np.minimum((1-local_min)*total*cap[ids]/cap[ids].sum(),multiplier*cap[ids]);remaining=total-component.sum();jobs[ids]=apportion(component+remaining*res[ids]/res[ids].sum(),total//100)*100;shares.append(remaining/total)
   assert jobs.sum()==12646700
   row={'capacity_ceiling_multiplier':multiplier,'minimum_unclassified_component':local_min,'jobs_total':int(jobs.sum()),'largest_anchor_jobs':int(jobs.max()),'unclassified_component_by_region':dict(zip(b['names'].tolist(),shares)),'centers':[]}
   for priority,name,(x0,y0,x1,y1)in CENTERS:
    loc=a['locations'];m=(loc[:,0]>=x0)&(loc[:,0]<=x1)&(loc[:,1]>=y0)&(loc[:,1]<=y1);row['centers'].append({'name':name,'jobs':int(jobs[m].sum())})
   sens.append(row)
 (OUT/'capacity_sensitivity.json').write_text(json.dumps({'selected':{'capacity_ceiling_multiplier':2.,'minimum_unclassified_component':.2},'scenarios':sens,'meaning':'Scenario uncertainty; not confidence intervals or observed informal/homework shares'},indent=2))
 cross=a['regions'][pairs['origin']]!=a['regions'][pairs['destination']];metrics={'cross_region_distance_km_p50_p90':weighted_quantile(dnew[cross],pairs['units'][cross],[.5,.9]),'over50km_fraction':float(pairs['units'][dnew>50].sum()/pairs['units'].sum()),'top_1pct_anchor_job_share':float(np.sort(a['jobs'])[-max(1,len(a['jobs'])//100):].sum()/a['jobs'].sum()),'duplicate_coordinate_records_excluding_onsite_clones':len(a['locations'])-len(np.unique(a['locations'],axis=0))};(OUT/'final_spatial_metrics.json').write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2))

 # Capacity review is an output, separate from frozen coverage-support inputs.
 vs=readgz(ROOT/'assets/JKT/government_inputs.json.gz')['villages'];vp=np.bincount(a['villages'],weights=a['population'],minlength=len(vs));vc=np.bincount(a['villages'],weights=res,minlength=len(vs));review=[{'admin_id':v['id'],'region':v['region'],'kecamatan':v['kecamatan'],'kelurahan':v['kelurahan'],'population':int(vp[i]),'relative_residential_capacity':float(vc[i]),'population_to_prior_capacity':float(vp[i]/vc[i])if vc[i]>0 else None}for i,v in enumerate(vs)];flag=[x for x in review if x['population_to_prior_capacity']and x['population_to_prior_capacity']>5];(OUT/'residential_capacity_review.json').write_text(json.dumps({'meaning':'Coverage/floor/occupancy uncertainty, not measured overcrowding. Official village population remains exact.','baseline_risk_villages':263,'villages_over5x_prior_capacity':len(flag),'flagged_villages':flag,'all_villages':review},indent=2))
