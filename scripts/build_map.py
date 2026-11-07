"""Build with the checked-out Depot; CLI paths are supplied by the caller.

DEPOT_SOURCE points to Depot's src directory. JAVA_OSM_PBF is the source PBF.
MAP_BUILD_WORK holds intermediates, keeping user-facing files separate.
"""
import gzip
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text())
WORK = Path(os.environ['MAP_BUILD_WORK']).resolve()
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.environ['DEPOT_SOURCE'])
from depot.maps import MapGen
import stream_buildings


class LimitedMapGen(MapGen):
    def _building_sources(self):
        clean,_=stream_buildings.prepare(self.buildings_geojson,self.city_dir,CONFIG['building_filter_m2'])
        return stream_buildings.select_light(clean,Path(self.city_dir)/'light',
                    CONFIG['building_limit'],CONFIG['building_sample_grid_m'])

    def process_buildings(self):
        clean, _ = self._building_sources()
        stream_buildings.encode(clean, Path(self.city_dir) / 'light/building-stats.json',
                                Path(self.city_dir) / 'buildings_index.bin')

    def _generate_building_tiles(self):
        clean, foundations = self._building_sources()
        self.buildings_mbtiles = str(Path(self.city_dir) / 'buildings.mbtiles')
        self.buildings_foundations_mbtiles = str(Path(self.city_dir) / 'buildings-foundations.mbtiles')
        for path, output, layer, attribute in [
            (clean, self.buildings_mbtiles, 'buildings', 'height'),
            (foundations, self.buildings_foundations_mbtiles, 'foundations', 'foundationDepth')]:
            self._run_command(['tippecanoe','-o',output,'--layer='+layer,'--include='+attribute,
                               '--no-tile-size-limit','-Z12',f'-z{self.maxzoom}',str(path),'--force'])

    def _run_command(self, cmd):
        # Upstream hardcodes a 16 GB Java heap. This host has 16 GB total RAM.
        if isinstance(cmd, list):
            cmd = ['-Xmx5g' if part == '-Xmx16g' else part for part in cmd]
            if cmd and cmd[0] == 'java':
                cmd.insert(1, '-Djava.net.preferIPv4Stack=true')
                cmd += ['--threads=2', '--nodemap-type=sortedtable', '--nodemap-storage=mmap',
                        f'--download-dir={WORK / "planetiler-sources"}',
                        f'--tmpdir={WORK / "planetiler-tmp"}']
        return super()._run_command(cmd)


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    city_dir = WORK / CONFIG['code']
    city_dir.mkdir(exist_ok=True)
    source = Path(os.environ['JAVA_OSM_PBF']).resolve()
    clipped = city_dir / 'jkt.osm.pbf'
    if not clipped.exists():
        run('osmium', 'extract', '--strategy=complete_ways', '--bbox',
            ','.join(map(str, CONFIG['bbox'])), source, '-o', clipped, '--overwrite')
    buildings = city_dir / 'osm-buildings.geojson'
    if not buildings.exists():
        pbf = city_dir / 'osm-buildings.pbf'
        run('osmium', 'tags-filter', clipped, 'wr/building', '-o', pbf, '--overwrite')
        run('osmium', 'export', pbf, '--geometry-types=polygon', '--add-unique-id=type_id',
            '-o', buildings, '--overwrite')
    # Streaming normalization avoids GDAL's full in-memory feature table.
    normalized = city_dir / 'osm-buildings-normalized.geojson'
    if not normalized.exists():
        import ijson
        tmp = normalized.with_suffix('.tmp')
        count = 0
        with buildings.open('rb') as inp, tmp.open('w') as out:
            out.write('{"type":"FeatureCollection","features":[')
            for feature in ijson.items(inp, 'features.item', use_float=True):
                geometry = feature.get('geometry') or {}
                rings = geometry.get('coordinates', [])
                polygons = [rings] if geometry.get('type') == 'Polygon' else rings
                # Cheap conservative prefilter; Depot applies the accurate UTM
                # 40 m² threshold later. Translating coordinates avoids cancellation.
                area = 0.
                for polygon in polygons:
                    for index, ring in enumerate(polygon):
                        if len(ring) < 4:
                            continue
                        x0, y0 = ring[0]
                        twice = sum((a[0]-x0)*(b[1]-y0) - (b[0]-x0)*(a[1]-y0)
                                    for a,b in zip(ring, ring[1:]))
                        area += (1 if index == 0 else -1) * abs(twice) / 2 * 111000**2 * math.cos(math.radians(y0))
                if area < CONFIG['building_filter_m2'] * .97:
                    continue
                props = feature.get('properties', {})
                try:
                    height = float(str(props.get('height', '')).split()[0])
                except (ValueError, IndexError):
                    try:
                        height = float(props.get('building:levels', 0)) * 3
                    except (ValueError, TypeError):
                        height = 4
                props = {key: props[key] for key in ['name', 'building'] if key in props}
                props['height'] = max(3, min(height or 4, 350))
                feature['properties'] = props
                if count:
                    out.write(',')
                json.dump(feature, out, separators=(',', ':'))
                count += 1
            out.write(']}')
        tmp.replace(normalized)
        print(f'Normalized {count:,} OSM building footprints.', flush=True)
    obj = LimitedMapGen(
        city=CONFIG['code'], bbox=CONFIG['bbox'], osmpbf=str(source), outputdir=str(WORK),
        buildings_geojson=str(normalized), building_index_filter_size=CONFIG['building_filter_m2'],
        building_index_simplification=1, building_tile_simplification=1,
        create_building_foundations=True, create_ocean_foundations=False,
        maxzoom=CONFIG['maxzoom'], ncores=2, RAM=3, cleanup_files=True,
        cities=['city', 'town'], suburbs=['suburb', 'village'],
        neighborhoods=['neighbourhood', 'quarter'], verb=True)
    # extract_base_data's ogr2ogr export is unused by the subsequent stages.
    # The equivalent complete-ways OSM extraction has already been performed.
    if not (city_dir / 'buildings_index.bin.gz').exists():
        obj.process_buildings()
    if not (city_dir / 'roads.geojson').exists():
        obj.process_roads_and_aeroways()
    if not (city_dir / 'JKT-nolabels.pmtiles').exists():
        obj.generate_pmtiles()
    if not (city_dir / 'JKT.pmtiles').exists():
        obj.add_labels()
    asset_dir = ROOT / 'assets'
    data_dir = asset_dir / CONFIG['code']
    data_dir.mkdir(exist_ok=True)
    for name in ['JKT.pmtiles', 'JKT_foundations.pmtiles']:
        shutil.copy2(city_dir / name, asset_dir / name)
    shutil.copy2(city_dir / 'buildings_index.bin.gz', data_dir / 'buildings_index.bin.gz')
    for name in ['roads.geojson', 'runways_taxiways.geojson']:
        with open(city_dir / name, 'rb') as inp, gzip.open(data_dir / (name + '.gz'), 'wb') as out:
            shutil.copyfileobj(inp, out)
    print('Map assets packaged. Generate and validate demand next.', flush=True)


if __name__ == '__main__':
    main()
