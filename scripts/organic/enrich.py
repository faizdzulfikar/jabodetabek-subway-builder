"""Stage B: use the full OSM inventory to join POIs/parts/official industrial sites.
Only scratch candidates change; no engine files are written.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from propose import category,CATS,SQM_JOB
from baseline import *
import sqlite3,zlib,shapely,rasterio
SCR=Path('work/organic-stage-b');AUD=Path('work/organic-audit');OUT=ROOT/'docs/organic-stage-b'
PROJ=Transformer.from_crs(4326,32748,always_xy=True).transform
if __name__=='__main__':
 t=time.monotonic();db=sqlite3.connect(AUD/'inventory.sqlite');a=np.load(AUD/'building_candidates.npz');arr={k:a[k].copy()for k in a.files};lookup=np.full(int(db.execute('select max(rowid)from buildings').fetchone()[0])+1,-1,dtype=np.int32);lookup[arr['rowid']]=np.arange(len(arr['rowid']));pois=[];pclass=[];parts=[];plevel=[]
 for _,lon,lat,ts in db.execute('SELECT * FROM pois'):
  c=category(json.loads(ts))
  if c not in [0,1,2,14]:pois.append(shapely.Point(lon,lat));pclass.append(c)
 sites=readgz(ROOT/'sources/government/industrial_sites.geojson.gz');official_start=len(pois)
 for f in sites['features']:
  if f['geometry']['type']=='Point':pois.append(shapely.geometry.shape(f['geometry']));pclass.append(5)
 for oid,ts,blob in db.execute('SELECT * FROM context'):
  tags=json.loads(ts)
  if 'building:part' not in tags:continue
  try:levels=float(tags['building:levels'])if 'building:levels'in tags else float(tags.get('height','0').replace(' m',''))/3.3;minimum=float(tags.get('building:min_level',0))
  except (ValueError,TypeError):continue
  if levels<=minimum:continue
  parts.append(shapely.make_valid(shapely.from_wkb(zlib.decompress(blob))));plevel.append((minimum,levels))
 allpoints=pois+[g.representative_point()for g in parts];tree=shapely.STRtree(allpoints);best=np.full(len(allpoints),-1,dtype=np.int32);best_area=np.full(len(allpoints),np.inf);geom_parent={}
 cur=db.execute('SELECT rowid,area,geometry FROM buildings')
 while rows:=cur.fetchmany(15000):
  ids=np.array([lookup[r[0]]for r in rows]);valid=ids>=0
  if not valid.any():continue
  rows=[r for r,v in zip(rows,valid)if v];ids=ids[valid];gs=shapely.from_wkb([zlib.decompress(r[2])for r in rows]);pairs=tree.query(gs,predicate='covers')
  for p,q in pairs.T:
   aa=rows[p][1]
   if aa<best_area[q]:best[q]=ids[p];best_area[q]=aa
  # Save only polygons relevant to a part to compute parent/part union floor bands.
  if pairs.size:
   for p,q in pairs.T:
    if q>=len(pois):geom_parent[int(ids[p])]=gs[p]
 # Large unclassified footprints are a low-confidence mixed-use/workshop prior,
 # not full residential stock or observed offices. Keep residential space too.
 large=(arr['category']==0)&(arr['area']>=800)
 arr['category'][large]=13;fl=arr['area'][large]*arr['levels'][large]*.8;arr['rescap'][large]=fl*.6/25;arr['jobcap'][large]=fl*.4/90
 # Broad industrial landuse is not a building function: dense small generic
 # roofs with a positive residential covariate may be mixed housing/workshops.
 from scipy.spatial import cKDTree
 xy=np.array(PROJ(arr['lon'],arr['lat'])).T;small=np.flatnonzero((arr['category']==5)&~arr['explicit_function']&(arr['area']<180));industrial_mixed=np.zeros(len(arr['rowid']),bool)
 if len(small):
  distance,_=cKDTree(xy).query(xy[small],k=9,workers=2);dense=small[distance[:,-1]<60]
  with rasterio.open('work/demand-v2/crop.tif')as wp:
   values=np.array([x[0]for x in wp.sample(zip(arr['lon'][dense],arr['lat'][dense]))]);keep=dense[values>=10]
  industrial_mixed[keep]=True;arr['category'][keep]=13;missing=keep[~arr['explicit_levels'][keep]];arr['levels'][missing]=1.5;floor=arr['area'][keep]*arr['levels'][keep]*.8;arr['rescap'][keep]=floor*.7/22;arr['jobcap'][keep]=floor*.3/90
 nodehits=collections.defaultdict(set)
 for q,c in enumerate(pclass):
  if best[q]>=0:nodehits[int(best[q])].add(c)
 changed=0
 for i,cats in nodehits.items():
  if arr['category'][i] not in [0,1,13]:continue
  c=next(iter(cats))if len(cats)==1 else 13
  if c==3 and arr['area'][i]<400:c=13
  if c==7 and arr['area'][i]<200:c=13
  arr['category'][i]=c;fl=arr['area'][i]*arr['levels'][i]*.8;share=.6 if c==13 else 0;arr['rescap'][i]=fl*share/25;arr['jobcap'][i]=fl*(1-share)/SQM_JOB[c];changed+=1
 parents=collections.defaultdict(list)
 for q,g in enumerate(parts):
  i=int(best[len(pois)+q])
  if i>=0:
   parent=geom_parent[i]
   if g.area>0 and parent.intersection(g).area/g.area>=.9:parents[i].append(q)
 merged=0
 for i,ids in parents.items():
  base=float(arr['levels'][i]);floor=arr['area'][i]*base;bands=sorted(set([base]+[max(base,v)for q in ids for v in plevel[q]]));parent=shapely.transform(geom_parent[i],PROJ,interleaved=False)
  for lo,hi in zip(bands,bands[1:]):
   active=[shapely.transform(parts[q],PROJ,interleaved=False).intersection(parent)for q in ids if plevel[q][0]<=lo and plevel[q][1]>=hi]
   if active:floor+=shapely.union_all(active).area*(hi-lo)
  ratio=floor/(arr['area'][i]*base)
  if ratio>1.00001:arr['rescap'][i]*=ratio;arr['jobcap'][i]*=ratio;arr['levels'][i]=floor/arr['area'][i];arr['explicit_levels'][i]=True;merged+=1
 # Infer missing office/apartment levels from nearby comparable observed buildings,
 # never from the name of a priority center. These remain inferred, not observed.
 from scipy.spatial import cKDTree
 xy=np.array(PROJ(arr['lon'],arr['lat'])).T;context_levels=0
 for c,minimum_area,ceiling in [(3,600,30),(2,250,15)]:
  known=np.flatnonzero((arr['category']==c)&arr['explicit_levels']);unknown=np.flatnonzero((arr['category']==c)&~arr['explicit_levels']&(arr['area']>=minimum_area))
  if not len(known)or not len(unknown):continue
  dd,ii=cKDTree(xy[known]).query(xy[unknown],k=min(8,len(known)))
  if dd.ndim==1:dd=dd[:,None];ii=ii[:,None]
  for row,i in enumerate(unknown):
   neighbors=known[ii[row]];use=(dd[row]<=500)&(arr['area'][neighbors]>=arr['area'][i]/3)&(arr['area'][neighbors]<=arr['area'][i]*3)
   if use.sum()<2:continue
   lev=float(np.clip(np.median(arr['levels'][neighbors[use]]),1,ceiling));ratio=lev/arr['levels'][i];arr['levels'][i]=lev;arr['rescap'][i]*=ratio;arr['jobcap'][i]*=ratio;context_levels+=1
 np.savez_compressed(SCR/'building_candidates.npz',**arr)
 vrc=np.bincount(arr['village'],weights=arr['rescap'],minlength=1502);stats={'stage':'B','candidate_villages_without_res_capacity':[v['id']for i,v in enumerate(readgz(ROOT/'assets/JKT/government_inputs.json.gz')['villages'])if vrc[i]==0],'node_pois_classified':official_start,'official_industrial_points':len(pois)-official_start,'poi_inside_eligible_footprints':int(np.sum(best[:official_start]>=0)),'official_sites_inside_eligible_footprints':int(np.sum(best[official_start:len(pois)]>=0)),'building_function_updates':changed,'dense_small_generic_industrial_context_mixed_inferred':int(np.sum(industrial_mixed&(arr['category']==13))),'large_unknown_footprints_mixed_use_inferred':int(large.sum()),'levels_inferred_from_nearby_comparable_buildings':context_levels,'parts_with_levels':len(parts),'parts_contained_90pct_in_parent':sum(map(len,parents.values())),'parents_with_incremental_floor_union':merged,'join_method':'smallest containing eligible parent; no arbitrary nearest-building assignment','floor_union_method':'parent base + unioned clipped parts per vertical floor band above base; parts not standalone candidates','seconds':time.monotonic()-t}
 (OUT/'inventory_enrichment.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))
