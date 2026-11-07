"""Aggregate WorldPop and existing OSM land-use tiles; no national raster is packaged."""
import sys,json,gzip,math
from pathlib import Path
import numpy as np, rasterio, shapely
from shapely.geometry import shape,box
from shapely.ops import transform
from pyproj import Transformer
from pmtiles.reader import Reader,MmapSource
import mapbox_vector_tile
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config.json').read_text())
def main(raster,boundaries):
 project=Transformer.from_crs(4326,32748,always_xy=True).transform
 inverse=Transformer.from_crs(32748,4326,always_xy=True).transform
 merc=Transformer.from_crs(3857,32748,always_xy=True).transform
 names=['Kota Jakarta Selatan','Kota Jakarta Timur','Kota Jakarta Pusat','Kota Jakarta Barat','Kota Jakarta Utara','Kota Tangerang','Tangerang','Kota Tangerang Selatan','Kota Depok','Kota Bogor','Bogor','Kota Bekasi','Bekasi']
 regions={f['properties']['shapeName']:shape(f['geometry']) for f in json.load(open(boundaries))['features'] if f['properties']['shapeName'] in names}
 assert len(regions)==13
 bbox=box(*[CFG['bbox'][i] for i in [0,1,2,3]])
 cells={}; full={}; clipped={}
 with rasterio.open(raster) as src:
  for region,g in regions.items():
   win=rasterio.windows.from_bounds(*g.bounds,src.transform).round_offsets().round_lengths()
   a=src.read(1,window=win); tr=src.window_transform(win)
   rr,cc=np.where(np.isfinite(a)&(a>0)); xx,yy=rasterio.transform.xy(tr,rr,cc)
   xx=np.array(xx);yy=np.array(yy);vv=a[rr,cc].astype(float)
   mask=shapely.contains_xy(g,xx,yy); xx=xx[mask];yy=yy[mask];vv=vv[mask]
   full[region]=float(vv.sum())
   w,s,e,n=CFG['bbox']; mask=(xx>=w)&(xx<=e)&(yy>=s)&(yy<=n)
   xx=xx[mask];yy=yy[mask];vv=vv[mask]; clipped[region]=float(vv.sum())
   x,y=project(xx,yy)
   for gx,gy,v in zip(np.floor(np.array(x)/500).astype(int),np.floor(np.array(y)/500).astype(int),vv):
    key=(int(gx),int(gy),region);cells[key]=cells.get(key,0.)+v
 print('WorldPop population within map',sum(clipped.values()),flush=True)
 # Decode land-use polygons already packaged in the base map, preserving their spatial extent.
 layers={'industrial':[],'commercial':[]}
 w,s,e,n=CFG['bbox'];z=12;nn=2**z; world=20037508.342789244
 ty=lambda lat:int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*nn)
 with (ROOT/'assets/JKT.pmtiles').open('rb') as f:
  reader=Reader(MmapSource(f))
  for tx in range(int((w+180)/360*nn),int((e+180)/360*nn)+1):
   for y in range(ty(n),ty(s)+1):
    raw=reader.get(z,tx,y)
    if not raw:continue
    tile=mapbox_vector_tile.decode(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)
    for layer,target in [('industrial','industrial'),('commercial','commercial'),('hospital','commercial'),('university','commercial')]:
     if layer not in tile:continue
     extent=tile[layer]['extent']
     def convert(x,y,z=None):return merc((tx+np.asarray(x)/extent)/nn*2*world-world,world-(y_tile+1-np.asarray(y)/extent)/nn*2*world)
     y_tile=y
     for feat in tile[layer]['features']:
      geom=shape(feat['geometry'])
      if geom.geom_type not in ['Polygon','MultiPolygon']:continue
      g=transform(convert,geom)
      if not g.is_valid:g=shapely.make_valid(g)
      layers[target].append(g)
 print('Land-use polygons', {k:len(v) for k,v in layers.items()},flush=True)
 # Also add employment-only cells, so industry is not forced into residential locations.
 projected_regions={k:transform(project,g.intersection(bbox)) for k,g in regions.items()}
 for geoms in layers.values():
  for g in geoms:
   a,b,c,d=g.bounds
   for gx in range(math.floor(a/500),math.floor(c/500)+1):
    for gy in range(math.floor(b/500),math.floor(d/500)+1):
     cell=box(gx*500,gy*500,(gx+1)*500,(gy+1)*500)
     if not g.intersects(cell):continue
     for region,rg in projected_regions.items():
      if rg.intersects(cell):cells.setdefault((gx,gy,region),0.)
 keys=sorted(cells); polygons=[box(x*500,y*500,(x+1)*500,(y+1)*500).intersection(projected_regions[r]) for x,y,r in keys]
 areas={}
 for kind,geoms in layers.items():
  union=shapely.union_all(geoms); areas[kind]=shapely.area(shapely.intersection(polygons,union))
 records=[]
 for i,((x,y,r),g) in enumerate(zip(keys,polygons)):
  if g.is_empty:continue
  p=g.representative_point();lon,lat=inverse(p.x,p.y)
  records.append({'location':[round(lon,6),round(lat,6)],'region':r,'population':round(cells[(x,y,r)],5),'industrial_m2':round(float(areas['industrial'][i]),2),'commercial_m2':round(float(areas['commercial'][i]),2)})
 out={'cells':records,'population_full_regions':full,'population_in_map':clipped,'sources':{'population':'WorldPop R2025A v1 constrained 2025 100m, DOI 10.5258/SOTON/WP00839','boundaries':'geoBoundaries IDN ADM2 2020, CC BY 3.0 IGO','landuse':'OSM geometry from packaged JKT.pmtiles'}}
 with gzip.open(ROOT/'assets/JKT/calibration_inputs.json.gz','wt') as f:json.dump(out,f,separators=(',',':'))
 print('Prepared cells',len(records),flush=True)
if __name__=='__main__':main(*sys.argv[1:])
