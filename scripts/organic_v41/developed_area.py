from pathlib import Path
import json,gzip,csv,numpy as np,shapely
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds,Window
from pyproj import Geod
r=Path('outputs/jabodetabek-mod');o=r/'docs/organic-v41';rows=list(csv.DictReader((o/'area_comparison.csv').open()));geo=json.load(gzip.open(o/'audit_boundaries.geojson.gz','rt'));geod=Geod(ellps='WGS84');byname={f['properties']['name']:shapely.geometry.shape(f['geometry'])for f in geo['features']}
# Internal10m raster used only to MEASURE historical developed evidence, never final coordinates.
with rasterio.open('work/organic-stage-b/worldcover2021_S09E105.tif')as ds:
 for row in rows:
  g=byname[row['name']];bounds=g.bounds
  if g.is_empty:count=0;ha=0
  else:
   win=from_bounds(*bounds,ds.transform).round_offsets().round_lengths();win=win.intersection(Window(0,0,ds.width,ds.height));a=ds.read(1,window=win);t=ds.window_transform(win);mask=geometry_mask([shapely.geometry.mapping(g)],a.shape,t,invert=True);count=int(np.sum((a==50)&mask));x,y=t*(a.shape[1]/2,a.shape[0]/2);dx=abs(t.a);dy=abs(t.e);m2=abs(geod.polygon_area_perimeter([x,x+dx,x+dx,x],[y,y,y+dy,y+dy])[0]);ha=count*m2/10000
  row['worldcover2021_builtup_proxy_ha']=round(ha,2);row['jobs_per_worldcover2021_builtup_ha_current']=round(int(row['jobs_current'])/ha,2)if ha else 0;row['jobs_per_worldcover2021_builtup_ha_proposed']=round(int(row['jobs_proposed'])/ha,2)if ha else 0;row['developed_evidence_warning']='2021 built-up class50 within mapped boundary; historical/incomplete, includes impervious uses; not verified2025 occupied industrial hectares. Existing developed_industrial_proxy_ha only subtracts natural masks from industrial landuse.'
with (o/'area_comparison.csv').open('w')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
print('Historical built-up denominator added for',len(rows),'geographic areas')
