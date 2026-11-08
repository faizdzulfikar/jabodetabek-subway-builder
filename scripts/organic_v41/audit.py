"""Stage A v4.1: diagnostics and a non-installed, conservative facility scenario.
Run from workspace with work/map-venv/bin/python. Does not write assets/mod/config.
"""
from pathlib import Path
import json,gzip,hashlib,csv,time,sqlite3,zlib,sys,copy
import numpy as np
import shapely
from shapely.geometry import shape,mapping,box
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41';OUT.mkdir(exist_ok=True)
SCR=Path('work/organic-v41');SCR.mkdir(exist_ok=True)
CATS=['unknown','residential','apartments','office','government','factory','warehouse','retail','market','university','school','hospital','hotel','mixed','excluded','exhibition','community','transport']
P=Transformer.from_crs(4326,32748,always_xy=True).transform

def readgz(p):return json.load(gzip.open(p,'rt'))
def write(n,d): (OUT/n).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def gz(n,d):
 with gzip.GzipFile(filename=str(OUT/n),mode='wb',mtime=0)as f:f.write(json.dumps(d,separators=(',',':')).encode())
def csvout(n,rows):
 with (OUT/n).open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def apportion(w,total):
 q=np.asarray(w,float)/sum(w)*int(total);v=np.floor(q).astype(np.int64);v[np.argsort(-(q-v),kind='stable')[:int(total-v.sum())]]+=1;return v

