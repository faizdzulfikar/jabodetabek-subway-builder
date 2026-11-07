"""Developed-parcel fallback: WorldCover2021 built-up, current roads, hard masks.
No regular cell-center coordinates or uniform scattering are generated.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
import shapely,sqlite3,zlib,rasterio,rasterio.features
from shapely.ops import nearest_points
SCR=Path('work/organic-stage-b');OUT=ROOT/'docs/organic-stage-b';PROJ=Transformer.from_crs(4326,32748,always_xy=True).transform;INV=Transformer.from_crs(32748,4326,always_xy=True).transform

def pieces(g):
 if g.geom_type=='Polygon':return [g]
 return [p for x in getattr(g,'geoms',[])for p in pieces(x)]
if __name__=='__main__':
 started=time.monotonic();db=sqlite3.connect('work/organic-audit/inventory.sqlite');bounds=readgz(ROOT/'sources/government/village_boundaries.geojson.gz')['features'];vmap={f['properties']['code']:shapely.make_valid(shapely.transform(shapely.geometry.shape(f['geometry']),PROJ,interleaved=False))for f in bounds};props={f['properties']['code']:f['properties']for f in bounds};gaps=readgz(ROOT/'docs/organic-stage-a/proposed_allocations.json.gz')['unlocated_allocations'];mask=[];res=[];industrial=[]
 if (ROOT/'sources/organic/coverage_support.json').exists():
  existing={p['admin_id']for p in gaps};gaps += [{'admin_id':p['admin_id']}for p in json.loads((ROOT/'sources/organic/coverage_support.json').read_text())['flagged_villages']if p['admin_id']not in existing]
 if (ROOT/'sources/organic/coverage_support.json').exists():
  existing={p['admin_id']for p in gaps};gaps += [{'admin_id':code}for code in json.loads((ROOT/'sources/organic/coverage_support.json').read_text())['mandatory_admin_ids']if code not in existing]
 if (OUT/'inventory_enrichment.json').exists():
  existing={p['admin_id']for p in gaps};gaps += [{'admin_id':code}for code in json.loads((OUT/'inventory_enrichment.json').read_text()).get('candidate_villages_without_res_capacity',[])if code not in existing]
 if (OUT/'proposed_allocations.json.gz').exists():
  existing={p['admin_id']for p in gaps};gaps += [p for p in readgz(OUT/'proposed_allocations.json.gz')['unlocated_allocations']if p['admin_id']not in existing]
 for oid,ts,blob in db.execute('select * from context'):
  t=json.loads(ts);l=t.get('landuse');n=t.get('natural');ae=t.get('aeroway');am=t.get('amenity');isbad=n in ['water','bay','strait','wood','wetland']or l in ['forest','reservoir','cemetery','railway']or ae in ['runway','taxiway','apron']or t.get('leisure')=='nature_reserve'or am in ['school','university','college','hospital','place_of_worship','parking','prison']
  if isbad:mask.append(shapely.make_valid(shapely.transform(shapely.from_wkb(zlib.decompress(blob)),PROJ,interleaved=False)))
  if l=='industrial':industrial.append(shapely.make_valid(shapely.transform(shapely.from_wkb(zlib.decompress(blob)),PROJ,interleaved=False)))
  if l=='residential':res.append(shapely.make_valid(shapely.transform(shapely.from_wkb(zlib.decompress(blob)),PROJ,interleaved=False)))
 mask.append(shapely.transform(shapely.from_wkb(Path('work/organic-audit/packaged_water.wkb').read_bytes()),PROJ,interleaved=False));air=readgz(ROOT/'assets/JKT/runways_taxiways.geojson.gz');mask += [shapely.transform(shapely.geometry.shape(f['geometry']),PROJ,interleaved=False)for f in air['features']if f['geometry']['type']in ['Polygon','MultiPolygon']];mt=shapely.STRtree(mask);it=shapely.STRtree(industrial);rt=shapely.STRtree(res)
 roads=readgz(ROOT/'assets/JKT/roads.geojson.gz');rgs=[];width=[]
 for f in roads['features']:
  if f['properties'].get('structure')!='normal':continue
  rgs.append(shapely.transform(shapely.geometry.shape(f['geometry']),PROJ,interleaved=False));width.append(8 if f['properties'].get('roadClass')in ['major','highway']else 3)
 db.execute('CREATE INDEX IF NOT EXISTS buildings_lon_lat ON buildings(lon,lat)');db.commit()
 roadtree=shapely.STRtree(rgs);width=np.array(width);features=[];stats=[]
 with rasterio.open(SCR/'worldcover2021_S09E105.tif')as src,rasterio.open('work/demand-v2/crop.tif')as worldpop:
  for gap in gaps:
   code=gap['admin_id'];vg=vmap[code];wgs=shapely.transform(vg,INV,interleaved=False);win=rasterio.windows.from_bounds(*wgs.bounds,src.transform).round_offsets().round_lengths();ar=src.read(1,window=win);polys=[]
   for gj,val in rasterio.features.shapes((ar==50).astype('uint8'),mask=ar==50,transform=src.window_transform(win)):
    g=shapely.transform(shapely.geometry.shape(gj),PROJ,interleaved=False).intersection(vg)
    if not g.is_empty:polys.append(g)
   built=shapely.union_all(polys)
   # Supplement only currently unmapped developed land: never count existing roofs twice.
   x0,y0,x1,y1=wgs.bounds;existing_roofs=[]
   for blob, in db.execute('SELECT geometry FROM buildings WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?',(x0-.003,x1+.003,y0-.003,y1+.003)):
    roof=shapely.transform(shapely.make_valid(shapely.from_wkb(zlib.decompress(blob))),PROJ,interleaved=False)
    if roof.intersects(vg):existing_roofs.append(roof)
   if existing_roofs:built=built.difference(shapely.union_all(existing_roofs).buffer(2))
   matches=mt.query(vg,predicate='intersects');forbidden=shapely.union_all([mask[i].intersection(vg)for i in matches]);ri=roadtree.query(vg.buffer(300),predicate='intersects');localroads=[rgs[i]for i in ri];corridor=shapely.union_all([g.buffer(200)for g in localroads]);carriage=shapely.union_all([rgs[i].buffer(float(width[i]))for i in ri]);developed=built.difference(forbidden).intersection(corridor).difference(carriage);validpieces=[g for g in pieces(shapely.make_valid(developed))if g.area>=70];localtree=shapely.STRtree(localroads);count=0;industrial_parts=[industrial[i].intersection(vg)for i in it.query(vg,predicate='intersects')];industrial_local=shapely.union_all(industrial_parts);shapely.prepare(industrial_local);residential_local=shapely.union_all([res[i].intersection(vg)for i in rt.query(vg,predicate='intersects')]);shapely.prepare(residential_local)
   for g in validpieces:
    # Anchor at the developed parcel's access side, using the real road geometry.
    core=g.buffer(-1)
    if core.is_empty or core.area<10:continue
    rp=core.representative_point();q=localtree.nearest(rp);roadpoint=nearest_points(localroads[q],rp)[0];anchor=nearest_points(core,roadpoint)[0]
    if not vg.covers(anchor)or anchor.distance(forbidden)<.1 or anchor.distance(carriage)<.1:continue
    lon,lat=INV(anchor.x,anchor.y);wp=float(next(worldpop.sample([(lon,lat)]))[0]);in_industrial=industrial_local.covers(anchor);in_residential=residential_local.covers(anchor)
    if in_industrial and not in_residential and (g.area>1200 or wp<10):continue
    if wp<=0:continue
    qg=shapely.transform(g,INV,interleaved=False);features.append({'type':'Feature','properties':{'id':f'parcel_{code}_{count}','admin_id':code,'source':'ESA_WorldCover2021_v200_class50_plus_OSM2026_road_access','source_year':2021,'function':'residential_inferred','confidence':'residential_landuse_supported'if in_residential else'small_builtup_industrial_context_inferred'if in_industrial else'fallback_not_observed_building','worldpop2025_pixel_population':wp,'industrial_context':bool(in_industrial),'residential_landuse_support':bool(in_residential),'area_m2':g.area,'road_access_m':anchor.distance(localroads[q]),'population':0},'geometry':shapely.geometry.mapping(qg),'anchor':[lon,lat]});count+=1
   stats.append({**props[code],'fallback_parcels':count,'builtup_m2_before_masks':built.area,'eligible_developed_m2':sum(g.area for g in validpieces)});print(code,count,flush=True)
 save={'type':'FeatureCollection','features':features}
 with gzip.GzipFile(filename=str(OUT/'fallback_parcels.geojson.gz'),mode='wb',mtime=0)as f:f.write(json.dumps(save,separators=(',',':')).encode())
 summary={'parcels':len(features),'villages':len(stats),'without_fallback':[p for p in stats if not p['fallback_parcels']],'by_village':stats,'source_url':'https://esa-worldcover.org/en/data-access','worldcover_year':2021,'worldcover_sha256':hashlib.sha256((SCR/'worldcover2021_S09E105.tif').read_bytes()).hexdigest(),'method':'unmapped connected built-up parcels (all existing OSM roofs subtracted with2m tolerance), village clip, hard-mask and all-road carriageway subtraction, within200m road corridor; nearest valid interior point on access side, no random jitter','limitations':['2021 land-cover classification is fallback evidence, not observed2026 building function','No claim of parcel ownership or individual house count','Road widths inferred8m major/3m others','Mapped residential landuse takes priority in overlap; otherwise industrial context admits only small unmapped builtup parcels<=1200m2 with WorldPop2025>=10persons/100mcell. Existing roofs/facilities already subtracted'],'seconds':time.monotonic()-started};(OUT/'fallback_coverage.json').write_text(json.dumps(summary,indent=2));print('COMPLETE',len(features),'unresolved',len(summary['without_fallback']))
