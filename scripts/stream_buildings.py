"""Bounded-memory building prep and the documented SBBI v1 binary layout.

Stores typed-array sections in temporary files instead of retaining millions of
Python dictionaries. Layout interoperates with Depot / Subway Builder's encoder.
"""
from array import array
from collections import defaultdict
import gzip
import hashlib
import heapq
from itertools import islice
import json
import math
from pathlib import Path
import shutil
import struct
import ijson
import numpy as np
from pyproj import Transformer
import shapely
from shapely.geometry import shape, mapping


def select_light(source, destination, limit=30000, grid_m=500):
    """One spatially distributed sample per cell, then landmarks / extra samples.

    Keep only a small number of feature objects in memory, not the full source.
    Sampling and tie-breaking are deterministic for a given prepared source.
    """
    destination = Path(destination)
    destination.mkdir(exist_ok=True)
    stats_path = destination / 'building-stats.json'
    clean = destination / 'buildings-clean.geojsonl'
    foundations = destination / 'foundations-clean.geojsonl'
    if stats_path.exists():
        stats = json.loads(stats_path.read_text())
        if stats.get('sample_limit') == limit and stats.get('sample_grid_m') == grid_m:
            return clean, foundations
    cells = {}
    landmarks = []
    with open(source) as inp:
        for identifier,line in enumerate(inp):
            feature = json.loads(line)
            x,y = feature['geometry']['coordinates'][0][0]
            key = (math.floor(x*110600/grid_m),math.floor(y*111200/grid_m))
            score = int.from_bytes(hashlib.blake2b(str(identifier).encode(),digest_size=8).digest(),'little')
            items = cells.setdefault(key,[])
            candidate = (score,identifier,feature)
            if len(items)<2:
                items.append(candidate);items.sort(key=lambda a:a[0])
            elif score < items[-1][0]:
                items[-1]=candidate;items.sort(key=lambda a:a[0])
            height = feature['properties'].get('height',4)
            if height >= 30:
                item=(height,identifier,feature)
                if len(landmarks)<2000:
                    heapq.heappush(landmarks,item)
                elif item[:2]>landmarks[0][:2]:
                    heapq.heapreplace(landmarks,item)
    source_count = identifier+1
    selected = {}
    first = sorted((items[0] for items in cells.values()),key=lambda item:item[0])
    for score,identifier,feature in first[:limit]:
        selected[identifier]=feature
    for height,identifier,feature in sorted(landmarks,reverse=True):
        if len(selected)>=limit: break
        selected[identifier]=feature
    extras=sorted((items[1] for items in cells.values() if len(items)>1),key=lambda item:item[0])
    for score,identifier,feature in extras:
        if len(selected)>=limit: break
        selected[identifier]=feature
    bounds=[math.inf,math.inf,-math.inf,-math.inf]
    rings_count=coords_count=0
    maxdepth=0
    with clean.open('w') as out, foundations.open('w') as fo:
        for identifier,feature in sorted(selected.items()):
            rings=feature['geometry']['coordinates']
            flat=[p for ring in rings for p in ring]
            bounds=[min(bounds[0],min(p[0] for p in flat)),min(bounds[1],min(p[1] for p in flat)),
                    max(bounds[2],max(p[0] for p in flat)),max(bounds[3],max(p[1] for p in flat))]
            out.write(json.dumps(feature,separators=(',',':'))+'\n')
            depth=feature['properties']['foundationDepth']
            fo.write(json.dumps({'type':'Feature','geometry':feature['geometry'],
                                'properties':{'foundationDepth':depth}},separators=(',',':'))+'\n')
            rings_count+=len(rings);coords_count+=len(flat);maxdepth=max(maxdepth,depth)
    stats={'buildings':len(selected),'rings':rings_count,'coordinates':coords_count,
           'bounds':bounds,'max_foundation_depth':maxdepth,'sample_limit':limit,
           'sample_grid_m':grid_m,'source_features':source_count,
           'mode':'spatial sample plus up to 2000 tall landmarks; omitted buildings have no collision footprints'}
    stats_path.write_text(json.dumps(stats,indent=2))
    print(f'Light map selected {len(selected):,} building footprints.',flush=True)
    return clean,foundations