def main():
 start=time.monotonic();protected=[p for folder in ['assets','mod']for p in (ROOT/folder).rglob('*')if p.is_file()]+[ROOT/'config.json',ROOT/'BUILD_STATUS.json']
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in protected};write('production_baseline_hashes.json',hashes)
 required=['DATA_GUIDE.md','BUILD_STATUS.json','assets/JKT/demand-method.json','sources/government/COVERAGE.md','sources/government/population_controls.json','sources/government/kelurahan_estimates.csv','sources/government/workplace_proxies.json','sources/government/source_manifest.json','sources/government/quality_issues.json','docs/organic-stage-b/organic_parameters.json','docs/organic-stage-b/employment_capacity_regularization.json','docs/organic-stage-b/validation.json']
 write('input_manifest.json',{n:{'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),'bytes':(ROOT/n).stat().st_size}for n in required})
 # Read every required source; record schemas, no v3-generation routine is executed.
 inputs={n:json.loads((ROOT/n).read_text()) for n in required if n.endswith('.json')}
 inp=readgz(ROOT/'assets/JKT/government_inputs.json.gz');vs=inp['villages'];names=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz')['names'].tolist()
 a=np.load(ROOT/'docs/organic-stage-b/proposed_arrays.npz');ar={k:a[k].copy()for k in a.files};alloc=readgz(ROOT/'docs/organic-stage-b/proposed_allocations.json.gz');points=alloc['points'];n=len(points);loc=ar['locations'];reg=ar['regions'];village=ar['villages'];home=ar['home'];old=ar['jobs'];pop=ar['population']
 db=sqlite3.connect('work/organic-audit/inventory.sqlite');ctx=[]
 for id,t,b in db.execute('select * from context'):
  t=json.loads(t);g=shapely.make_valid(shapely.from_wkb(zlib.decompress(b)))
  if not g.is_empty:ctx.append((id,t,g))
 airport=next(g for id,t,g in ctx if id=='r19104217')
 masks=shapely.union_all([g for id,t,g in ctx if t.get('aeroway')in ['runway','taxiway','apron'] or t.get('natural')in ['water','bay','strait','wetland','wood']or t.get('landuse')in ['forest','reservoir']]+[shapely.from_wkb(Path('work/organic-audit/packaged_water.wkb').read_bytes())])
 # Anchor-class capacity is an aggregate, not staffing. Modify only contained facility tags.
 mix=ar['capacity_mix'].copy();cap=np.array([p['relative_employment_capacity']for p in points]);rc=np.array([p['relative_residential_capacity']for p in points]);newcap=cap.copy()
 candidates=np.load('work/organic-stage-b/building_candidates.npz');c={k:candidates[k]for k in candidates.files};members=np.load('work/organic-stage-b/cluster_members.npz');cm={int(i):int(j)for i,j in zip(members['rowid'],members['cluster'])if i>0 and j>=0};lookup={int(i):q for q,i in enumerate(c['rowid'])}
 facilities=[];corrections=[];new=[];airport_rows=[]
 for rowid,id,lon,lat,area,ts,blob in db.execute("select rowid,* from buildings where json_extract(tags,'$.aeroway') in ('terminal','hangar') or json_extract(tags,'$.building') in ('hangar','industrial','factory','warehouse') or json_extract(tags,'$.industrial') is not null"):
  t=json.loads(ts);inairport=airport.covers(shapely.Point(lon,lat));q=lookup.get(rowid);anchor=cm.get(rowid);kind=None;prior=None
  if inairport and(t.get('aeroway')=='hangar' or t.get('building')=='hangar'):kind='airport_maintenance';prior=100
  elif inairport and t.get('aeroway')=='terminal':kind='airport_terminal';prior=80
  elif t.get('building')in ['industrial','factory']or t.get('industrial')=='factory':kind='factory';prior=50
  elif t.get('building')=='warehouse':kind='warehouse';prior=180
  if kind is None:continue
  if q is None:continue
  fl=float(c['area'][q]*c['levels'][q]*.8);before=fl/150 if kind=='airport_terminal' else float(c['jobcap'][q]);after=fl/prior
  if kind=='airport_maintenance' and anchor is None:
   g=shapely.make_valid(shapely.from_wkb(zlib.decompress(blob)));pt=g.representative_point()
   if masks.covers(pt):continue
   # Newly restored hangar uses a genuine building interior, never apron centroid.
   vi=int(c['village'][q]);ri=names.index(vs[vi]['region']);anchor=n+len(new)
   new.append({'id':f'audit_{anchor}','location':[pt.x,pt.y],'osm_id':id,'source_anchor_id':id,'anchor_kind':'building','source_year':2026,'admin_id':vs[vi]['id'],'population':0,'model_residents':0,'jobs':0,'relative_residential_capacity':0,'relative_employment_capacity':after,'anchor_function':'transport','dominant_job_capacity_function':'transport','anchor_morphology_inferred':'none','anchor_levels_observed':bool(c['explicit_levels'][q]),'function_observed':True,'road_distance_m':float(c['road_m'][q]),'village':vi,'region':ri})
  elif anchor is not None:
   newcap[anchor]+=after-before
  else:continue
  item={'osm_id':id,'anchor':int(anchor),'name':t.get('name',''),'function':kind,'usable_floor_m2_inferred':round(fl,2),'levels_observed':bool(c['explicit_levels'][q]),'old_relative_capacity':round(before,3)if anchor<n else 0,'proposed_relative_capacity':round(after,3),'area_per_worker_scenario':prior,'confidence':'Observed footprint/function; inferred usable floor and staffing intensity'}
  facilities.append(item)
  if inairport:airport_rows.append(item)
 if new:
  newloc=np.array([p['location']for p in new]);ar['locations']=np.vstack([loc,newloc]);ar['xy']=np.vstack([ar['xy'],np.array(P(*newloc.T)).T]);ar['villages']=np.r_[village,[p['village']for p in new]];ar['regions']=np.r_[reg,[p['region']for p in new]];ar['category']=np.r_[ar['category'],np.full(len(new),17)]
  for k in ['home','population']:ar[k]=np.r_[ar[k],np.zeros(len(new),np.int64)]
  newcap=np.r_[newcap,[p['relative_employment_capacity']for p in new]];rc=np.r_[rc,np.zeros(len(new))];mix=np.vstack([mix,np.zeros((len(new),18))]);mix[n:,17]=newcap[n:];points=points+new
 # Reject residential anchors that are positively identified as tanks/parking or
 # named airport operational facilities. Unknown airport buildings are NOT blanket excluded.
 anchor_by_osm={p['osm_id']:i for i,p in enumerate(points)if p['osm_id']};res_corrections=[]
 for oid,ts in db.execute("select id,tags from buildings where tags like '%gasometer%' or tags like '%parking%' or tags like '%Office%' or tags like '%Utility Building%' or tags like '%Ground Support Equipment%' or tags like '%Emergency Hall%' or tags like '%Garuda City Centre%'"):
  i=anchor_by_osm.get(oid)
  if i is None:continue
  t=json.loads(ts);inairport=airport.covers(shapely.Point(points[i]['location']));name=t.get('name','').lower();kind=None
  if t.get('building')in ['gasometer','storage_tank']or t.get('man_made')in ['gasometer','storage_tank']:kind='storage_vessel';newcap[i]=0
  elif t.get('building')=='parking' or t.get('parking')=='multi-storey':kind='parking_structure';newcap[i]=min(newcap[i],10)
  elif inairport and any(w in name for w in ['office','utility building','ground support equipment','emergency hall','garuda city centre']):kind='named_airport_operations'
  if kind is None:continue
  if ar['population'][i]>0 or ar['home'][i]>0:res_corrections.append({'anchor':i,'osm_id':oid,'reason':kind,'population_removed_from_anchor':int(ar['population'][i]),'working_origins_removed_from_anchor':int(ar['home'][i]),'admin_id':points[i]['admin_id'],'evidence':'Observed tag'if kind!='named_airport_operations'else'Inferred function from named operational building inside aerodrome'})
  rc[i]=0
 # Re-apportion only affected villages over existing residential anchors; no new settlement.
 affected={int(ar['villages'][x['anchor']])for x in res_corrections}
 for v in affected:
  ids=np.flatnonzero(ar['villages']==v);valid=ids[rc[ids]>0];assert len(valid)
  pt=int(ar['population'][ids].sum());ht=int(ar['home'][ids].sum());ar['population'][ids]=0;ar['home'][ids]=0
  ar['population'][valid]=apportion(rc[valid],pt);ar['home'][valid]=apportion(rc[valid],ht//100)*100
 for i,p in enumerate(points):p.update(population=int(ar['population'][i]),model_residents=int(ar['home'][i]),relative_residential_capacity=round(float(rc[i]),3))
 csvout('residential_anchor_corrections.csv',res_corrections)
 newcap=np.maximum(newcap,0);reg=ar['regions'];loc=ar['locations'];pop=ar['population'];home=ar['home'];old=np.r_[old,np.zeros(len(new),np.int64)];jobs=np.zeros(len(points),np.int64);floorpart=np.zeros(len(points));respart=np.zeros(len(points));regions=[]
 for r,name in enumerate(names):
  ids=np.flatnonzero(reg==r);total=int(old[ids].sum());floor=np.minimum(.8*total*newcap[ids]/newcap[ids].sum(),2*newcap[ids]);residual=total-floor.sum();neigh=residual*rc[ids]/rc[ids].sum();jobs[ids]=apportion(floor+neigh,total//100)*100;floorpart[ids]=floor;respart[ids]=neigh
  v4=next(x for x in inputs['docs/organic-stage-b/employment_capacity_regularization.json']['regions']if x['region']==name)
  orig=int(home[ids].sum());persons=int(pop[ids].sum());regions.append({'region':name,'population_current':persons,'population_proposed':persons,'working_origins_current':orig,'working_origins_proposed':orig,'jobs_current':total,'jobs_proposed':int(jobs[ids].sum()),'v4_floor_prior_jobs':round(total*(1-v4['unclassified_neighborhood_component_share'])),'v4_neighborhood_prior_jobs':round(total*v4['unclassified_neighborhood_component_share']),'proposed_floor_prior_jobs':round(float(floor.sum())),'proposed_neighborhood_prior_jobs':round(float(residual)),'v4_fallback_share':v4['unclassified_neighborhood_component_share'],'proposed_fallback_share':float(residual/total),'reallocated_jobs_half_l1':int(abs(jobs[ids]-old[ids]).sum()//2),'working_to_population_ratio':orig/persons})
 # S1 intensity pilot is deliberately separate from the recommended S0 corrections.
 pilotjobs=jobs.copy();pilotcap=newcap.copy();pilotregions=copy.deepcopy(regions)
 original=readgz(ROOT/'docs/organic-stage-b/proposed_allocations.json.gz')['points']
 corecap=np.r_[[p['relative_employment_capacity']for p in original],[p['relative_employment_capacity']*100/150 for p in new]]
 for x in res_corrections:
  i=x['anchor']
  if x['reason']=='storage_vessel':corecap[i]=0
  elif x['reason']=='parking_structure':corecap[i]=min(corecap[i],10)
 newcap=corecap;regions=[]
 for r,name in enumerate(names):
  ids=np.flatnonzero(reg==r);total=int(old[ids].sum());floor=np.minimum(.8*total*newcap[ids]/newcap[ids].sum(),2*newcap[ids]);residual=total-floor.sum();neigh=residual*rc[ids]/rc[ids].sum();jobs[ids]=apportion(floor+neigh,total//100)*100;floorpart[ids]=floor;respart[ids]=neigh
  rr=pilotregions[r].copy();rr.update(proposed_floor_prior_jobs=round(float(floor.sum())),proposed_neighborhood_prior_jobs=round(float(residual)),proposed_fallback_share=float(residual/total),reallocated_jobs_half_l1=int(abs(jobs[ids]-old[ids]).sum()//2),pilot_reallocated_jobs_half_l1=pilotregions[r]['reallocated_jobs_half_l1'],pilot_fallback_share=pilotregions[r]['proposed_fallback_share']);regions.append(rr)
 mix*=np.divide(newcap,mix.sum(1),out=np.zeros(len(newcap)),where=mix.sum(1)>0)[:,None];pilotmix=mix.copy();pilotmix*=np.divide(pilotcap,pilotmix.sum(1),out=np.zeros(len(pilotcap)),where=pilotmix.sum(1)>0)[:,None]
 ar['jobs']=jobs;ar['capacity_mix']=mix
 for i,p in enumerate(points):p.update(jobs=int(jobs[i]),relative_employment_capacity=round(float(newcap[i]),3))
 proposed=copy.deepcopy(alloc);proposed.update(stage='A_V41_PROPOSAL_NOT_INSTALLED',points=points,proposal='S0 recommended correction: exclude identified tanks/parking/airport operations from residence; restore CGK hangars at existing150m2 transport prior. Preserve other v4 priors and region totals.')
 gz('proposed_allocations.json.gz',proposed);np.savez_compressed(OUT/'proposed_arrays.npz',**ar);pilot=copy.deepcopy(proposed);pilot['proposal']='S1 sensitivity only: explicit factory50, warehouse180, CGK terminal80/hangar100 m2 per modelworker';
 for i,p in enumerate(pilot['points']):p.update(jobs=int(pilotjobs[i]),relative_employment_capacity=round(float(pilotcap[i]),3))
 gz('pilot_allocations.json.gz',pilot);np.savez_compressed(OUT/'pilot_arrays.npz',**{**ar,'jobs':pilotjobs,'capacity_mix':pilotmix});csvout('regional_comparison.csv',regions);csvout('facility_capacity_changes.csv',facilities);csvout('airport_facility_capacity.csv',airport_rows)
 # Geographic footprints: official admin geometry for suburbs; OSM named parcels for estates.
 boundary=readgz(ROOT/'sources/government/village_boundaries.geojson.gz');bounds={f['properties']['code']:shapely.make_valid(shape(f['geometry']))for f in boundary['features']};vmap={v['id']:i for i,v in enumerate(vs)}
 areas=[]
 def add(name,g,kind,source,confidence,scope=''):areas.append({'name':name,'geometry':g,'kind':kind,'boundary_source':source,'confidence':confidence,'scope':scope})
 districts={'Kota Tangerang Selatan':['Serpong','Serpong Utara'],'Tangerang':['Cisauk','Pagedangan','Kelapa Dua','Cikupa','Balaraja'],'Bekasi':['Tambun Selatan','Tambun Utara','Cibitung','Cikarang Barat','Cikarang Utara','Cikarang Selatan','Cikarang Pusat'],'Bogor':['Klapanunggal','Gunung Putri','Citeureup','Cileungsi','Cibinong','Bojonggede','Tajurhalang','Parung','Kemang','Dramaga','Babakan Madang','Sukaraja']}
 norm=lambda s:''.join(x for x in s.casefold()if x.isalnum())
 for region,kecs in districts.items():
  for kec in kecs:
   ids=[v['id']for v in vs if v['region']==region and norm(v['kecamatan'])==norm(kec)];assert ids,(region,kec)
   add(kec+' · '+region,shapely.union_all([bounds[x]for x in ids]),'residential_admin','BIG June2026 village union','Observed boundary; inferred sub-village allocation','Administrative envelope, NOT estate/township legal boundary')
 for region in ['Kota Bekasi','Kota Bogor']:
  ids=[v['id']for v in vs if v['region']==region];add(region,shapely.union_all([bounds[x]for x in ids]),'residential_admin','BIG June2026 village union','Observed boundary; inferred sub-village allocation','City envelope')
 for word in ['Rawa Buntu','Nambo']:
  ids=[v['id']for v in vs if norm(v['kelurahan'])==norm(word)]
  if ids:add(word,shapely.union_all([bounds[x]for x in ids]),'residential_admin','BIG village boundary','Observed boundary; allocated population may be derived','Village, not station walking catchment')
 # Named residential complexes wherever mapped; explicit administrative proxy if absent.
 for title,word,bb in [('BSD City','bsd',(106.60,-6.35,106.70,-6.25)),('Gading Serpong','gading serpong',(106.59,-6.30,106.65,-6.20)),('Alam Sutera','alam sutera',(106.64,-6.27,106.68,-6.21)),('Sentul','sentul',(106.83,-6.64,106.92,-6.51))]:
  polys=[g for id,t,g in ctx if word in t.get('name','').lower()and t.get('landuse')=='residential'and g.intersects(box(*bb))]
  if polys:add(title+' mapped housing parcels',shapely.union_all(polys),'residential_named','Named OSM residential parcels','Observed mapped subset; incomplete township coverage','Subset only; surrounding administrative envelopes reported separately')
  else:
   gs=[bounds[v['id']]for v in vs if shape(bounds[v['id']]).representative_point().within(box(*bb))];add(title+' administrative envelope',shapely.union_all(gs),'residential_named','BIG villages selected by published audit window','Inferred envelope; NOT actual township boundary','No complete mapped township polygon; do not compare to township totals')
 estate_specs=[('Jababeka',lambda t:'kawasan industri jababeka'in t.get('name','').lower()),('MM2100',lambda t:t.get('name')=='MM2100 Industrial Town'),('EJIP',lambda t:t.get('name')=='East Jakarta Industrial Park'),('Lippo Cikarang industrial parcels',lambda t:'delta silicon'in t.get('name','').lower()),('GIIC / Kota Deltamas industrial',lambda t:t.get('name')=='Greenland International Industrial Center'),('Marunda',lambda t:'marunda'in t.get('name','').lower()),('Pulogadung',lambda t:'industrial estate pulogadung'in t.get('name','').lower()),('Cikupa Mas',lambda t:t.get('name')=='Cikupa Mas'),('Balaraja named industrial parcels',lambda t:'balaraja'in t.get('name','').lower())]
 for title,pred in estate_specs:
  ps=[g for id,t,g in ctx if t.get('landuse')=='industrial'and pred(t)];assert ps,title;add(title,shapely.union_all(ps),'industrial','OSM named industrial polygons','Observed mapped footprint; occupancy/facility function inferred','Mapped industrial extent, not all developed/occupied land or township employment denominator')
 for title,region,kecs in [('Cibitung industrial clusters','Bekasi',['Cibitung']),('Cakung industrial clusters','Kota Jakarta Timur',['Cakung']),('Jatiuwung industrial clusters','Kota Tangerang',['Jatiuwung'])]:
  env=shapely.union_all([bounds[v['id']]for v in vs if v['region']==region and norm(v['kecamatan'])in [norm(x)for x in kecs]])
  ps=[g.intersection(env)for id,t,g in ctx if t.get('landuse')=='industrial'and g.intersects(env)];add(title,shapely.union_all(ps),'industrial','OSM industrial polygons clipped to BIG kecamatan','Inferred industrial subset; not operator boundary','May overlap other estates; never sum overlapping areas')
 add('Soekarno–Hatta airport',airport,'airport','OSM r19104217','Observed mapped aerodrome footprint','Whole aerodrome excludes offsite ecosystem; no shift headcount interpretation')
 # Existing StageA priority windows now clipped to actual activity parcels/footprints.
 centers=json.loads((ROOT/'docs/organic-stage-a/employment_centers.json').read_text())
 activity=[g for id,t,g in ctx if t.get('landuse')in ['commercial','retail','industrial']]
 for center in centers:
  bb=box(*center['bbox']);gs=[g.intersection(bb)for g in activity if g.intersects(bb)];g=shapely.union_all(gs)
  add(center['name'],g,'employment_core','OSM activity parcels clipped to archived audit window','Inferred activity footprint; corridor boundary not legal','Core subset; excludes unmapped/mixed residential workplace corridors; windows overlap')
 # All current/proposed counts use identical defined geographic masks.
 oldloc=loc[:n];oldpoints=shapely.points(oldloc);allpoints=shapely.points(loc)
 rows=[];masks_by_name={};allfeatures=[];industrial_union=shapely.union_all([g for id,t,g in ctx if t.get('landuse')=='industrial'])
 cloc=np.column_stack([c['lon'],c['lat']]);ccat=c['category'];road=c['road_m']
 for area in areas:
  g=area['geometry'];inside=shapely.intersects_xy(g,loc[:,0],loc[:,1]);masks_by_name[area['name']]=inside;ci=shapely.intersects_xy(g,c['lon'],c['lat']);area_m2=shapely.transform(g,P,interleaved=False).area
  industrial=g.intersection(industrial_union);mapped_ind_m2=shapely.transform(industrial,P,interleaved=False).area
  # Developed land proxy = mapped industrial parcel minus explicitly mapped natural/airside masks;
  # not verified occupied hectares. Retain roof footprint as an independent denominator.
  develop=industrial.difference(masks);devha=shapely.transform(develop,P,interleaved=False).area/10000
  barea=float(c['area'][ci].sum());known=ci&c['explicit_function'];residential=ci&np.isin(ccat,[0,1,2,13]);inres=float(np.sum(rc[inside]));population=int(pop[inside].sum());oldpopulation=int(a['population'][inside[:n]].sum());nj=int(jobs[inside].sum());oj=int(old[inside].sum());vi=np.unique(ar['villages'][inside]);controls=[vs[int(v)]for v in vi]
  row={'name':area['name'],'kind':area['kind'],'boundary_source':area['boundary_source'],'scope':area['scope'],'confidence':area['confidence'],'area_ha':round(area_m2/10000,2),'mapped_industrial_ha':round(mapped_ind_m2/10000,2),'developed_industrial_proxy_ha':round(devha,2),'population_current':oldpopulation,'population_proposed':population,'working_origins_current':int(a['home'][inside[:n]].sum()),'working_origins_proposed':int(home[inside].sum()),'jobs_current':oj,'jobs_proposed':nj,'jobs_pilot_s1':int(pilotjobs[inside].sum()),'jobs_delta':nj-oj,'jobs_per_area_ha_current':round(oj/(area_m2/10000),2)if area_m2 else 0,'jobs_per_area_ha_proposed':round(nj/(area_m2/10000),2)if area_m2 else 0,'industrial_jobs_per_developed_ha_current':round(oj/devha,2)if devha else 0,'industrial_jobs_per_developed_ha_proposed':round(nj/devha,2)if devha else 0,'eligible_mapped_buildings':int(ci.sum()),'eligible_roof_ha':round(barea/10000,2),'explicit_function_building_fraction':float(known.sum()/max(1,ci.sum())),'observed_levels_building_fraction':float(c['explicit_levels'][ci].mean())if ci.any()else 0,'residential_eligible_buildings':int(residential.sum()),'apartment_buildings':int(np.sum(ci&(ccat==2))),'mapped_factory_buildings':int(np.sum(ci&(ccat==5))),'mapped_warehouse_buildings':int(np.sum(ci&(ccat==6))),'allocation_anchors_current':int(inside[:n].sum()),'allocation_anchors_proposed':int(inside.sum()),'population_on_parcel_fallback':sum(int(pop[i])for i in np.flatnonzero(inside)if points[i]['anchor_kind']=='builtup_parcel'),'population_to_relative_capacity':round(population/max(inres,1),3),'covered_villages':len(vi)}
  rows.append(row);allfeatures.append({'type':'Feature','properties':{k:v for k,v in area.items()if k!='geometry'},'geometry':mapping(g)})
 csvout('area_comparison.csv',rows);gz('audit_boundaries.geojson.gz',{'type':'FeatureCollection','features':allfeatures});np.savez_compressed(OUT/'area_masks.npz',**{str(i):m for i,m in enumerate(masks_by_name.values())});write('area_order.json',list(masks_by_name))
 # Exact administrative audit; official controls vs allocated sums, no density multipliers.
 vrows=[]
 for v,meta in enumerate(vs):
  ids=ar['villages']==v;vrows.append({'admin_id':meta['id'],'region':meta['region'],'kecamatan':meta['kecamatan'],'kelurahan':meta['kelurahan'],'population_status':meta['population_status'],'source_year':meta['year'],'population_current':int(a['population'][ids[:n]].sum()),'population_proposed':int(pop[ids].sum()),'working_origins_current':int(a['home'][ids[:n]].sum()),'working_origins_proposed':int(home[ids].sum()),'jobs_current':int(old[ids].sum()),'jobs_proposed':int(jobs[ids].sum()),'jobs_pilot_s1':int(pilotjobs[ids].sum()),'anchors_current':int(ids[:n].sum()),'anchors_proposed':int(ids.sum()),'population_on_parcel_fallback':sum(int(pop[i])for i in np.flatnonzero(ids)if points[i]['anchor_kind']=='builtup_parcel')})
 csvout('village_comparison.csv',vrows)
 # Capacity components by observed anchor flags is a diagnostic only: explicit_function flag
 # records non-generic building tag, not validated true functional observation.
 attribution=[]
 for r,name in enumerate(names):
  ids=np.flatnonzero(reg==r)
  for label,cond in [('explicit_tag',lambda p:p['function_observed']),('inferred_function',lambda p:not p['function_observed'])]:
   ix=np.array([i for i in ids if cond(points[i])],int);attribution.append({'region':name,'anchor_function_flag':label,'current_jobs':int(old[ix].sum()),'proposed_jobs':int(jobs[ix].sum()),'proposed_floor_prior_jobs':round(float(floorpart[ix].sum())),'proposed_neighborhood_prior_jobs':round(float(respart[ix].sum())),'warning':'Flag != workplace staffing observation; all job values are model estimates'})
 csvout('employment_evidence_components.csv',attribution)
 # All proposed points retain baseline anchors or newly restored valid hangar interiors.
 added_mask=shapely.intersects_xy(masks,loc[n:,0],loc[n:,1]);checks={'stage':'A_V41_PROPOSAL_ONLY','production_demand_sha256':hashes['assets/JKT/demand_data.json.gz'],'production_commit':'dfec7f2c0614daa2d1735c5d976993afba4e589d','population':int(pop.sum()),'working_origins':int(home.sum()),'jobs':int(jobs.sum()),'population_village_margins_unchanged':all(x['population_current']==x['population_proposed']for x in vrows),'working_origin_village_margins_unchanged':all(x['working_origins_current']==x['working_origins_proposed']for x in vrows),'regional_job_margins_unchanged':all(x['jobs_current']==x['jobs_proposed']for x in regions),'allocation_anchors_current':n,'allocation_anchors_proposed':len(points),'restored_airport_hangar_anchors':len(new),'new_anchor_mapped_mask_hits':int(added_mask.sum()),'coordinates_baseline_unchanged':bool(np.array_equal(loc[:n],a['locations'])),'jobs_moved_half_l1':int(abs(jobs-old).sum()//2),'population_moved_half_l1':int(abs(pop[:n]-a['population']).sum()//2),'working_origins_moved_half_l1':int(abs(home[:n]-a['home']).sum()//2),'S1_tagged_facility_capacity_changes':len(facilities),'stage_a_seconds':time.monotonic()-start,'production_files_unchanged':all(hashlib.sha256((ROOT/nm).read_bytes()).hexdigest()==h for nm,h in hashes.items()),'official_controls_baseline_count':446,'official_controls_policy':'All baseline village population and working origins retained exactly; therefore baseline446 controls remain exact; separate independent control check follows','not_game_verified':True,'scenario_interpretation':'S0 classified-anchor correction and six restored CGK hangars, existing intensities retained. S1 is a separate intensity sensitivity pilot. No regional job total or population change.'}
 assert checks['production_files_unchanged']and checks['new_anchor_mapped_mask_hits']==0 and checks['population']==32615007 and checks['jobs']==12646700
 write('audit_checks.json',checks);write('scenario_parameters.json',{'stage': 'A_NOT_INSTALLED', 'recommended_S0': {'name': 'classification_and_hangar_correction', 'residential_corrections': '28 positive nonresidential tags +5inferred airport operational names; preserve village totals', 'employment_intensities': 'All v4 priors unchanged; six restored CGK hangars use transport150m2/relative-worker', 'floor_ceiling_multiplier': 2, 'minimum_neighborhood_share': 0.2, 'regional_jobs': 'unchanged', 'population_and_working_origins_by_village': 'unchanged'}, 'sensitivity_S1': {'name': 'function_specific_capacity_pilot', 'factory_m2_per_relative_worker': 50, 'warehouse_m2_per_relative_worker': 180, 'CGK_terminal_m2_per_relative_worker': 80, 'CGK_hangar_m2_per_relative_worker': 100, 'eligibility': 'positively tagged facilities only, no blanket inferred-industrial multiplier', 'status': 'Sensitivity only; coefficients not measured staffing or recommended release defaults'}, 'OD': {'review_cross_region_fraction': 0.3, 'baseline_control_fraction': 0.4, 'regional_sensitivity_fractions': [0.3, 0.35, 0.4], 'decay_km': 18, 'decay_sensitivity_km': [12, 18, 30], 'within_region_noise_km': 6, 'status': 'Gameplay choices pending explicit user selection; no fitted2025 claim'}, 'confidence': 'Observed geometry/tags; inferred floor/capacity; gameplay OD and ceiling', 'population_total': 32615007, 'working_tripmakers_total': 12646700})
 print(json.dumps(checks,indent=2),flush=True)
if __name__=='__main__':main()
