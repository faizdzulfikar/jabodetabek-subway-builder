"""Stage A independent checks: controls, ledgers, geometry, schema and asset hashes."""
from baseline import *
import sys,shapely,sqlite3,zlib,re,resource
if __name__=='__main__':
 scratch=Path(sys.argv[1]);alloc=readgz(OUT/'proposed_allocations.json.gz');inp=readgz(ROOT/'assets/JKT/government_inputs.json.gz');vs=inp['villages'];vindex={v['id']:i for i,v in enumerate(vs)};pop=np.zeros(len(vs),np.int64);located=np.zeros(len(vs),np.int64);home=np.zeros(len(vs),np.int64);points=alloc['points'];regjobs=collections.Counter();reghome=collections.Counter()
 for p in points:
  v=vindex[p['admin_id']];pop[v]+=p['population'];located[v]+=p['population'];home[v]+=p['model_residents'];regjobs[vs[v]['region']]+=p['jobs'];reghome[vs[v]['region']]+=p['model_residents']
 for p in alloc['unlocated_allocations']:
  v=vindex[p['admin_id']];pop[v]+=p['population'];home[v]+=p['model_residents'];reghome[vs[v]['region']]+=p['model_residents']
 norm=lambda s:re.sub('[^A-Z0-9]','',str(s).upper());controls=json.loads((ROOT/'sources/government/population_controls.json').read_text());checks=[]
 for c in controls:
  ids=[i for i,v in enumerate(vs) if v['region']==c['region'] and norm(v['kecamatan'])==norm(c['kecamatan']) and (not c['kelurahan'] or norm(v['kelurahan'])==norm(c['kelurahan']))];value=int(pop[ids].sum());checks.append({'region':c['region'],'kecamatan':c['kecamatan'],'kelurahan':c['kelurahan'],'target':int(c['population']),'allocated_including_unlocated':value,'located':int(located[ids].sum()),'residual':value-int(c['population'])})
 dump('population_control_checks.json',checks)
 # Every preview anchor must be inside its own source footprint and admin polygon.
 db=sqlite3.connect(scratch/'inventory.sqlite');ids={p['osm_id']:p for p in points};bad=[];matched=0
 for oid,blob in db.execute('SELECT id,geometry FROM buildings'):
  if oid not in ids:continue
  p=ids[oid];g=shapely.from_wkb(zlib.decompress(blob));matched+=1
  if not g.covers(shapely.Point(*p['location'])):bad.append(oid)
 waters=shapely.from_wkb((scratch/'packaged_water.wkb').read_bytes());loc=np.array([p['location']for p in points]);sea=shapely.contains_xy(waters,loc[:,0],loc[:,1]);base=np.load(OUT/'baseline_arrays.npz');bsea=shapely.contains_xy(waters,*base['locations'].T)
 boundary=readgz(ROOT/'sources/government/village_boundaries.geojson.gz');polygons={f['properties']['code']:shapely.make_valid(shapely.geometry.shape(f['geometry']))for f in boundary['features']};adminbad=[p['id']for p in points if not polygons[p['admin_id']].covers(shapely.Point(*p['location']))]
 maskgs={'water_inland':[],'forest_wetland_proxy':[],'airside':[]}
 for oid,ts,blob in db.execute('SELECT * FROM context'):
  tags=json.loads(ts);keys=[]
  if tags.get('natural')in ['water','bay','strait']or tags.get('waterway')=='riverbank'or tags.get('landuse')=='reservoir':keys.append('water_inland')
  if tags.get('natural')in ['wood','wetland']or tags.get('landuse')=='forest'or tags.get('leisure')=='nature_reserve':keys.append('forest_wetland_proxy')
  if tags.get('aeroway')in ['runway','taxiway','apron']:keys.append('airside')
  if keys:
   g=shapely.make_valid(shapely.from_wkb(zlib.decompress(blob)))
   for k in keys:maskgs[k].append(g)
 air=readgz(ROOT/'assets/JKT/runways_taxiways.geojson.gz');maskgs['airside'] += [shapely.geometry.shape(f['geometry'])for f in air['features']if f['geometry']['type']in ['Polygon','MultiPolygon']]
 maskhits={};pointgeoms=shapely.points(loc)
 for k,gs in maskgs.items():
  pairs=shapely.STRtree(gs).query(pointgeoms,predicate='within');maskhits[k]=len(np.unique(pairs[0]))if pairs.size else 0
 roads=readgz(ROOT/'assets/JKT/roads.geojson.gz');project=Transformer.from_crs(4326,32748,always_xy=True).transform;major=[shapely.transform(shapely.geometry.shape(f['geometry']),project,interleaved=False)for f in roads['features']if f['properties'].get('roadClass')in ['major','highway']and f['properties'].get('structure')=='normal'];xy=np.array(project(*loc.T)).T;_,rd=shapely.STRtree(major).query_nearest(shapely.points(xy),return_distance=True,all_matches=False);maskhits['major_road_8m_proxy']=int((rd<8).sum())
 oldhash=json.loads((scratch/'baseline_hashes.json' if (scratch/'baseline_hashes.json').exists() else OUT/'production_baseline_hashes.json').read_text());changed=[]
 # baseline manifest may store dictionary directly or under files.
 if 'files'in oldhash:oldhash=oldhash['files']
 for rel,expected in oldhash.items():
  path=ROOT/rel
  if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:changed.append(rel)
 raw=gzip.decompress((OUT/'proposed_allocations.json.gz').read_bytes());times=[]
 for _ in range(3):
  t=time.monotonic();json.loads(raw);times.append(time.monotonic()-t)
 bm=json.loads((OUT/'baseline_metrics.json').read_text());result={'stage':'A_ONLY','ready_for_stage_b_deployment':False,'stage_b_blockers':['Unlocated population/working origins','Point-level OD not implemented','Parts/POI/official site joins and capacity sensitivity pending','New allocation not tested in-game'],'authoritative_controls':len(checks),'all_authoritative_controls_exact_including_unlocated':all(x['residual']==0 for x in checks),'max_authoritative_control_residual':max(abs(x['residual'])for x in checks),'allocated_plus_unlocated_population':int(pop.sum()),'working_origins_including_unlocated':int(home.sum()),'point_jobs_total':sum(regjobs.values()),'regional_origins_with_ledger_match':dict(reghome)=={n:int(v)for n,v in zip(base['names'],base['od'].sum(1))},'regional_jobs_match':dict(regjobs)=={n:int(v)for n,v in zip(base['names'],base['od'].sum(0))},'outside_map_bbox_points':int(np.sum((loc[:,0]<106.3)|(loc[:,0]>107.35)|(loc[:,1]<-6.85)|(loc[:,1]>-5.9))),'unique_anchor_ids':len(set(p['id']for p in points))==len(points),'unique_anchor_osm_ids':len(ids)==len(points),'own_footprint_matches':matched,'outside_own_admin_ids':adminbad,'mapped_mask_hits_proposal':maskhits,'outside_own_footprint_ids':bad,'packaged_water_hits_proposal':int(sea.sum()),'packaged_water_hits_baseline':{'points':int(bsea.sum()),'jobs':int(base['jobs'][bsea].sum()),'residents':int(base['home'][bsea].sum())},'baseline_tracked_files_checked':len(oldhash),'production_tracked_files_changed':changed,'proposed_allocation_json_bytes':len(raw),'proposed_allocation_gzip_bytes':(OUT/'proposed_allocations.json.gz').stat().st_size,'allocation_json_parse_seconds_three_runs':times,'engine_format_assessment':'Point coordinates and integer counts can use existing points/pops schema. Allocation contains metadata and is NOT a loadable engine demand asset. Micro OD and in-game verification deferred to approved Stage B.','validity_scope':'Mapped-mask checks only; not proof of complete real-world geographic validity.'};dump('validation.json',result);print(json.dumps(result,indent=2));assert not changed and not bad and matched==len(points);assert result['all_authoritative_controls_exact_including_unlocated'];assert result['regional_origins_with_ledger_match']and result['regional_jobs_match'];assert not sea.any() and not adminbad and not any(maskhits.values())
