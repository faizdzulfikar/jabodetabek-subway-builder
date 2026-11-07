"""Stage B adaptive building/parcel allocation (staging output). No engine demand file emitted.
Run from workspace: work/map-venv/bin/python .../propose.py work/organic-audit/inventory.sqlite
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
OUT=ROOT/'docs/organic-stage-b'
def dump(name,x):(OUT/name).write_text(json.dumps(x,indent=2)+'\n')
import sqlite3,zlib,sys,shapely,hashlib,resource
from scipy.spatial import cKDTree
from collections import Counter
START=time.monotonic();SCR=Path('work/organic-stage-b');DB=sqlite3.connect(sys.argv[1]);PROJ=Transformer.from_crs(4326,32748,always_xy=True).transform
CATS=['unknown','residential','apartments','office','government','factory','warehouse','retail','market','university','school','hospital','hotel','mixed','excluded','exhibition','community','transport']
# Capacity coefficients are scenario assumptions, not measured workers or residents.
SQM_JOB=np.array([300,350,200,20,25,75,140,35,45,50,70,45,100,40,1e12,140,100,150])
LEVELS=np.array([1.5,1.5,6,3,2,1,1,2,1,3,2,4,4,2,1,1,1,2])
def category(t):
 b=t.get('building','');a=t.get('amenity','');l=t.get('landuse','')
 if b in ['roof','construction','ruins','greenhouse','garages','garage','carport','shed','service','barn','farm_auxiliary'] or a in ['parking','parking_space']:return 14
 if a in ['hospital','clinic','doctors'] or b=='hospital':return 11
 if a in ['university','college']:return 9
 if a in ['school','kindergarten'] or b=='school':return 10
 if a=='marketplace':return 8
 if t.get('tourism') in ['hotel','motel','hostel'] or b=='hotel':return 12
 if t.get('office')=='government' or a in ['townhall','courthouse','police','fire_station']:return 4
 if a in ['conference_centre','exhibition_centre']:return 15
 if b in ['warehouse','storage_tank'] or l in ['garages','railway']:return 6
 if b in ['industrial','factory'] or l=='industrial':return 5
 if t.get('shop') or b in ['retail','supermarket','kiosk'] or l=='retail':return 7
 if t.get('office') or b=='office':return 3
 if b=='commercial':return 13
 if b=='apartments':return 2
 if b in ['house','residential','detached','terrace','bungalow','semidetached_house','dormitory'] or l=='residential':return 1
 if l=='commercial':return 13
 return 0

def apportion(w,total):
 w=np.asarray(w,float)
 if not len(w):assert total==0;return np.zeros(0,dtype=np.int64)
 assert w.sum()>0
 q=w/w.sum()*int(total);n=np.floor(q).astype(np.int64);r=int(total)-int(n.sum())
 if r:n[np.argsort(-(q-n),kind='stable')[:r]]+=1
 return n

def inside(tree,points):
 out=np.zeros(len(points),bool)
 if tree is not None:
  pairs=tree.query(points,predicate='within')
  if pairs.size:out[pairs[0]]=True
 return out

def savegz(p,x):
 with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(x,separators=(',',':')).encode())

if __name__=='__main__':
 base=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz');inp=readgz(ROOT/'assets/JKT/government_inputs.json.gz');vs=inp['villages'];names=base['names'].tolist();vreg=np.array([names.index(v['region']) for v in vs]);bound=readgz(ROOT/'sources/government/village_boundaries.geojson.gz');vmap={v['id']:i for i,v in enumerate(vs)};vpol=[];vi=[]
 for f in bound['features']:
  if f['properties']['code'] in vmap:vpol.append(shapely.make_valid(shapely.geometry.shape(f['geometry'])));vi.append(vmap[f['properties']['code']])
 vt=shapely.STRtree(vpol);vi=np.array(vi)
 if '--reuse' not in sys.argv:
  # Full mapped context: footprint geometry, no arbitrary center-based boosts.
  ctx=[];cc=[];masks={k:[] for k in ['water','airside','forest']};context_counts=Counter();parts=0
  for oid,ts,blob in DB.execute('SELECT * FROM context'):
   t=json.loads(ts);g=shapely.make_valid(shapely.from_wkb(zlib.decompress(blob)))
   if g.is_empty:continue
   if 'building:part'in t:parts+=1;continue
   c=category(t)
   if c in [1,3,4,5,6,7,8,9,10,11,12,13,15]:ctx.append(g);cc.append(c);context_counts[CATS[c]]+=1
   if t.get('natural') in ['water','bay','strait'] or t.get('waterway')=='riverbank' or t.get('landuse')=='reservoir':masks['water'].append(g)
   if t.get('aeroway') in ['runway','taxiway','apron']:masks['airside'].append(g)
   if t.get('natural') in ['wood','wetland'] or t.get('landuse')=='forest' or t.get('leisure')=='nature_reserve':masks['forest'].append(g)
  ct=shapely.STRtree(ctx);cc=np.array(cc);masktrees={k:shapely.STRtree(g) if g else None for k,g in masks.items()}
  # Existing runway/taxiway polygons strengthen line features missing from area extract.
  air=readgz(ROOT/'assets/JKT/runways_taxiways.geojson.gz')
  masks['airside'] += [shapely.geometry.shape(f['geometry']) for f in air['features'] if f['geometry']['type'] in ['Polygon','MultiPolygon']]
  masktrees['airside']=shapely.STRtree(masks['airside'])
  roads=readgz(ROOT/'assets/JKT/roads.geojson.gz');roadgs=[];maj=[]
  for f in roads['features']:
   g=shapely.transform(shapely.geometry.shape(f['geometry']),PROJ,interleaved=False);roadgs.append(g)
   if f['properties'].get('roadClass') in ['major','highway'] and f['properties'].get('structure')=='normal':maj.append(g)
  del roads
  rt=shapely.STRtree(roadgs);mt=shapely.STRtree(maj)
  bpoints=shapely.points(base['locations']);bpt=shapely.STRtree(bpoints);baseline_contained=np.zeros(len(bpoints),bool);baseline_mask={k:inside(t,bpoints) for k,t in masktrees.items()};bp_projected=shapely.points(base['xy']);_,bd=mt.query_nearest(bp_projected,return_distance=True,all_matches=False);baseline_mask['major_road_8m_proxy']=bd<8
  cols={k:[] for k in ['rowid','lon','lat','area','village','category','levels','explicit_levels','explicit_function','road_m','rescap','jobcap']};excluded=Counter();tags_count=Counter();total=0
  cur=DB.execute('SELECT rowid,lon,lat,area,tags,geometry FROM buildings')
  while rows:=cur.fetchmany(10000):
   gs=shapely.from_wkb([zlib.decompress(r[5]) for r in rows]);ps=shapely.points([[r[1],r[2]] for r in rows]);pg=shapely.transform(ps,PROJ,interleaved=False);pairs=bpt.query(gs,predicate='covers')
   if pairs.size:baseline_contained[pairs[1]]=True
   vp=vt.query(ps,predicate='within');vill=np.full(len(rows),-1,dtype=np.int32)
   if vp.size:
    order=np.lexsort((vi[vp[1]],vp[0]));vill[vp[0,order]]=vi[vp[1,order]]
   ts=[json.loads(r[4]) for r in rows];cat=np.array([category(t) for t in ts]);explicit=(cat!=0)&(cat!=1) # explicit residential measured separately below
   explicit=np.array([any(k in t for k in ['office','shop','amenity','tourism']) or t.get('building') not in [None,'yes'] for t in ts])
   cp=ct.query(ps,predicate='within')
   # choose smallest enclosing functional polygon; explicit footprint tags always win.
   if cp.size:
    carea=shapely.area(np.array(ctx,dtype=object)[cp[1]]);order=np.lexsort((carea,cp[0]));seen=set()
    for q in order:
     p,j=cp[:,q]
     if p not in seen and not explicit[p]:cat[p]=cc[j];seen.add(p)
   lev=[];known=[]
   for i,t in enumerate(ts):
    try:l=float(t.get('building:levels','').split(';')[0]);ok=True
    except ValueError:
     try:l=float(t.get('height','').replace(' m',''))/3.3;ok=True
     except ValueError:l=LEVELS[cat[i]];ok=False
    lev.append(float(np.clip(l,1,100)));known.append(ok)
   lev=np.array(lev);area=np.array([r[3] for r in rows]);floor=area*lev*.8
   # Tall mall envelopes are mixed-use inference; retail podium height is not entire tower.
   tallmall=(cat==7)&(lev>8);cat[tallmall]=13
   res_share=np.where(np.isin(cat,[0,1,2]),.95,np.where(cat==13,.6,0));rescap=floor*res_share/np.where(cat==2,32,22)
   job_share=np.where(np.isin(cat,[0,1,2]),.05,np.where(cat==13,.4,1));jobcap=floor*job_share/SQM_JOB[cat]
   # Institutions and commercial buildings may contain caretakers but no assumed residential stock.
   invalid=np.zeros(len(rows),bool)
   for k,t in masktrees.items():
    hit=inside(t,ps);invalid|=hit;excluded[k]+=int(hit.sum())
   _,rd=rt.query_nearest(pg,return_distance=True,all_matches=False);_,md=mt.query_nearest(pg,return_distance=True,all_matches=False)
   invalid|=md<8;excluded['major_road_8m_proxy']+=int((md<8).sum());invalid|=cat==14;excluded['function_excluded']+=int((cat==14).sum());excluded['outside_admin']+=int((vill<0).sum());invalid|=vill<0
   # Road access is a diagnostic, not a silent exclusion: missing private roads are common.
   good=~invalid;total+=len(rows)
   values=[np.array([r[0] for r in rows]),np.array([r[1] for r in rows]),np.array([r[2] for r in rows]),area,vill,cat,lev,np.array(known),explicit,rd,rescap,jobcap]
   for k,v in zip(cols,values):cols[k].append(v[good])
   if total%250000==0:print('classified',total,'seconds',round(time.monotonic()-START),flush=True)
  arr={k:np.concatenate(v) for k,v in cols.items()};np.savez_compressed(SCR/'building_candidates.npz',**arr);np.savez_compressed(SCR/'baseline_validity.npz',contained=baseline_contained,**baseline_mask)
  stats={'inventory_buildings':total,'eligible':len(arr['rowid']),'excluded_overlapping_counts':dict(excluded),'building_parts_not_yet_merged':parts,'context_polygon_counts':dict(context_counts),'baseline_outside_mapped_buildings_points':int((~baseline_contained).sum()),'baseline_outside_mapped_buildings_jobs':int(base['jobs'][~baseline_contained].sum()),'baseline_mapped_mask_hits':{k:{'points':int(v.sum()),'residents':int(base['home'][v].sum()),'jobs':int(base['jobs'][v].sum())} for k,v in baseline_mask.items()},'missing_levels_fraction':float(1-arr['explicit_levels'].mean()),'inferred_function_fraction':float(1-arr['explicit_function'].mean()),'farther_than_250m_from_mapped_road_fraction':float(np.mean(arr['road_m']>250))}
  dump('inventory_metrics.json',stats);print(json.dumps(stats),flush=True)
 else:
  cache=np.load(SCR/'building_candidates.npz');arr={k:cache[k]for k in cache.files}
 # Packaged water includes coastline/ocean, missing from PBF closed-area-only masks.
 water=shapely.from_wkb((Path('work/organic-audit/packaged_water.wkb')).read_bytes());hit=shapely.contains_xy(water,arr['lon'],arr['lat']);arr={k:v[~hit]for k,v in arr.items()}
 stats=json.loads((ROOT/'docs/organic-stage-a/inventory_metrics.json').read_text());stats['packaged_water_additional_excluded']=int(hit.sum());stats['eligible_after_coast_mask']=len(arr['rowid']);dump('inventory_metrics.json',stats)
 # Correct known non-residential functions before allocating generic low-rise capacity.
 corrected={};tanks=[]
 for rowid,ts in DB.execute("SELECT rowid,tags FROM buildings WHERE json_extract(tags,'$.amenity') IN ('place_of_worship','community_centre','arts_centre','bank','restaurant','cafe','fast_food','bus_station','ferry_terminal') OR json_extract(tags,'$.building') IN ('storage_tank','mosque','church','temple','cathedral','train_station','transportation','stadium','hangar') OR json_extract(tags,'$.aeroway') IN ('terminal','hangar')"):
  t=json.loads(ts);b=t.get('building');am=t.get('amenity')
  if b in ['storage_tank','hangar'] or t.get('aeroway')=='hangar':tanks.append(rowid)
  else:corrected[rowid]=7 if am in ['bank','restaurant','cafe','fast_food'] else 17 if b in ['train_station','transportation'] or am in ['bus_station','ferry_terminal'] or t.get('aeroway')=='terminal' else 16
 keep=~np.isin(arr['rowid'],tanks);arr={k:v[keep]for k,v in arr.items()}
 for c in [7,16,17]:
  hit=np.isin(arr['rowid'],[i for i,k in corrected.items()if k==c]);arr['category'][hit]=c;arr['rescap'][hit]=0;arr['jobcap'][hit]=arr['area'][hit]*arr['levels'][hit]*.8/SQM_JOB[c]
 # Fill only villages without mapped residential capacity, using independently valid developed parcels.
 parcel_data=readgz(OUT/'fallback_parcels.geojson.gz')['features'];parcel_map={};vrc=np.bincount(arr['village'],weights=arr['rescap'],minlength=len(vs));byadmin={v['id']:i for i,v in enumerate(vs)}
 flagged={p['admin_id']for p in json.loads((ROOT/'sources/organic/coverage_support.json').read_text()).get('flagged_villages',[])}if (ROOT/'sources/organic/coverage_support.json').exists()else set()
 for q,feature in enumerate(parcel_data):
  v=byadmin[feature['properties']['admin_id']]
  if vrc[v]>0 and feature['properties']['admin_id']not in flagged:continue
  rowid=-q-1;parcel_map[rowid]=feature
 extras=[]
 for rowid,feature in parcel_map.items():
  pr=feature['properties'];area=pr['area_m2'];extras.append({'rowid':rowid,'lon':feature['anchor'][0],'lat':feature['anchor'][1],'area':area,'village':byadmin[pr['admin_id']],'category':1,'levels':1.5,'explicit_levels':False,'explicit_function':False,'road_m':pr['road_access_m'],'rescap':area*1.5*.8*.95/25,'jobcap':area*1.5*.8*.05/350})
 for k in arr:arr[k]=np.r_[arr[k],[e[k]for e in extras]].astype(arr[k].dtype)
 print('fallback candidates',len(extras),flush=True)
 # Major roads and rivers are barriers for aggregation, not barriers for commuting.
 roads=readgz(ROOT/'assets/JKT/roads.geojson.gz');barriers=[shapely.transform(shapely.geometry.shape(f['geometry']),PROJ,interleaved=False)for f in roads['features']if f['properties'].get('roadClass')in ['major','highway']and f['properties'].get('structure')=='normal'];del roads
 barrier_tree=shapely.STRtree(barriers);river=shapely.transform(water,PROJ,interleaved=False);shapely.prepare(river)
 def blocked(start,end):
  lines=shapely.linestrings(np.stack([start,end],axis=1));result=shapely.intersects(river,lines);pairs=barrier_tree.query(lines,predicate='crosses')
  if pairs.size:result[pairs[0]]=True
  return result
 def cluster_assign(members,picked,radius):
  tree=cKDTree(xy[picked]);dd,nn=tree.query(xy[members],k=min(4,len(picked)))
  if dd.ndim==1:dd=dd[:,None];nn=nn[:,None]
  assigned=np.full(len(members),-1,dtype=int);dist=np.full(len(members),np.inf)
  for k in range(dd.shape[1]):
   pending=np.flatnonzero((assigned<0)&(dd[:,k]<=radius))
   if not len(pending):continue
   hit=blocked(xy[members[pending]],xy[picked[nn[pending,k]]]);ok=pending[~hit];assigned[ok]=nn[ok,k];dist[ok]=dd[ok,k]
  return assigned,dist
 # Select weighted, irregular actual-building anchors within each village/function stratum.
 rng=np.random.default_rng(20261107);xy=np.array(PROJ(arr['lon'],arr['lat'])).T;water_contact=shapely.intersects_xy(river,xy[:,0],xy[:,1]);print('projected water-contact candidates excluded',int(water_contact.sum()),flush=True);arr={k:v[~water_contact]for k,v in arr.items()};xy=xy[~water_contact];vpop=np.array([v['population'] for v in vs]);before_vhome=np.bincount(base['villageids'],weights=base['home']/100,minlength=len(vs)).astype(int)
 # Density is an internal morphology covariate; final coordinates remain actual buildings.
 tree=cKDTree(xy);morph=np.zeros(len(xy),dtype=np.int8)
 for start in range(0,len(xy),100000):
  end=min(start+100000,len(xy));dd,_=tree.query(xy[start:end],k=9,workers=2);morph[start:end]=np.where((dd[:,-1]<50)&(arr['area'][start:end]<150),1,np.where(dd[:,-1]>150,3,2))
 low=np.isin(arr['category'],[0,1]);sqm=np.select([morph==1,morph==3],[18.,30.],default=25.);arr['rescap'][low]*=22/sqm[low]
 # Round derived village estimates within each kecamatan, preserving all published controls exactly.
 for region,kec in sorted({(v['region'],v['kecamatan'])for v in vs}):
  ids=np.array([i for i,v in enumerate(vs)if v['region']==region and v['kecamatan']==kec])
  vpop[ids]=apportion(vpop[ids],round(vpop[ids].sum()))
 vpop=vpop.astype(np.int64)
 target=60000;quotas=np.maximum(4,apportion(np.sqrt(vpop),target));chosen=[];cluster_of=np.full(len(xy),-1,dtype=np.int32);fallbacks=[];distances=[]
 for v in range(len(vs)):
  if v%100==0:print('clustering village',v,'anchors',len(chosen),flush=True)
  ids=np.flatnonzero(arr['village']==v)
  if not len(ids):fallbacks.append({'village':vs[v]['id'],'reason':'no valid mapped buildings; no fabricated point'});continue
  # capacity mixture is for sampling coverage only, not population/job totals.
  w=arr['rescap'][ids]+arr['jobcap'][ids]*3+1;num=min(len(ids),int(quotas[v]));priority=-np.log(np.maximum(rng.random(len(ids)),1e-15))/w;sel=np.argsort(priority)[:num]
  # Preserve each functional category, including hospitals and factories.
  for c in np.unique(arr['category'][ids]):
   ci=np.flatnonzero(arr['category'][ids]==c);sel=np.union1d(sel,ci[np.argmin(priority[ci])])
  # Aggregate only buildings of the same functional class within this village.
  for c in np.unique(arr['category'][ids]):
   members=ids[arr['category'][ids]==c];picked=ids[sel[arr['category'][ids[sel]]==c]]
   radius=np.where(morph[members]==1,200,np.where(morph[members]==3,500,350));nn,dd=cluster_assign(members,picked,radius)
   loops=0
   while np.any(nn<0):
    bad=np.flatnonzero(nn<0);remaining=np.ones(len(bad),bool);extra=[];bt=cKDTree(xy[members[bad]])
    for q in range(len(bad)):
     if not remaining[q]:continue
     extra.append(members[bad[q]]);remaining[bt.query_ball_point(xy[members[bad[q]]],float(radius[bad[q]])*.65)]=False
    picked=np.unique(np.r_[picked,extra]);nn,dd=cluster_assign(members,picked,radius);loops+=1
    if loops>10:
     picked=np.unique(np.r_[picked,members[nn<0]]);nn,dd=cluster_assign(members,picked,radius);assert np.all(nn>=0)
   offset=len(chosen);chosen.extend(picked.tolist());cluster_of[members]=nn+offset;distances.extend(dd.tolist())
 chosen=np.array(chosen);np.savez_compressed(SCR/'cluster_members.npz',rowid=arr['rowid'],cluster=cluster_of);n=len(chosen);valid=cluster_of>=0;rc=np.bincount(cluster_of[valid],weights=arr['rescap'][valid],minlength=n);jc=np.bincount(cluster_of[valid],weights=arr['jobcap'][valid],minlength=n);pop=np.zeros(n,dtype=np.int64);home=np.zeros(n,dtype=np.int64);jobs=np.zeros(n,dtype=np.int64);av=arr['village'][chosen];ar=vreg[av]
 # Keep existing village population controls, including explicitly-labelled derived estimates.
 for v in range(len(vs)):
  ids=np.flatnonzero(av==v)
  if not len(ids):continue
  if rc[ids].sum()==0:
   fallbacks.append({'village':vs[v]['id'],'reason':'no residential-class capacity; residents withheld pending developed-parcel fallback'});continue
  pop[ids]=apportion(rc[ids],vpop[v]);home[ids]=apportion(rc[ids],before_vhome[v])*100
 for r in range(13):
  ids=np.flatnonzero(ar==r);formal=jc[ids]/jc[ids].sum();local=rc[ids]/rc[ids].sum();weight=.8*formal+.2*local;jobs[ids]=apportion(weight,base['od'].sum(axis=0)[r]//100)*100
 # Category mix must be aggregated from constituent buildings, not anchor category.
 mixes=np.zeros((n,len(CATS)))
 for c in range(len(CATS)):
  m=valid&(arr['category']==c);mixes[:,c]=np.bincount(cluster_of[m],weights=arr['jobcap'][m],minlength=n)
 rows=[]
 for i,j in enumerate(chosen):
  rowid=int(arr['rowid'][j]);rr=DB.execute('SELECT id FROM buildings WHERE rowid=?',(rowid,)).fetchone()[0]if rowid>0 else parcel_map[rowid]['properties']['id']
  rows.append({'id':f'audit_{i}','location':[float(arr['lon'][j]),float(arr['lat'][j])],'osm_id':rr if rowid>0 else None,'source_anchor_id':rr,'anchor_kind':'building'if rowid>0 else 'builtup_parcel','source_year':2026 if rowid>0 else 2021,'admin_id':vs[av[i]]['id'],'population':int(pop[i]),'model_residents':int(home[i]),'jobs':int(jobs[i]),'relative_residential_capacity':round(float(rc[i]),3),'relative_employment_capacity':round(float(jc[i]),3),'anchor_function':CATS[arr['category'][j]],'dominant_job_capacity_function':CATS[int(mixes[i].argmax())],'anchor_morphology_inferred':['none','dense_lowrise','suburban_or_urban','sparse_periurban_rural'][int(morph[j])],'anchor_levels_observed':bool(arr['explicit_levels'][j]),'function_observed':bool(arr['explicit_function'][j]),'road_distance_m':round(float(arr['road_m'][j]),1)})
 unlocated=[{'admin_id':vs[v]['id'],'population':int(vpop[v]),'model_residents':int(before_vhome[v]*100),'reason':('No eligible mapped buildings' if not np.any(av==v) else 'No mapped residential capacity')+'; pending developed-parcel / validated built-up fallback'} for v in range(len(vs)) if not np.any(av==v) or rc[av==v].sum()==0]
 savegz(OUT/'proposed_allocations.json.gz',{'stage':'B_STAGED_COMPLETE_ALLOCATION','seed':20261107,'population_semantics':'inhabitants; existing derived village estimates retained','model_residents_semantics':'working tripmakers, baseline village margins retained; groups of 100','jobs_semantics':'scenario allocations, not observed workplace counts','points':rows,'unlocated_allocations':unlocated,'unallocated_villages':fallbacks})
 np.savez_compressed(OUT/'proposed_arrays.npz',locations=np.array([arr['lon'][chosen],arr['lat'][chosen]]).T,xy=xy[chosen],home=home,jobs=jobs,population=pop,villages=av,regions=ar,category=arr['category'][chosen],capacity_mix=mixes)
 check={'points':n,'unlocated_village_count':len(unlocated),'unlocated_population':sum(x['population'] for x in unlocated),'unlocated_working_residents':sum(x['model_residents'] for x in unlocated),'population_conserved_including_unlocated':int(pop.sum())+sum(x['population'] for x in unlocated)==int(vpop.sum()),'origins_conserved_including_unlocated':int(home.sum())+sum(x['model_residents'] for x in unlocated)==int(base['home'].sum()),'population':int(pop.sum()),'population_target':int(vpop.sum()),'population_residual':int(pop.sum()-vpop.sum()),'origins':int(home.sum()),'destinations':int(jobs.sum()),'origin_target':int(base['home'].sum()),'destination_target':int(base['jobs'].sum()),'regional_origins_exact':bool(np.array_equal(np.bincount(ar,weights=home,minlength=13),base['od'].sum(axis=1))),'regional_jobs_exact':bool(np.array_equal(np.bincount(ar,weights=jobs,minlength=13),base['od'].sum(axis=0))),'all_located_village_population_exact':bool(all(pop[av==v].sum()==vpop[v] for v in np.unique(av) if rc[av==v].sum()>0)),'all_village_working_origins_exact':bool(all(home[av==v].sum()==before_vhome[v]*100 for v in range(len(vs)))),'fallbacks':fallbacks,'max_cluster_radius_m':float(max(distances)),'cluster_distance_unweighted_p50_p90_p99_m':np.quantile(distances,[.5,.9,.99]).tolist(),'largest_anchor_jobs':int(jobs.max()),'top_1percent_job_share':float(np.sort(jobs)[-max(1,n//100):].sum()/jobs.sum()),'phase_histogram_25m':np.histogram((xy[chosen]%500).ravel(),np.arange(0,501,25))[0].tolist(),'candidate_npz_bytes':(SCR/'building_candidates.npz').stat().st_size,'allocation_gzip_bytes':(OUT/'proposed_allocations.json.gz').stat().st_size,'seconds':time.monotonic()-START,'peak_rss_bytes_macos':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limitations':['Point-level OD generated separately after allocation','OSM parts floor bands merged where parent containment>=90%','Node POIs and official industrial sites joined by containment; unmatched sites not forced into nearest buildings','Coastline mask is generalized packaged zoom12 water; not a surveyed shoreline','Unknown buildings use density-derived low-rise priors; morphology is inferred, not observed','Twenty percent of regional jobs use residential capacity as a neighborhood-work scenario prior' ,'Road widths are sensitivity proxies, not surveyed carriageway bounds','Catchments same-function and same-village; straight aggregation segment cannot cross major-road line or water']}
 dump('proposal_checks.json',check);print(json.dumps(check),flush=True)
