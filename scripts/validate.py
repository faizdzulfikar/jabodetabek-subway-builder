"""Fail on missing assets, inconsistent demand, or wrong binary formats."""
import gzip
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def main():
    assets = ROOT / 'assets'
    data = assets / 'JKT'
    for name in ['JKT.pmtiles', 'JKT_foundations.pmtiles']:
        with (assets / name).open('rb') as handle:
            assert handle.read(7) == b'PMTiles', f'Invalid PMTiles header: {name}'
    with gzip.open(data / 'buildings_index.bin.gz', 'rb') as handle:
        header = handle.read(88)
        assert struct.unpack_from('<I', header)[0] == 0x49424253, 'Invalid building magic'
        assert header[4] == 1, 'Unsupported building binary version'
        values = struct.unpack('<IBBHI'+'I'*7+'d'*6, header)
        buildings,cols,rows,rings,coords,cells,refs = values[4:11]
        assert buildings > 0 and cols > 0 and rows > 0
        expected = 88 + buildings*36
        expected += (-expected) % 8
        expected += (buildings+1)*4 + (rings+1)*4
        expected += (-expected) % 8
        expected += coords*16 + (rows+1)*4 + cells*4 + (cells+1)*4 + refs*4
        actual = 88
        while chunk := handle.read(8*1024*1024):
            actual += len(chunk)
        assert actual == expected, f'Truncated/inconsistent building index: {actual} vs {expected}'
    with gzip.open(data / 'demand_data.json.gz', 'rt') as handle:
        demand = json.load(handle)
    points = {p['id']: p for p in demand['points']}
    assert len(points) == len(demand['points']) and len(points) > 100
    west, south, east, north = json.loads((ROOT / 'config.json').read_text())['bbox']
    totals = {key: [0, 0, set()] for key in points}
    pop_ids = set()
    for pop in demand['pops']:
        assert pop['id'] not in pop_ids
        pop_ids.add(pop['id'])
        origin, destination = pop['residenceId'], pop['jobId']
        assert origin in points and destination in points and origin != destination
        assert pop['size'] > 0 and pop['drivingSeconds'] > 0 and pop['drivingDistance'] > 0
        totals[origin][0] += pop['size']
        totals[destination][1] += pop['size']
        totals[origin][2].add(pop['id'])
        totals[destination][2].add(pop['id'])
    for identifier, point in points.items():
        lon, lat = point['location']
        assert west <= lon <= east and south <= lat <= north
        residents, jobs, linked = totals[identifier]
        assert (point['residents'], point['jobs']) == (residents, jobs)
        assert set(point['popIds']) == linked and len(point['popIds']) == len(linked)
    road_counts = {}
    for name in ['roads.geojson.gz', 'runways_taxiways.geojson.gz']:
        with gzip.open(data / name, 'rt') as handle:
            collection = json.load(handle)
        assert collection['type'] == 'FeatureCollection'
        assert collection['features'], f'No features: {name}'
        road_counts[name] = len(collection['features'])
    print(json.dumps({'validation': 'passed', 'buildings':buildings, 'points': len(points), 'groups': len(pop_ids),
                      'commuters': sum(p['residents'] for p in points.values()),
                      **road_counts}, indent=2))


if __name__ == '__main__':
    main()
