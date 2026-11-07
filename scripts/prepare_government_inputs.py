"""Spatial disaggregation of official local-government population controls.
WorldPop is used ONLY to distribute totals below the published administrative level.
"""
from pathlib import Path
import json,gzip,re,sys,collections,math
import numpy as np,rasterio,shapely
from shapely.geometry import shape,box,Point
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1]
GOV=ROOT/'sources/government'
def norm(s):return re.sub('[^A-Z0-9]','',str(s).upper())
def region_name(p):
 n=p['WADMKK'].upper()
 if 'JAKARTA' in n:return 'Kota Jakarta '+n.split('JAKARTA ')[-1].title()
 if n.startswith('KOTA '):return 'Kota '+n[5:].title()
 return n.replace('KABUPATEN ','').title()
def main(boundaries,raster):
 cfg=json.loads((ROOT/'config.json').read_text());old=json.load(gzip.open(ROOT/'assets/JKT/calibration_inputs.json.gz','rt'))
 names=set(old['population_in_map']);allowed={'31.71','31.72','31.73','31.74','31.75','32.01','32.16','32.71','32.75','32.76','36.03','36.71','36.74'}
 features=[f for f in json.load(open(boundaries))['features'] if f['properties']['KDPKAB'] in allowed and f['properties'].get('KDEPUM')]
 regs=[region_name(f['properties']) for f in features];assert set(regs)==names,(set(regs),names)
 geometries=shapely.make_valid([shape(f['geometry']) for f in features]);tree=shapely.STRtree(geometries)
 # Source-level matching uses admin codes when supplied; name keys are checked for uniqueness.
 bycode={norm(f['properties']['KDEPUM']):i for i,f in enumerate(features)}
 byname={(regs[i],norm(f['properties']['WADMKC']),norm(f['properties']['NAMOBJ'])):i for i,f in enumerate(features)}
 controls=json.loads((GOV/'population_controls.json').read_text());direct={};district={};unmatched=[]
 for c in controls:
  key=(c['region'],norm(c['kecamatan']))
  if c['kelurahan']:
   i=bycode.get(norm(c['code'])) if c['code'] else byname.get((*key,norm(c['kelurahan'])))
   if i is None:unmatched.append(c)
   else:direct[i]=c
  else:district[key]=c
 if unmatched:
  (GOV/'unmatched_controls.json').write_text(json.dumps(unmatched,indent=2));raise ValueError(f'{len(unmatched)} unmatched official villages; resolve before generation')
 project=Transformer.from_crs(4326,32748,always_xy=True).transform;inverse=Transformer.from_crs(32748,4326,always_xy=True).transform
 cells=collections.defaultdict(lambda:[0.,0.,0.,0.,0.,0.])
 with rasterio.open(raster) as src:
  win=rasterio.windows.from_bounds(*cfg['bbox'],src.transform).round_offsets().round_lengths();a=src.read(1,window=win);tr=src.window_transform(win)
  rr,cc=np.where(np.isfinite(a)&(a>0));xx,yy=rasterio.transform.xy(tr,rr,cc);xx=np.array(xx);yy=np.array(yy);values=a[rr,cc]
  pairs=tree.query(shapely.points(xx,yy),predicate='within');seen=set();matched=0.
  px,py=project(xx,yy)
  for pixel,village in zip(*pairs):
   pixel=int(pixel);village=int(village)
   if pixel in seen:continue
   seen.add(pixel);v=float(values[pixel]);x=float(px[pixel]);y=float(py[pixel]);k=(int(x//500),int(y//500),village);c=cells[k];c[0]+=v;c[1]+=v*x;c[2]+=v*y;matched+=v
 print('Village geometry / raster assignment',len(features),len(cells),matched,flush=True)
 # Reuse packaged land-use area weights, assigning their 500m representative points to official villages.
 for c in old['cells']:
  lon,lat=c['location'];ids=tree.query(Point(lon,lat),predicate='within')
  if len(ids)==0:continue
  village=int(ids[0]);x,y=project(lon,lat);cell=cells[(int(x//500),int(y//500),village)];cell[3]+=c['industrial_m2'];cell[4]+=c['commercial_m2']
 # Official Bekasi industry locations are not assigned worker counts. They supply an establishment-count weight.
 sites=json.load(gzip.open(GOV/'industrial_sites.geojson.gz','rt'));site_seen=set();site_matched=0
 for f in sites['features']:
  lon,lat=f['geometry']['coordinates'][:2];key=(round(lon,5),round(lat,5))
  if key in site_seen:continue
  site_seen.add(key);ids=tree.query(Point(lon,lat),predicate='within')
  if len(ids)==0:continue
  village=int(ids[0]);x,y=project(lon,lat);cells[(int(x//500),int(y//500),village)][5]+=1;site_matched+=1
 # Guarantee a record for each official village; tiny/zero-raster villages use a representative point.
 assigned={k[2] for k in cells}
 for i,g in enumerate(geometries):
  if i not in assigned:
   lon,lat=g.representative_point().coords[0];w,s,e,n=cfg['bbox']
   if not(w<=lon<=e and s<=lat<=n):continue
   x,y=project(lon,lat);cells[(int(x//500),int(y//500),i)]=[0.,0.,0.,0.,0.,0.]
 vmass=collections.Counter()
 for (gx,gy,i),c in cells.items():vmass[i]+=c[0]
 district_mass=collections.Counter()
 for i,f in enumerate(features):district_mass[(regs[i],norm(f['properties']['WADMKC']))]+=vmass[i]
 villages=[];targets={}
 for i,f in enumerate(features):
  p=f['properties'];key=(regs[i],norm(p['WADMKC']));control=direct.get(i) or district.get(key)
  if control is None:raise ValueError(f'Missing official population control for {key}')
  if i in direct:target=control['population'];level='observed_kelurahan'
  else:
   mass=district_mass[key];assert mass>0,key;target=control['population']*vmass[i]/mass;level='estimated_from_kecamatan'
  targets[i]=target
  villages.append({'id':p['KDEPUM'],'region':regs[i],'kecamatan':p['WADMKC'],'kelurahan':p['NAMOBJ'],'population':target,'population_status':level,'year':control['year'],'source':control['source'],'reported_working_residents':control['reported_working_residents'] if i in direct else (control['reported_working_residents']*target/control['population'] if control['reported_working_residents'] is not None else None)})
 records=[]
 for (gx,gy,i),c in sorted(cells.items()):
  g=geometries[i];x,y=(c[1]/c[0],c[2]/c[0]) if c[0]>0 else ((gx+.5)*500,(gy+.5)*500);lon,lat=inverse(x,y)
  if not g.covers(Point(lon,lat)):lon,lat=g.intersection(box(*cfg['bbox'])).representative_point().coords[0]
  w,s,e,n=cfg['bbox']
  if not(w<=lon<=e and s<=lat<=n):continue
  pop=targets[i]*c[0]/vmass[i] if vmass[i]>0 else targets[i]
  records.append({'location':[round(lon,6),round(lat,6)],'region':regs[i],'village':i,'population':pop,'industrial_m2':c[3],'commercial_m2':c[4],'official_industry_sites':c[5]})
 # Every direct village and kecamatan population must survive the disaggregation exactly.
 totals=collections.Counter();vtotal=collections.Counter()
 for c in records:totals[(c['region'],norm(villages[c['village']]['kecamatan']))]+=c['population'];vtotal[c['village']]+=c['population']
 for i,c in direct.items():assert abs(vtotal[i]-c['population'])<.01,(i,vtotal[i],c['population'])
 for key,c in district.items():assert abs(totals[key]-c['population'])<.01,(key,totals[key],c['population'])
 out={'version':3,'cells':records,'villages':villages,'official_controls':len(controls),'official_sites_matched_unique_coordinates':site_matched,'population_total':sum(c['population'] for c in records),'source_level_checks_passed':True}
 with gzip.open(ROOT/'assets/JKT/government_inputs.json.gz','wt') as f:json.dump(out,f,separators=(',',':'))
 # Keep only selected simplified official boundaries, compressed; no national geometry in package.
 with gzip.open(GOV/'village_boundaries.geojson.gz','wt') as f:json.dump({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'code':f['properties']['KDEPUM'],'region':regs[i],'kecamatan':f['properties']['WADMKC'],'kelurahan':f['properties']['NAMOBJ']},'geometry':shapely.geometry.mapping(geometries[i])} for i,f in enumerate(features)]},f,separators=(',',':'))
 print('Prepared',len(records),'cells',len(villages),'villages; population',out['population_total'],flush=True)
if __name__=='__main__':main(*sys.argv[1:])