def prepare(source, destination, min_area=40):
    destination = Path(destination)
    clean = destination / 'buildings-clean.geojsonl'
    foundations = destination / 'foundations-clean.geojsonl'
    stats_path = destination / 'building-stats.json'
    if stats_path.exists() and clean.exists() and foundations.exists():
        return clean, foundations
    forward = Transformer.from_crs(4326, 32748, always_xy=True).transform
    reverse = Transformer.from_crs(32748, 4326, always_xy=True).transform
    count = rings_count = coords_count = 0
    bounds = [math.inf, math.inf, -math.inf, -math.inf]
    maximum_depth = 0
    with open(source, 'rb') as inp, clean.open('w') as out, foundations.open('w') as fo:
        iterator = ijson.items(inp, 'features.item', use_float=True)
        while batch := list(islice(iterator, 10000)):
            batch = [f for f in batch if f.get('geometry')]
            geoms = shapely.transform([shape(f['geometry']) for f in batch], forward, interleaved=False)
            geoms = shapely.make_valid(geoms)
            areas = shapely.area(geoms)
            geoms = shapely.simplify(geoms, 1, preserve_topology=True)
            geoms = shapely.transform(geoms, reverse, interleaved=False)
            for feature, geom, area in zip(batch, geoms, areas):
                if area < min_area or geom.is_empty:
                    continue
                if geom.geom_type == 'MultiPolygon':
                    geom = max(geom.geoms, key=lambda part: part.area)
                if geom.geom_type != 'Polygon':
                    continue
                # Round like game city pipelines, then recover exact rounded bounds.
                rings = [[[math.floor(x*100000+.5)/100000, math.floor(y*100000+.5)/100000]
                          for x,y,*_ in ring.coords]
                         for ring in [geom.exterior, *geom.interiors]]
                flat = [p for ring in rings for p in ring]
                west, south = min(p[0] for p in flat), min(p[1] for p in flat)
                east, north = max(p[0] for p in flat), max(p[1] for p in flat)
                if west >= east or south >= north:
                    continue
                height = float(feature.get('properties', {}).get('height', 4))
                width = max(1., min((east-west)*110600, (north-south)*111200))
                depth = max(1., min(60., .25 * height * (height/width)**.25))
                depth = round(depth, 3)
                geometry = {'type':'Polygon', 'coordinates':rings}
                out.write(json.dumps({'type':'Feature', 'geometry':geometry,
                          'properties':{'height':height, 'foundationDepth':depth}}, separators=(',',':'))+'\n')
                fo.write(json.dumps({'type':'Feature', 'geometry':geometry,
                         'properties':{'foundationDepth':depth}}, separators=(',',':'))+'\n')
                bounds = [min(bounds[0],west), min(bounds[1],south),
                          max(bounds[2],east), max(bounds[3],north)]
                count += 1
                rings_count += len(rings)
                coords_count += len(flat)
                maximum_depth = max(maximum_depth, depth)
            if count and count % 250000 < 10000:
                print(f'Prepared {count:,} building footprints...', flush=True)
    stats = {'buildings':count, 'rings':rings_count, 'coordinates':coords_count,
             'bounds':bounds, 'max_foundation_depth':maximum_depth}
    stats_path.write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats), flush=True)
    return clean, foundations


def encode(source, stats_path, output, constant_depth=None):
    stats = json.loads(Path(stats_path).read_text())
    count, ring_count, coord_count = [stats[key] for key in ['buildings','rings','coordinates']]
    west,south,east,north = stats['bounds']
    cell_size = .0009
    lon_cell = cell_size / math.cos(math.radians((south+north)/2))
    cols = math.ceil((east-west)/lon_cell)
    rows = math.ceil((north-south)/cell_size)
    temp = Path(output).parent / 'binary-sections'
    temp.mkdir(exist_ok=True)
    names = ['bounds','depths','building-rings','ring-coords','coords']
    files = {name:(temp/name).open('wb') for name in names}
    cells = defaultdict(lambda: array('I'))
    ring_cursor = coord_cursor = 0
    with open(source) as inp:
        for identifier,line in enumerate(inp):
            feature = json.loads(line)
            rings = feature['geometry']['coordinates']
            flat = [p for ring in rings for p in ring]
            minx,miny = min(p[0] for p in flat), min(p[1] for p in flat)
            maxx,maxy = max(p[0] for p in flat), max(p[1] for p in flat)
            files['bounds'].write(struct.pack('<4d',minx,miny,maxx,maxy))
            depth = constant_depth if constant_depth is not None else feature['properties']['foundationDepth']
            files['depths'].write(struct.pack('<f',depth))
            files['building-rings'].write(struct.pack('<I',ring_cursor))
            for ring in rings:
                files['ring-coords'].write(struct.pack('<I',coord_cursor))
                files['coords'].write(struct.pack('<'+'d'*len(ring)*2,*(v for p in ring for v in p)))
                ring_cursor += 1
                coord_cursor += len(ring)
            for row in range(max(0,math.floor((miny-south)/cell_size)),min(rows-1,math.floor((maxy-south)/cell_size))+1):
                for col in range(max(0,math.floor((minx-west)/lon_cell)),min(cols-1,math.floor((maxx-west)/lon_cell))+1):
                    cells[(row,col)].append(identifier)
    files['building-rings'].write(struct.pack('<I',ring_cursor))
    files['ring-coords'].write(struct.pack('<I',coord_cursor))
    for handle in files.values():
        handle.close()
    assert identifier+1 == count and ring_cursor == ring_count and coord_cursor == coord_count
    keys = sorted(cells)
    references = sum(len(value) for value in cells.values())
    maximum_depth = constant_depth if constant_depth is not None else stats['max_foundation_depth']
    header = struct.pack('<IBBHI'+'I'*7+'d'*6,
                         0x49424253,1,0,0,count,cols,rows,ring_count,coord_count,len(keys),references,0,
                         cell_size,maximum_depth,west,south,east,north)
    assert len(header) == 88
    with open(output,'wb') as out:
        out.write(header)
        for name in names:
            if name in ['building-rings','coords']:
                out.write(b'\0' * ((-out.tell()) % 8))
            with (temp/name).open('rb') as inp:
                shutil.copyfileobj(inp,out)
        starts = array('I',[0])
        cursor = 0
        for row in range(rows):
            while cursor < len(keys) and keys[cursor][0] == row:
                cursor += 1
            starts.append(cursor)
        out.write(struct.pack('<'+'I'*len(starts),*starts))
        for row,col in keys:
            out.write(struct.pack('<I',col))
        cursor = 0
        for key in keys:
            out.write(struct.pack('<I',cursor))
            cursor += len(cells[key])
        out.write(struct.pack('<I',cursor))
        for key in keys:
            values = cells[key]
            out.write(struct.pack('<'+'I'*len(values),*values))
    with open(output,'rb') as inp, gzip.open(str(output)+'.gz','wb',compresslevel=5) as out:
        shutil.copyfileobj(inp,out)
    shutil.rmtree(temp)
    print(f'Encoded {count:,} buildings in bounded memory.',flush=True)
