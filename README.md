# Jabodetabek — experimental Subway Builder city

Target: Subway Builder 1.7.2. City code: `JKT`.

For data review, start with the [data index](DATA_GUIDE.md).

Extent: a rectangle `[106.30, -6.85, 107.35, -5.90]` covering mainland Jakarta,
Bogor, Depok, Tangerang, and Bekasi, including peripheral territory. This is not an
administrative boundary extract. Offshore Kepulauan Seribu is outside the extent.
The map starts empty, for building your own network.

## Status

Installed and verified in game: basemap and roads display, and the Demand panel
reads12,646,700 modelled working trip-makers. See `BUILD_STATUS.json` for checks. Keep the
local tile server running while playing.

## Data and limitations

- Real OpenStreetMap geometry for roads, sampled buildings, land use, water, airports,
  and place labels. Java source extract timestamp: 2026-11-05T21:23:02Z.
- **Lightweight build: at most 30,000 representative building footprints**, sampled
  across 500 m cells with some tall landmarks retained. Buildings not selected are
  omitted from both rendering and collision detection. The full building database
  is not part of the playable package. Demand still uses the original building
  density, in a small aggregated file.
- Buildings under 40 square metres are filtered before sampling.
  Missing heights default to 4 m or 3 m per mapped floor. Foundation depth uses a
  bounded height/footprint-width heuristic, not geological surveys or engineering
  foundation measurements. The binary building encoder is byte-compatibility-tested
  against Depot on a sample; preparation streams features to limit peak memory.
- **Demand v3:** official local-government population controls cover all13 mainland
  city/regency areas, at kecamatan or kelurahan level. Source years are2025, except
  Kabupaten Bogor2022. They total32,615,007 registered residents across mixed periods.
  This is not presented as a same-date population census.
- 317 kelurahan have direct population controls;1,185 other villages are estimated
  within official kecamatan totals using WorldPop100m weights and BIG2026 boundaries.
  Source-level totals are preserved exactly before rounding the display audit.
- In-game Residents are12,646,700 modelled working trip-makers, not all inhabitants.
  SIAK working-resident weights are used where available; missing participation is
  estimated. Workplace locations use official business proxies where available and
  OSM land-use elsewhere. Comprehensive current workplace counts are unavailable.
  Regional workplace shares still use historical JUTPI2018, with the DKI split updated
  by registered Jamsostek2024 membership. Trips remain synthetic.
- See [government data coverage](sources/government/COVERAGE.md), the source manifest,
  quality issues and kelurahan audit in `sources/government/` for exact distinctions.
- Driving times are estimates (detour factor and assumed speed), not routed road
  journeys or measured traffic. No measured mode-share validation has been done.
- Ocean-depth collision restrictions are unavailable in this first build.
- Maximum stored zoom is 13; the game overzooms above it.
- This project provides a city map. It does not yet build a 10-line metro network.

## Playing

1. Ensure all assets pass `python3 scripts/validate.py`.
2. Run `Start Map Server.command` (or `python3 scripts/serve.py`) and keep it open.
   Requires the `pmtiles` CLI (`brew install pmtiles` on this Mac).
3. Run `python3 scripts/install.py`. This links the mod into
   `~/Library/Application Support/metro-maker4/mods/JKT` and mounts its data at
   `~/Library/Application Support/metro-maker4/cities/data/JKT`. Both links are
   needed for the native data loader in game version 1.7.2. Keep this package in place.
4. Reload/restart Subway Builder, enable **Jabodetabek — Experimental Map** in
   Settings → Mods, and select Jabodetabek under Modded when starting a new game.

The servers listen only on `127.0.0.1`, ports 18765 (packaged data) and 18766 (tiles).
Stop them with Ctrl+C. No public hosting or uploads are required.

## Rebuilding

Sources: `scripts/build_map.py`, `scripts/generate_demand.py`, `config.json`.
The build uses Depot plus Osmium, mapshaper, Java/Planetiler, Tippecanoe, and PMTiles.
The local build uses a Python virtual environment and a workspace-local mapshaper.
Depot is referenced externally rather than bundled.

Example environment (adapt paths to your checkout):

```sh
export DEPOT_SOURCE=/path/to/depot/src
export JAVA_OSM_PBF=/path/to/java-latest.osm.pbf
export MAP_BUILD_WORK=/path/to/intermediates
export PATH=/path/to/mapshaper/node_modules/.bin:/path/to/planetiler-directory:$PATH
python scripts/build_map.py
python scripts/generate_government_demand.py
python scripts/validate.py
```

The wrapper limits Planetiler to a 5 GB Java heap and two threads during the one-time
data preparation. This is not a requirement of the resulting lightweight map server.
`stream_buildings.py` replaces Depot's in-memory building preparation and encoding
for this large region. Rebuild demand v3 from included `assets/JKT/government_inputs.json.gz` with
`generate_government_demand.py` (NumPy required). To re-aggregate government sources, use
`prepare_government_inputs.py BIG_VILLAGES.geojson WORLDPOP_CROP.tif`; keep the included
original `calibration_inputs.json.gz` for OSM land-use weights. This additionally
requires Rasterio, Shapely, PyProj, pmtiles, and mapbox-vector-tile.

## Sources and attribution

- Map data © OpenStreetMap contributors, ODbL 1.0:
  https://www.openstreetmap.org/copyright
- Geofabrik Java extract:
  https://download.geofabrik.de/asia/indonesia/java.html
- Ocean polygon source mirror (2026-10-31 snapshot):
  https://ftp.fau.de/mirrors/openstreetmapdata.com-archive/2026-10-31/
- Depot map processing (GPL-3.0):
  https://github.com/Subway-Builder-Modded/depot
- Planetiler (Apache-2.0): https://github.com/onthegomap/planetiler
- Basemap tile schema/profile: © OpenMapTiles, CC BY 4.0:
  https://github.com/openmaptiles/openmaptiles/#license
- PMTiles: https://github.com/protomaps/go-pmtiles
- Subway Builder custom city API:
  https://www.subwaybuilder.com/docs/guides/custom-cities

Retain OpenStreetMap attribution when sharing the map and observe ODbL obligations
for the derived geographic database. Synthetic demand methodology is documented
in `assets/JKT/demand-method.json` after generation.

## Demand sources

- WorldPop population: https://doi.org/10.5258/SOTON/WP00839 (CC BY 4.0).
  Crop downloaded using https://api.worldpop.org/v3/raster, year 2025, 100m.
- JUTPI2 workplace estimates, Table39 printed page60:
  https://openjicareport.jica.go.jp/pdf/12356382.pdf
- BPS SE2016 DKI workplace split:
  https://jakarta.bps.go.id/id/statistics-table/2/OTQ5IzI%3D/banyaknya-tenaga-kerja-menurut-wilayah-dan-skala-usaha--provinsi-dki-jakarta-hasil-se2016-.html
- geoBoundaries ADM2 Indonesia, represented year2020, CC BY3.0IGO:
  https://www.geoboundaries.org/api/current/gbOpen/IDN/ADM2/

New demand is loaded when starting a new city. Existing saves may retain old demand.

Government source details and administrative audit: `sources/government/COVERAGE.md`.
