"""Additional before/after metrics, density sensitivity and visual review artifacts."""
from pathlib import Path
import json,gzip,csv,sqlite3,zlib,time,hashlib,sys
import numpy as np
import shapely
from scipy.spatial.distance import cdist
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import LogNorm,TwoSlopeNorm
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41'
def load(n):return json.loads((OUT/n).read_text())
def gzread(p):return json.load(gzip.open(p,'rt'))
def dump(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
def csvout(n,rr):
 with (OUT/n).open('w')as f:w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
def quant(x,w,qq=[.1,.5,.9,.95,.99]):
 ix=np.argsort(x);return np.interp(np.array(qq)*sum(w),np.cumsum(w[ix]),x[ix]).tolist()
def apportion(w,total):
 q=w/sum(w)*total;a=np.floor(q).astype(np.int64);a[np.argsort(-(q-a),kind='stable')[:int(total-sum(a))]]+=1;return a
if __name__=='__main__':
 a=np.load(OUT/'proposed_arrays.npz');b=np.load(ROOT/'docs/organic-stage-b/proposed_arrays.npz');base=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz');p=gzread(OUT/'proposed_allocations.json.gz')['points'];n=len(b['jobs']);oldjobs=np.r_[b['jobs'],np.zeros(len(p)-n)];oldhome=np.r_[b['home'],np.zeros(len(p)-n)];oldpop=np.r_[b['population'],np.zeros(len(p)-n)];names=base['names'].tolist();reg=a['regions'];xy=a['xy'];loc=a['locations'];area=list(csv.DictReader((OUT/'area_comparison.csv').open()));geo=gzread(OUT/'audit_boundaries.geojson.gz');masks=np.load(OUT/'area_masks.npz');pairs=np.load(OUT/'od_pairs.npz');oldpairs=np.load(ROOT/'docs/organic-stage-b/od_pairs.npz');od=np.load(OUT/'regional_od_units.npy')*100;oldod=np.load(ROOT/'docs/organic-stage-b/regional_od_units.npy')*100
 # District-wide exact administrative controls, contrasted with spatial clipping.
 vs=gzread(ROOT/'assets/JKT/government_inputs.json.gz')['villages'];vr=list(csv.DictReader((OUT/'village_comparison.csv').open()));byid={x['admin_id']:x for x in vr};norm=lambda s:''.join(x for x in s.upper()if x.isalnum())
 rows=[]
 for name,kec in sorted(set((v['region'],v['kecamatan'])for v in vs)):
  vv=[i for i,v in enumerate(vs)if v['region']==name and v['kecamatan']==kec];ids=np.isin(a['villages'],vv);ni=ids[:n];status=[v['population_status']for i,v in enumerate(vs)if i in vv];total=int(a['population'][ids].sum());fallback=sum(int(x['population'])for i,x in enumerate(p)if ids[i]and x['anchor_kind']=='builtup_parcel');rc=sum(x['relative_residential_capacity']for i,x in enumerate(p)if ids[i]);rows.append({'region':name,'kecamatan':kec,'source_years':','.join(sorted({str(v['year'])for i,v in enumerate(vs)if i in vv})),'population_current':int(b['population'][ni].sum()),'population_proposed':total,'working_origins_current':int(b['home'][ni].sum()),'working_origins_proposed':int(a['home'][ids].sum()),'jobs_current':int(b['jobs'][ni].sum()),'jobs_proposed':int(a['jobs'][ids].sum()),'population_fallback_share':fallback/max(total,1),'population_to_relative_capacity':total/max(rc,1),'anchors':int(ids.sum()),'direct_kelurahan_controls':sum(x=='observed_kelurahan'for x in status),'derived_village_estimates':sum(x!='observed_kelurahan'for x in status)})
 csvout('all_district_comparison.csv',rows)
 priority={norm(x.split(' · ')[0])for x in load('area_order.json')}
 discovered=sorted([x for x in rows if norm(x['kecamatan'])not in priority],key=lambda x:(x['population_fallback_share'],x['population_to_relative_capacity']),reverse=True)[:15];csvout('additional_coverage_review.csv',discovered)
 # Proportional res evidence, floor ceiling and intensity pilot remain separate.
 cap=np.array([x['relative_employment_capacity']for x in p]);rc=np.array([x['relative_residential_capacity']for x in p]);pilot=gzread(OUT/'pilot_allocations.json.gz')['points'];pcap=np.array([x['relative_employment_capacity']for x in pilot]);sens=[]
 for label,cp in [('S0_existing_intensities',cap),('S1_function_specific_pilot',pcap)]:
  for ceiling in [1,2,3]:
   jj=np.zeros(len(p),np.int64);fallback=[]
   for ri,name in enumerate(names):
    ii=np.flatnonzero(reg==ri);total=int(oldjobs[ii].sum());fl=np.minimum(.8*total*cp[ii]/cp[ii].sum(),ceiling*cp[ii]);res=total-fl.sum();jj[ii]=apportion(fl+res*rc[ii]/rc[ii].sum(),total//100)*100;fallback.append(float(res/total))
   for i,aa in enumerate(area):
    if aa['kind']not in ['industrial','airport','employment_core']:continue
    ids=masks[str(i)];sens.append({'capacity_scenario':label,'ceiling':ceiling,'area':aa['name'],'jobs':int(jj[ids].sum()),'total_jobs':int(jj.sum()),'max_regional_residual':int(max(abs(jj[reg==ri].sum()-oldjobs[reg==ri].sum())for ri in range(13))),'uncertainty':'Intensity/ceiling sensitivity, not observed workforce'})
 csvout('capacity_sensitivity.csv',sens)
 # OD corridor diagnostics require actual point pairs, not regional population proxies.
 def stats(pp,x,r):
  u=pp['origin'];v=pp['destination'];w=pp['units']*100;dist=np.linalg.norm(x[u]-x[v],axis=1)/1000
  return {'workers':int(sum(w)),'cross_region_workers':int(w[r[u]!=r[v]].sum()),'cross_region_fraction':float(w[r[u]!=r[v]].sum()/sum(w)),'distance_km_p10_p50_p90_p95_p99':quant(dist,w),'trips_over50km':int(w[dist>50].sum()),'onsite_workers':int(w[u==v].sum())}
 ds={'current':stats(oldpairs,b['xy'],b['regions']),'proposed_S0_tau18_cross30':stats(pairs,xy,reg),'caution':'30% and40% use administrative kab/kota including Jakarta cities; travel seconds remain proxy, not congestion','not_work_trip_to_passenger_trip_conversion':True};dump('od_diagnostics.json',ds)
 cor=[]
 for ri,name in enumerate(names):
  u=pairs['origin'];v=pairs['destination'];w=pairs['units']*100;ou=oldpairs['origin'];ov=oldpairs['destination'];ow=oldpairs['units']*100;jak=np.array(['Jakarta'in x for x in names]);mask=(reg[u]==ri)&jak[reg[v]];om=(b['regions'][ou]==ri)&jak[b['regions'][ov]];cross=(reg[u]==ri)&(reg[v]!=ri);oc=(b['regions'][ou]==ri)&(b['regions'][ov]!=ri)
  cor.append({'origin':name,'working_origins':int(a['home'][reg==ri].sum()),'current_to_jakarta':int(ow[om].sum()),'proposed_to_jakarta':int(w[mask].sum()),'current_cross_region':int(ow[oc].sum()),'proposed_cross_region':int(w[cross].sum()),'current_local':int(oldod[ri,ri]),'proposed_local':int(od[ri,ri])})
 csvout('regional_corridor_od.csv',cor)
 locflows=[]
 for i,aa in enumerate(area):
  if aa['kind']not in ['residential_admin','industrial','residential_named']:continue
  ids=masks[str(i)];u=pairs['origin'];v=pairs['destination'];w=pairs['units']*100;ou=oldpairs['origin'];ov=oldpairs['destination'];ow=oldpairs['units']*100;olds=ids[:n]
  local=ids[u]&ids[v];oldlocal=olds[ou]&olds[ov];dist=np.linalg.norm(xy[u]-xy[v],axis=1)/1000
  locflows.append({'area':aa['name'],'origins_current':int(oldhome[ids].sum()),'origins_proposed':int(a['home'][ids].sum()),'jobs_current':int(oldjobs[ids].sum()),'jobs_proposed':int(a['jobs'][ids].sum()),'within_defined_area_current':int(ow[oldlocal].sum()),'within_defined_area_proposed':int(w[local].sum()),'origin_trips_within10km_current':int(ow[olds[ou]&(np.linalg.norm(b['xy'][ou]-b['xy'][ov],axis=1)<10000)].sum()),'origin_trips_within10km_proposed':int(w[ids[u]&(dist<10)].sum())})
 csvout('local_corridor_od.csv',locflows)
 # Airport non-overlapping anchor role diagnostics; buildings do not share jobs twice.
 db=sqlite3.connect('work/organic-audit/inventory.sqlite');air=next(shape['geometry']for shape in geo['features']if shape['properties']['kind']=='airport');air=shapely.geometry.shape(air);inside=shapely.intersects_xy(air,loc[:,0],loc[:,1]);role={}
 for oid,ts in db.execute('select id,tags from buildings where lon between 106.62 and 106.69 and lat between -6.16 and -6.09'):
  t=json.loads(ts);name=t.get('name','').lower();k='unclassified_or_neighborhood'
  if t.get('aeroway')=='terminal':k='passenger_terminal_buildings'
  elif t.get('aeroway')=='hangar'or t.get('building')=='hangar':k='maintenance_hangars'
  elif any(x in name for x in ['cargo','kargo']):k='cargo_logistics'
  elif any(x in name for x in ['ground support','pt. jas','ground handling']):k='ground_handling'
  elif t.get('office')or'office'in name or'garuda city centre'in name:k='operator_airline_offices'
  elif t.get('amenity')=='police'or'security'in name:k='security'
  elif t.get('tourism')=='hotel' or t.get('shop')or t.get('amenity')in ['cafe','restaurant','fast_food']:k='retail_hospitality'
  elif t.get('building')=='warehouse':k='warehouses_unclassified'
  elif any(x in name for x in ['utility','emergency']):k='support_operations'
  role[oid]=k
 rr=[]
 for label in sorted(set(role.get(p[i]['osm_id'],'unclassified_or_neighborhood')for i in np.flatnonzero(inside))):
  ii=np.array([i for i in np.flatnonzero(inside)if role.get(p[i]['osm_id'],'unclassified_or_neighborhood')==label],int);rr.append({'airport_role':label,'current_population':int(oldpop[ii].sum()),'proposed_population':int(a['population'][ii].sum()),'current_jobs':int(oldjobs[ii].sum()),'proposed_jobs_S0':int(a['jobs'][ii].sum()),'pilot_jobs_S1':sum(x['jobs']for i,x in enumerate(pilot)if i in set(ii)),'anchors':len(ii),'confidence':'Named/tags only; unclassified remainder retained for audit, no invented facility staffing'})
 csvout('airport_role_comparison.csv',rr)
 # Grid diagnostic is a screen for regular phase clustering, not proof of realism.
 phase=xy%500;dump('spatial_diagnostics.json',{'anchor_coordinate_phase_within10m_both_axes_of500m_centers':float(np.mean(np.all(abs(phase-250)<10,axis=1))),'phase_histogram25m':np.histogram(phase.ravel(),np.arange(0,501,25))[0].tolist(),'population_anchor_count':int(np.count_nonzero(a['population'])),'working_origin_anchor_count':int(np.count_nonzero(a['home'])),'job_anchor_count':int(np.count_nonzero(a['jobs'])),'no_grid_method':'Coordinates identical to v4 actual building/parcel interiors plus6restored hangar interiors; no jitter or grid-placement operation','note':'Point sparsity can reflect100-person rounding and aggregation; all-inhabitants layer is only audit data, not game Residents.'})
 # Comparison map uses analysis hex bins only for compact visual summaries; NOT final coordinates.
 plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
 def scatter(ax,xx,yy,weights,title,bbox=None,vmax=None):
  good=weights>0
  if bbox:good&=(xx>=bbox[0])&(xx<=bbox[2])&(yy>=bbox[1])&(yy<=bbox[3])
  v=weights[good];im=ax.scatter(xx[good],yy[good],s=np.clip(np.sqrt(v)/4,1,30),c=v,cmap='viridis',norm=LogNorm(vmin=100 if v.max()>100 else 1,vmax=max(101,v.max()) if vmax is None else vmax),alpha=.65,linewidths=0,rasterized=True);ax.set_title(title);ax.set_aspect(1.006);ax.ticklabel_format(useOffset=False,style='plain');ax.xaxis.set_major_locator(MaxNLocator(4));ax.yaxis.set_major_locator(MaxNLocator(5));return im
 fig,axs=plt.subplots(2,2,figsize=(14,14),layout='constrained')
 for ax,values,title in zip(axs.ravel(),[oldpop,a['population'],oldjobs,a['jobs']],['v4 inhabitants (audit stock)','Proposed S0 inhabitants (same totals)','v4 model workplace jobs','Proposed S0 jobs (same regional totals)']):
  im=scatter(ax,*loc.T,values,title,vmax=max(oldpop.max(),a['population'].max()) if 'inhabitants' in title else max(oldjobs.max(),a['jobs'].max()));fig.colorbar(im,ax=ax,label='People per real-feature anchor',shrink=.7);ax.set_xlim(106.3,107.35);ax.set_ylim(-6.85,-5.9)
 fig.suptitle('v4.1 Stage A — proposed only; organic coordinates, no production change');fig.savefig(OUT/'metro_before_after.png',dpi=150);plt.close(fig)
 for tag,bb in [('airport',(106.625,-6.15,106.69,-6.095)),('cikarang',(107.04,-6.42,107.23,-6.25)),('bsd',(106.59,-6.35,106.71,-6.21)),('bogor_nambo',(106.72,-6.65,106.99,-6.38))]:
  fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained');win=(loc[:,0]>=bb[0])&(loc[:,0]<=bb[2])&(loc[:,1]>=bb[1])&(loc[:,1]<=bb[3]);sharedmax=max(101,max(oldjobs[win].max(),a['jobs'][win].max(),max(x['jobs']for i,x in enumerate(pilot)if win[i])))
  for ax,jj,title in zip(axs,[oldjobs,a['jobs'],np.array([x['jobs']for x in pilot])],['v4 jobs','S0 correction, proposed','S1 intensity pilot, sensitivity only']):
   im=scatter(ax,*loc.T,jj,title,bb,sharedmax)
   for _,ts,blob in db.execute("select * from context where tags like '%aeroway%'"):
    tt=json.loads(ts)
    if tt.get('aeroway')not in ['runway','taxiway','apron']:continue
    gg=shapely.from_wkb(zlib.decompress(blob))
    if not gg.intersects(shapely.box(*bb)):continue
    for poly in gg.geoms if hasattr(gg,'geoms')else[gg]:
     if poly.geom_type=='Polygon':xx,yy=poly.exterior.xy;ax.fill(xx,yy,color='#d8dce0',alpha=.6,zorder=0)
   for f in geo['features']:
    if f['properties']['kind']not in ['industrial','airport']:continue
    g=shapely.geometry.shape(f['geometry'])
    for gg in g.geoms if hasattr(g,'geoms')else[g]:
     if gg.geom_type=='Polygon':xx,yy=gg.exterior.xy;ax.plot(xx,yy,c='#ad4d1c',lw=.5)
   ax.set_xlim(bb[0],bb[2]);ax.set_ylim(bb[1],bb[3]);fig.colorbar(im,ax=ax,label='Jobs / anchor',shrink=.6)
  fig.suptitle(tag+' — same boundaries and total regional jobs; S1 is not a staffing census');fig.savefig(OUT/('focus_'+tag+'.png'),dpi=150);plt.close(fig)
 fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained');short=['Kab Bekasi','Kab Bogor','Bekasi','Bogor','Depok','Jkt W','Jkt C','Jkt S','Jkt E','Jkt N','Tangerang','Tangsel','Kab Tangerang']
 for ax,mat,title in zip(axs,[oldod,od,od-oldod],['v4:40% cross-region','S0 + reviewed30% cross-region','Proposed minus current']):
  delta='minus'in title;mm=max(abs(od-oldod).max(),1)/1000;im=ax.imshow(mat/1000,cmap='RdBu_r'if delta else'magma',vmin=-mm if delta else 0,vmax=mm if delta else max(od.max(),oldod.max())/1000);ax.set_xticks(range(13),short,rotation=90);ax.set_yticks(range(13),short);ax.set_title(title);fig.colorbar(im,ax=ax,shrink=.7,label='Thousand worker persons')
 fig.savefig(OUT/'regional_od_comparison.png',dpi=150);plt.close(fig)
 dump('diagnostic_checks.json',{'all_district_population_margins_exact':all(r['population_current']==r['population_proposed']for r in rows),'all_district_origin_margins_exact':all(r['working_origins_current']==r['working_origins_proposed']for r in rows),'capacity_scenarios_conserve_regions':all(r['max_regional_residual']==0 for r in sens),'airport_roles_no_double_count':sum(r['current_jobs']for r in rr)==int(oldjobs[inside].sum()),'additional_clusters_reviewed':len(discovered),'all_districts_reviewed':len(rows),'current_game_checks':'../organic-stage-b/runtime_verification.json','proposal_game_test':'NOT RUN: StageA must not install','current_demand_gzip_bytes':(ROOT/'assets/JKT/demand_data.json.gz').stat().st_size,'proposed_demand_gzip_bytes':(OUT/'candidate-demand.json.gz').stat().st_size})
 print('Additional diagnostics and visualizations complete')
