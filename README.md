# Jabodetabek — experimental Subway Builder city

Target: Subway Builder 1.7.2. City code: `JKT`.

For data review, start with the [data index](DATA_GUIDE.md).

Extent: a rectangle `[106.30, -6.85, 107.35, -5.90]` covering mainland Jakarta,
Bogor, Depok, Tangerang, and Bekasi, including peripheral territory. This is not an
administrative boundary extract. Offshore Kepulauan Seribu is outside the extent.
The map starts empty, for building your own network.

## Status

Organic demand v4.1 S0+OD40 (mod 0.2.2) is installed and passed independent
spatial/statistical/schema gates. Verified in Subway Builder 1.7.2 on 8 November 2026:
fresh sandbox, Residents/Workers, point/OD details, pan/zoom and save/load.
Save: **Jabodetabek Organic v4.1 S0 OD40 QA**; older saves were not overwritten.
All population, village working-origin and regional job totals are unchanged.
See [v4.1 release report](docs/ORGANIC_V41_IMPLEMENTATION.md) and
[runtime evidence](docs/organic-v41-stage-b/runtime_verification.json).
Keep the local tile server running while playing. Workplaces and OD remain estimates.

## Data and limitations

- Real OpenStreetMap geometry for roads, sampled buildings, land use, water, airports,
  and place labels. Java source extract timestamp: 2026-11-05T21:23:02Z.
- **Lightweight build: at most 30,000 representative building footprints**, sampled
  across 500 m cells with some tall landmarks retained. Buildings not selected are
  omitted from both rendering and collision detection. The full building database
  is not part of the playable package. Organic demandv4 is allocated offline from the full OSM inventory,
  with115,929 building/parcel anchors and78,404 active engine points.
  The demand gzip is3.90MB; full raw buildings are not loaded by the game.
- Buildings under 40 square metres are filtered before sampling.
  Missing heights default to 4 m or 3 m per mapped floor. Foundation depth uses a
  bounded height/footprint-width heuristic, not geological surveys or engineering
  foundation measurements. The binary building encoder is byte-compatibility-tested
  against Depot on a sample; preparation streams features to limit peak memory.
- **Organic demandv4:** official local-government population controls cover all13 mainland
  city/regency areas, at kecamatan or kelurahan level. Source years are2025, except
  Kabupaten Bogor2022. They total32,615,007 registered residents across mixed periods.
  This is not presented as a same-date population census.
- 317 kelurahan have direct population controls;1,185 other villages are estimated
  within official kecamatan totals using WorldPop100m weights and BIG2026 boundaries.
  All446 source-level controls remain exact after integer allocation; no population is left unlocated.
- In-game Residents are12,646,700 modelled working trip-makers, not all inhabitants.
  SIAK working-resident weights are used where available; missing participation is
  estimated. Workplaces use building functions/floor-area priors, OSM land-use/POI context,
  and matched official industrial sites. Missing activity is an explicit
  unclassified neighborhood-work prior, not observed homeworking. Comprehensive current workplace counts are unavailable.
  Regional workplace shares still use historical JUTPI2018, with the DKI split updated
  by registered Jamsostek2024 membership. Trips remain synthetic; point/regional margins are exact. The reviewed
  cross-region scenario is40%, not an observed2026 commuting rate.
- Missing residential geometry uses validated road-accessible developed parcels
  from ESA WorldCover2021 built-up evidence. It is labelled historical fallback,
  not observed2026 building function. See [StageB results](docs/ORGANIC_DEMAND_STAGE_B.md)
  and [provenance](sources/organic/source_manifest.json).
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

Current organic demand is rebuilt by `scripts/organic/rebuild.py`, with an independent
release gate and repeat-generation SHA check. Full OSM SQLite inventory and the
WorldCover tile stay offline in scratch. See [StageB reproduction](docs/ORGANIC_DEMAND_STAGE_B.md)
and [StageA source preparation](docs/ORGANIC_DEMAND_CALIBRATION.md).

In this Codex workspace, run from the workspace directory above `outputs/`:

```sh
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/organic/rebuild.py
# Install the verified staged result when ready:
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/organic/rebuild.py --install
```

The default rebuild stages data without changing game assets. Installation resets
runtime-verification status: hot-reload/scan mods and repeat the documented game
checks. [Rollbackv3](docs/organic-stage-b/rollback-v3/manifest.json) preserves the prior
release. Do not run `generate_government_demand.py` forv4: it is the retainedv3
historical generator and would replace the current demand with the old method.

Map geometry can be rebuilt independently with `scripts/build_map.py`; it uses
Depot, Osmium, mapshaper, Java/Planetiler, Tippecanoe and PMTiles. Its one-time5GB
Java/two-thread budget is not a runtime game-server requirement. The lightweight
map/index is unchanged by the organic-demand rebuild.

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

- ESA WorldCover2021v200: https://esa-worldcover.org/en/data-access (CC BY4.0).
  ©ESA WorldCover project2021; contains modified Copernicus Sentinel data2021
  processed by ESA WorldCover consortium. Historical built-up fallback only.

- WorldPop population: https://doi.org/10.5258/SOTON/WP00839 (CC BY 4.0).
  Crop downloaded using https://api.worldpop.org/v3/raster, year 2025, 100m.
- JUTPI2 workplace estimates, Table39 printed page60:
  https://openjicareport.jica.go.jp/pdf/12356382.pdf
- BPS SE2016 DKI workplace split (legacyv2 reference, not currentv4 control):
  https://jakarta.bps.go.id/id/statistics-table/2/OTQ5IzI%3D/banyaknya-tenaga-kerja-menurut-wilayah-dan-skala-usaha--provinsi-dki-jakarta-hasil-se2016-.html
- geoBoundaries ADM2 Indonesia, represented year2020, CC BY3.0IGO (legacy regional reference):
  https://www.geoboundaries.org/api/current/gbOpen/IDN/ADM2/

New demand is loaded when starting a new city. Existing saves may retain old demand.

Government source details and administrative audit: `sources/government/COVERAGE.md`.
