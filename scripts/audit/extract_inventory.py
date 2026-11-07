"""Stage-A only: stream a COMPLETE OSM extract into scratch SQLite, never game assets.
Usage: python extract_inventory.py ACTIVITY.osm.pbf SCRATCH.sqlite
"""
import sys,sqlite3,json,zlib,time
from pathlib import Path
import osmium,numpy as np,shapely
from pyproj import Transformer
class Extract(osmium.SimpleHandler):
 def __init__(self,path):
  super().__init__();self.db=sqlite3.connect(path);self.db.execute('PRAGMA journal_mode=OFF');self.db.execute('PRAGMA synchronous=OFF')
  self.db.execute('CREATE TABLE IF NOT EXISTS buildings(id TEXT,lon REAL,lat REAL,area REAL,tags TEXT,geometry BLOB)');self.db.execute('CREATE TABLE IF NOT EXISTS context(id TEXT,tags TEXT,geometry BLOB)');self.db.execute('CREATE TABLE IF NOT EXISTS pois(id INTEGER,lon REAL,lat REAL,tags TEXT)');self.wkt=osmium.geom.WKBFactory();self.batch=[];self.count=0;self.errors=0;self.started=time.monotonic();self.proj=Transformer.from_crs(4326,32748,always_xy=True).transform
 def flush(self):
  if not self.batch:return
  gs=shapely.from_wkb([b[2] for b in self.batch]); gs=shapely.make_valid(gs);ps=shapely.point_on_surface(gs);pg=shapely.transform(gs,self.proj,interleaved=False);areas=shapely.area(pg);out=[]
  for (id,tags,wkb),g,p,a in zip(self.batch,gs,ps,areas):
   if not g.is_empty and a>=10 and np.isfinite(a):out.append((id,float(p.x),float(p.y),float(a),tags,zlib.compress(shapely.to_wkb(g),1)))
  self.db.executemany('INSERT INTO buildings VALUES(?,?,?,?,?,?)',out);self.count+=len(out);self.db.commit();self.batch.clear()
  if self.count%100000<5000:print(json.dumps({'buildings':self.count,'seconds':round(time.monotonic()-self.started)}),flush=True)
 def area(self,a):
  tags=dict(a.tags);building=tags.get('building') not in [None,'no'];part='building:part' in tags
  context=any(k in tags for k in ['landuse','natural','leisure','aeroway','amenity','office','shop','tourism'])
  if not(building or part or context):return
  try:
   wkb=bytes.fromhex(self.wkt.create_multipolygon(a));id=('w' if a.from_way() else 'r')+str(a.orig_id());t=json.dumps(tags,separators=(',',':'))
   if building and not part:
    self.batch.append((id,t,wkb))
    if len(self.batch)>=5000:self.flush()
   if context or part:self.db.execute('INSERT INTO context VALUES(?,?,?)',(id,t,zlib.compress(wkb,1)))
  except (RuntimeError,ValueError):self.errors+=1
 def node(self,n):
  tags=dict(n.tags)
  if any(k in tags for k in ['amenity','office','shop','tourism']):
   self.db.execute('INSERT INTO pois VALUES(?,?,?,?)',(n.id,n.location.lon,n.location.lat,json.dumps(tags,separators=(',',':'))))
 def finish(self):
  self.flush();self.db.commit();stats={'buildings':self.count,'geometry_errors':self.errors,'seconds':time.monotonic()-self.started,'context':self.db.execute('SELECT count(*) FROM context').fetchone()[0],'pois':self.db.execute('SELECT count(*) FROM pois').fetchone()[0]};self.db.close();return stats
if __name__=='__main__':
 target=Path(sys.argv[2]);assert not target.exists(),'Refuse to append to an existing inventory';e=Extract(target);e.apply_file(sys.argv[1],locations=True,idx='flex_mem');stats=e.finish();target.with_suffix('.stats.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats),flush=True)
