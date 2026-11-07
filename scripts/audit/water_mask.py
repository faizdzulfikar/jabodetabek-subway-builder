"""Decode existing packaged water, including ocean polygons, into scratch."""
from baseline import *
import math,shapely,sys
from pmtiles.reader import Reader,MmapSource
import mapbox_vector_tile

def water_geometries():
 result=[];w,s,e,n=106.3,-6.85,107.35,-5.9;z=12;nn=2**z;world=20037508.342789244;merc=Transformer.from_crs(3857,4326,always_xy=True).transform
 ty=lambda lat:int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*nn)
 with (ROOT/'assets/JKT.pmtiles').open('rb') as f:
  reader=Reader(MmapSource(f))
  for tx in range(int((w+180)/360*nn),int((e+180)/360*nn)+1):
   for yt in range(ty(n),ty(s)+1):
    raw=reader.get(z,tx,yt)
    if not raw:continue
    tile=mapbox_vector_tile.decode(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)
    if 'water' not in tile:continue
    extent=tile['water']['extent']
    def convert(x,y):return merc((tx+np.asarray(x)/extent)/nn*2*world-world,world-(yt+1-np.asarray(y)/extent)/nn*2*world)
    for feat in tile['water']['features']:
     g=shapely.geometry.shape(feat['geometry'])
     if g.geom_type in ['Polygon','MultiPolygon']:result.append(shapely.make_valid(shapely.transform(g,convert,interleaved=False)))
 return result
if __name__=='__main__':
 gs=water_geometries();Path(sys.argv[1]).write_bytes(shapely.to_wkb(shapely.union_all(gs)));print('water polygons',len(gs))
