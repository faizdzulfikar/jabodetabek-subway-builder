"""Independent Stage A v4.1 candidate validation; never installs."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
import shapely,sqlite3,zlib,re
OUT=ROOT/'docs/organic-v41'
if __name__=='__main__':
 started=time.monotonic();alloc=readgz(OUT/'proposed_allocations.json.gz');points=alloc['points'];assert not alloc['unlocated_allocations'];cache=np.load(OUT/'proposed_arrays.npz');a={k:cache[k]for k in cache.files};d=readgz(OUT/'candidate-demand.json.gz');sources=readgz(OUT/'engine_point_sources.json.gz');base=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz');vs=readgz(ROOT/'assets/JKT/government_inputs.json.gz')['villages'];vix={v['id']:i for i,v in enumerate(vs)};located=np.bincount(a['villages'],weights=a['population'],minlength=len(vs));norm=lambda s:re.sub('[^A-Z0-9]','',s.upper());controls=json.loads((ROOT/'sources/government/population_controls.json').read_text());checks=[]
 for c in controls:
  ids=[i for i,v in enumerate(vs)if v['region']==c['region']and norm(v['kecamatan'])==norm(c['kecamatan'])and (not c['kelurahan']or norm(v['kelurahan'])==norm(c['kelurahan']))];val=int(located[ids].sum());checks.append({'region':c['region'],'kecamatan':c['kecamatan'],'kelurahan':c['kelurahan'],'target':int(c['population']),'located':val,'residual':val-int(c['population'])})
 assert all(c['residual']==0 for c in checks);(OUT/'population_control_checks.json').write_text(json.dumps(checks,indent=2));db=sqlite3.connect('work/organic-audit/inventory.sqlite');byosm={p['osm_id']:p for p in points if p['osm_id']};matched=set();bad=[]
 for oid,blob in db.execute('SELECT id,geometry FROM buildings'):
  if oid not in byosm:continue
  matched.add(oid);g=shapely.from_wkb(zlib.decompress(blob));p=byosm[oid]
  if not g.covers(shapely.Point(*p['location'])):bad.append(p['id'])
 assert len(matched)==len(byosm) and not bad
 parcels={f['properties']['id']:f for f in readgz(ROOT/'docs/organic-stage-b/fallback_parcels.geojson.gz')['features']};parcel_count=0
 for p in points:
  if p['anchor_kind']!='builtup_parcel':continue
  g=shapely.geometry.shape(parcels[p['source_anchor_id']]['geometry']);assert g.covers(shapely.Point(*p['location']));parcel_count+=1
 boundary={f['properties']['code']:shapely.geometry.shape(f['geometry'])for f in readgz(ROOT/'sources/government/village_boundaries.geojson.gz')['features']};shapely.prepare(list(boundary.values()));assert all(boundary[p['admin_id']].covers(shapely.Point(*p['location']))for p in points);loc=np.array([p['location']for p in points]);assert np.all((loc[:,0]>=106.3)&(loc[:,0]<=107.35)&(loc[:,1]>=-6.85)&(loc[:,1]<=-5.9));pg=shapely.points(loc)
 masks={'water':[],'forest_wetland_proxy':[],'airside':[]}
 for oid,ts,blob in db.execute('SELECT * FROM context'):
  t=json.loads(ts);keys=[]
  if t.get('natural')in ['water','bay','strait']or t.get('waterway')=='riverbank'or t.get('landuse')=='reservoir':keys.append('water')
  if t.get('natural')in ['wood','wetland']or t.get('landuse')=='forest'or t.get('leisure')=='nature_reserve':keys.append('forest_wetland_proxy')
  if t.get('aeroway')in ['runway','taxiway','apron']:keys.append('airside')
  if keys:
   g=shapely.make_valid(shapely.from_wkb(zlib.decompress(blob)))
   for k in keys:masks[k].append(g)
 coast=shapely.from_wkb(Path('work/organic-audit/packaged_water.wkb').read_bytes());shapely.prepare(coast);coast_hits=int(shapely.contains_xy(coast,*loc.T).sum());air=readgz(ROOT/'assets/JKT/runways_taxiways.geojson.gz');masks['airside'] += [shapely.geometry.shape(f['geometry'])for f in air['features']if f['geometry']['type']in ['Polygon','MultiPolygon']];hits={'packaged_water':coast_hits}
 for k,gs in masks.items():
  pair=shapely.STRtree(pg).query(gs,predicate='contains');hits[k]=len(np.unique(pair[1]))if pair.size else 0
 roads=readgz(ROOT/'assets/JKT/roads.geojson.gz');proj=Transformer.from_crs(4326,32748,always_xy=True).transform;major=[shapely.transform(shapely.geometry.shape(f['geometry']),proj,interleaved=False)for f in roads['features']if f['properties']['roadClass']in ['major','highway']and f['properties'].get('structure')=='normal'];_,rd=shapely.STRtree(major).query_nearest(shapely.points(np.array(proj(*loc.T)).T),return_distance=True,all_matches=False);hits['major_road_8m_proxy']=int(np.sum(rd<8-1e-6));assert not any(hits.values()),hits
 # Derive every engine point margin from pops; do not trust serialized counters.
 ids={p['id']:i for i,p in enumerate(d['points'])};assert len(ids)==len(d['points']);h=np.zeros(len(ids),np.int64);j=h.copy();links=[set()for _ in ids];seen=set();od=np.zeros((13,13),np.int64)
 for pop in d['pops']:
  assert pop['id']not in seen;seen.add(pop['id']);u=ids[pop['residenceId']];v=ids[pop['jobId']];assert u!=v and pop['size']==100 and pop['drivingDistance']>0 and pop['drivingSeconds']>0;h[u]+=pop['size'];j[v]+=pop['size'];links[u].add(pop['id']);links[v].add(pop['id']);oi=sources[pop['residenceId']];di=sources[pop['jobId']];od[a['regions'][oi],a['regions'][di]]+=pop['size']
 eh=np.zeros(len(points),np.int64);ej=eh.copy()
 for i,p in enumerate(d['points']):
  assert h[i]==p['residents']and j[i]==p['jobs'];assert len(p['popIds'])==len(set(p['popIds']))and set(p['popIds'])==links[i];src=sources[p['id']];assert p['location']==points[src]['location'];eh[src]+=h[i];ej[src]+=j[i]
 assert np.array_equal(eh,a['home'])and np.array_equal(ej,a['jobs']);assert np.array_equal(od,np.load(OUT/'regional_od_units.npy')*100);assert np.array_equal(od.sum(1),base['od'].sum(1))and np.array_equal(od.sum(0),base['od'].sum(0));assert located.sum()==32615007 and h.sum()==j.sum()==12646700
 report={'stage':'A_V41_CANDIDATE_GATE_PASSED','official_population_controls_exact':len(checks),'population_geolocated':int(located.sum()),'unlocated_population':0,'working_origins':int(h.sum()),'jobs':int(j.sum()),'engine_points':len(ids),'groups':len(seen),'allocation_building_anchors_checked':len(matched),'allocation_parcel_anchors_checked':parcel_count,'all_anchor_admin_and_bbox_checks':True,'mapped_mask_hits':hits,'all_engine_point_margins_exact':True,'all_regional_od_margins_exact':True,'all_pop_references_and_point_links_valid':True,'allocation_sha256':hashlib.sha256((OUT/'proposed_allocations.json.gz').read_bytes()).hexdigest(),'engine_sources_sha256':hashlib.sha256((OUT/'engine_point_sources.json.gz').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256((OUT/'candidate-demand.json.gz').read_bytes()).hexdigest(),'seconds':time.monotonic()-started,'limits':['Zero hits refer to available mapped masks and inferred road widths','2021 parcel fallback and unclassified employment priors retain uncertainty','Travel time is a proxy, not measured congestion']};(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
