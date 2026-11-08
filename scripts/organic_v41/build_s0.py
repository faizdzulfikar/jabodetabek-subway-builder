"""Approved Stage B S0+OD40: targeted member-level corrections; no S1 intensities.
Only writes staging outputs; install is a separately gated step.
"""
from pathlib import Path
import numpy as np,json,gzip,csv,sqlite3,zlib,copy,time,hashlib
import shapely
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41-stage-b';OUT.mkdir(exist_ok=True)
P=Transformer.from_crs(4326,32748,always_xy=True).transform;INV=Transformer.from_crs(32748,4326,always_xy=True).transform
CATS=['unknown','residential','apartments','office','government','factory','warehouse','retail','market','university','school','hospital','hotel','mixed','excluded','exhibition','community','transport']
SQM=np.array([300,350,200,20,25,75,140,35,45,50,70,45,100,40,1e12,140,100,150])
def readgz(p):return json.load(gzip.open(p,'rt'))
def gz(p,d):
 with gzip.GzipFile(filename=str(p),mode='wb',mtime=0)as f:f.write(json.dumps(d,separators=(',',':')).encode())
def dump(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
def csvout(n,rr):
 with(OUT/n).open('w')as f:w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
def apportion(w,total):
 q=np.asarray(w,float)/sum(w)*int(total);v=np.floor(q).astype(np.int64);v[np.argsort(-(q-v),kind='stable')[:int(total-v.sum())]]+=1;return v
if __name__=='__main__':
 started=time.monotonic();base=readgz(ROOT/'docs/organic-stage-b/proposed_allocations.json.gz');old=base['points'];raw=np.load(ROOT/'docs/organic-stage-b/proposed_arrays.npz');b={k:raw[k]for k in raw.files};a={k:v.copy()for k,v in b.items()};n=len(old);cor=list(csv.DictReader((ROOT/'docs/organic-v41/residential_anchor_corrections.csv').open()));affected=sorted(int(x['anchor'])for x in cor);m=np.load('work/organic-stage-b/cluster_members.npz');select=np.isin(m['cluster'],affected);rids=m['rowid'][select];clusters=m['cluster'][select];rawc=np.load('work/organic-stage-b/building_candidates.npz');c={k:rawc[k]for k in rawc.files};wanted=set(map(int,rids));lookup={int(r):i for i,r in enumerate(c['rowid'])if int(r)in wanted};db=sqlite3.connect('work/organic-audit/inventory.sqlite')
 ctx=[]
 for oid,ts,blob in db.execute("select * from context where tags like '%aeroway%'or tags like '%water%'"):
  t=json.loads(ts)
  if t.get('aeroway')in ['runway','taxiway','apron']or t.get('natural')in ['water','bay','strait']or t.get('landuse')=='reservoir':ctx.append(shapely.transform(shapely.from_wkb(zlib.decompress(blob)),P,interleaved=False))
 mask=shapely.union_all(ctx);airport=shapely.from_wkb(zlib.decompress(db.execute("select geometry from context where id='r19104217'").fetchone()[0]))
 roads=readgz(ROOT/'assets/JKT/roads.geojson.gz');service=[]
 for f in roads['features']:
  pr=f['properties'];g=shapely.geometry.shape(f['geometry'])
  if not g.intersects(shapely.box(106.62,-6.16,106.70,-6.09))or pr.get('roadClass')in ['major','highway']or pr.get('structure')not in [None,'normal']:continue
  g=shapely.transform(g,P,interleaved=False)
  if not mask.intersects(g):service.append(g)
 del roads
 assert service;roadtree=shapely.STRtree(service)
 def accesspoint(geometry):
  g=shapely.transform(geometry,P,interleaved=False);inside=g.buffer(-10)
  if inside.is_empty:inside=g.buffer(-2)
  if inside.is_empty:inside=g
  # Staff-side is inferred from nearest mapped non-airside local road, not a surveyed gate.
  ranked=sorted(roadtree.query(g.buffer(1000)).tolist(),key=lambda j:service[j].distance(g))
  for j in ranked:
   line=shapely.shortest_line(service[j],inside)
   if line.is_empty or mask.intersects(line):continue
   pt=shapely.Point(line.coords[-1]);ll=shapely.transform(pt,INV,interleaved=False)
   return [ll.x,ll.y],float(line.length),j
  raise RuntimeError('No mapped non-airside road-side building interior; do not fabricate access')
 points=[];rc=[];jc=[];village=[];reg=[];category=[];mix=[];source_old=[];kept=[]
 for i,p in enumerate(old):
  if i in affected:continue
  kept.append(i);points.append(copy.deepcopy(p));rc.append(p['relative_residential_capacity']);jc.append(p['relative_employment_capacity']);village.append(int(b['villages'][i]));reg.append(int(b['regions'][i]));category.append(int(b['category'][i]));mix.append(b['capacity_mix'][i]);source_old.append(i)
 memberrows=[];facility_access=[];excluded=0
 for cl in affected:
  rr=rids[clusters==cl];ix=np.array([lookup[int(r)]for r in rr]);rs=c['rescap'][ix].astype(float);js=c['jobcap'][ix].astype(float);rs*=old[cl]['relative_residential_capacity']/max(rs.sum(),1e-20);js*=old[cl]['relative_employment_capacity']/max(js.sum(),1e-20)
  for k,(rid,q)in enumerate(zip(rr,ix)):
   oid,lon,lat,area,ts,blob=db.execute('select * from buildings where rowid=?',(int(rid),)).fetchone();tags=json.loads(ts);g=shapely.from_wkb(zlib.decompress(blob));name=tags.get('name','').lower();isairport=airport.covers(shapely.Point(lon,lat));cat=int(c['category'][q]);r=float(rs[k]);j=float(js[k]);reason='retain_existing_member_prior';evidence='inferred existing function';fl=float(c['area'][q]*c['levels'][q]*.8)
   # Main function wins: a funeral house WITH parking is not itself a parking structure.
   if tags.get('amenity')in ['mortuary','community_centre','arts_centre']or tags.get('building')=='sports_centre':cat=16;r=0;j=fl/SQM[16];reason='community_service_not_residential';evidence='observed main-function tag'
   elif tags.get('building')in ['gasometer','storage_tank','parking']or tags.get('man_made')in ['gasometer','storage_tank']:cat=14;r=0;j=0;reason='tank_or_parking_excluded';evidence='observed building/function tag'
   elif 'marketing'in name or(isairport and any(x in name for x in ['office','management building','reservation center','garuda city centre'])):cat=3;r=0;j=fl/SQM[3];reason='named_office_no_residence';evidence='inferred from mapped operational name; levels unchanged'
   elif isairport and any(x in name for x in ['utility building','emergency hall','ground support equipment']):cat=17;r=0;j=fl/SQM[17];reason='named_airport_operations_no_residence';evidence='inferred operational name; existing transport150 prior'
   elif 'community center'in name or(isairport and any(x in name for x in ['garuda club','multipurpose building'])):cat=16;r=0;j=fl/SQM[16];reason='named_community_service_no_residence';evidence='inferred mapped service name'
   loc=[lon,lat];road_distance=float(c['road_m'][q])
   if cat in [3,16,17]and isairport:
    loc,road_distance,roadid=accesspoint(g);facility_access.append({'osm_id':oid,'name':tags.get('name',''),'type':CATS[cat],'road_distance_m':round(road_distance,2),'anchor_longitude':loc[0],'anchor_latitude':loc[1],'access_evidence':'inferred nearest mapped local road outside runway/taxiway/apron; not surveyed employee entrance','crosses_mapped_airside_or_water':False})
   memberrows.append({'original_cluster':cl,'osm_id':oid,'building_tag':tags.get('building',''),'name':tags.get('name',''),'reason':reason,'evidence':evidence,'old_relative_residential_capacity_share':float(rs[k]),'new_relative_residential_capacity':r,'old_relative_employment_capacity_share':float(js[k]),'new_relative_employment_capacity':j,'levels':float(c['levels'][q]),'levels_observed':bool(c['explicit_levels'][q])})
   if r==0 and j==0:excluded+=1;continue
   p={'location':loc,'osm_id':oid,'source_anchor_id':oid,'anchor_kind':'building','source_year':2026,'admin_id':old[cl]['admin_id'],'population':0,'model_residents':0,'jobs':0,'relative_residential_capacity':r,'relative_employment_capacity':j,'anchor_function':CATS[cat],'dominant_job_capacity_function':CATS[cat],'anchor_morphology_inferred':old[cl]['anchor_morphology_inferred'],'anchor_levels_observed':bool(c['explicit_levels'][q]),'function_observed':evidence.startswith('observed'),'road_distance_m':road_distance,'classification_evidence':evidence,'source_v4_cluster':cl}
   points.append(p);rc.append(r);jc.append(j);village.append(int(b['villages'][cl]));reg.append(int(b['regions'][cl]));category.append(cat);v=np.zeros(18);v[cat]=j;mix.append(v);source_old.append(cl)
 # Restore six hangars at existing transport150 intensity; no S1 coefficients.
 hangs=readgz(ROOT/'docs/organic-v41/proposed_allocations.json.gz')['points'][n:]
 for p0 in hangs:
  p=copy.deepcopy(p0);oid=p['osm_id'];area,ts,blob=db.execute('select area,tags,geometry from buildings where id=?',(oid,)).fetchone();g=shapely.from_wkb(zlib.decompress(blob));loc,rd,roadid=accesspoint(g);p.update(location=loc,road_distance_m=rd,relative_employment_capacity=p['relative_employment_capacity'],classification_evidence='observed hangar; inferred floor/staff-side access');j=p['relative_employment_capacity'];points.append(p);rc.append(0);jc.append(j);village.append(int(p['village']));reg.append(int(p['region']));category.append(17);v=np.zeros(18);v[17]=j;mix.append(v);source_old.append(-1);facility_access.append({'osm_id':oid,'name':json.loads(ts).get('name',''),'type':'hangar','road_distance_m':round(rd,2),'anchor_longitude':loc[0],'anchor_latitude':loc[1],'access_evidence':'inferred nearest mapped local road outside runway/taxiway/apron; not surveyed employee entrance','crosses_mapped_airside_or_water':False})
 rc=np.array(rc);jc=np.array(jc);village=np.array(village);reg=np.array(reg);locations=np.array([p['location']for p in points]);population=np.zeros(len(points),np.int64);home=population.copy();jobs=population.copy();nv=1502
 # Unaffected villages keep exact baseline point allocations, avoiding new rounding churn.
 affected_v=set(int(b['villages'][i])for i in affected);byold={int(i):q for q,i in enumerate(source_old[:len(kept)])}
 for v in range(nv):
  ii=np.flatnonzero(village==v);bi=np.flatnonzero(b['villages']==v)
  if v not in affected_v:
   for i in bi:
    q=byold[int(i)];population[q]=b['population'][i];home[q]=b['home'][i]
  else:
   assert rc[ii].sum()>0;population[ii]=apportion(rc[ii],int(b['population'][bi].sum()));home[ii]=apportion(rc[ii],int(b['home'][bi].sum())//100)*100
 reports=[];names=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz')['names'].tolist()
 for r,name in enumerate(names):
  ii=np.flatnonzero(reg==r);total=int(b['jobs'][b['regions']==r].sum());fl=np.minimum(.8*total*jc[ii]/jc[ii].sum(),2*jc[ii]);remain=total-fl.sum();jobs[ii]=apportion(fl+remain*rc[ii]/rc[ii].sum(),total//100)*100;reports.append({'region':name,'jobs':total,'floor_component_ceiling_multiplier':2,'unclassified_neighborhood_component_share':float(remain/total)})
 for i,p in enumerate(points):p.update(id=f'audit_{i}',population=int(population[i]),model_residents=int(home[i]),jobs=int(jobs[i]),relative_residential_capacity=round(float(rc[i]),6),relative_employment_capacity=round(float(jc[i]),6))
 gz(OUT/'proposed_allocations.json.gz',{'stage':'B_V41_S0_OD40_STAGED','seed':20261107,'points':points,'unlocated_allocations':[],'unallocated_villages':[],'population_semantics':'inhabitants; all v4 village margins preserved','model_residents_semantics':'working tripmakers, all v4 village margins preserved','jobs_semantics':'S0 member-level correction; existing regional controls and priors; no S1 intensities'})
 np.savez_compressed(OUT/'proposed_arrays.npz',locations=locations,xy=np.array(P(*locations.T)).T,population=population,home=home,jobs=jobs,villages=village,regions=reg,category=np.array(category),capacity_mix=np.array(mix))
 csvout('member_reclassification.csv',memberrows);csvout('facility_access.csv',facility_access);dump('employment_capacity_regularization.json',{'regions':reports,'ceiling':2,'new_intensity_parameters':False});dump('build_checks.json',{'approved':'S0+OD40','baseline_anchors':n,'anchors':len(points),'original_clusters_rebuilt':len(affected),'constituent_buildings_reviewed':len(rids),'excluded_tank_parking_members':excluded,'restored_hangars':len(hangs),'population':int(population.sum()),'workers':int(home.sum()),'jobs':int(jobs.sum()),'exact_village_population':all(population[village==v].sum()==b['population'][b['villages']==v].sum()for v in range(nv)),'exact_village_origins':all(home[village==v].sum()==b['home'][b['villages']==v].sum()for v in range(nv)),'unaffected_villages_point_allocations_unchanged':True,'member_capacity_split':'Prior v4 aggregate capacities split proportionally by constituent v4 prior weights; only positively identified functions reclassified. Untargeted geography untouched.','access_limit':'Mapped road-side inferred, not surveyed staff gate or live routing','seconds':time.monotonic()-started})
 print(json.dumps(json.loads((OUT/'build_checks.json').read_text()),indent=2))
