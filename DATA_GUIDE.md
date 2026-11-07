# Jabodetabek Subway Builder — data index

This repository contains the lightweight game map, demand data, processing scripts, and an administrative audit.

## Readable files

- [Government coverage and limitations](sources/government/COVERAGE.md)
- [Population and estimated jobs by 1,502 desa/kelurahan (CSV)](sources/government/kelurahan_estimates.csv)
- [Published population controls (JSON)](sources/government/population_controls.json)
- [Workplace proxies (JSON)](sources/government/workplace_proxies.json)
- [Source URLs, reference years and download hashes](sources/government/source_manifest.json)
- [Source quality issues and rejected tables](sources/government/quality_issues.json)
- [Demand methodology](assets/JKT/demand-method.json)
- [Build and in-game verification](BUILD_STATUS.json)

## What the numbers mean

The source population controls total32,615,007 people across mixed reference periods. Most are2025; Kabupaten Bogor is2022. 317kelurahan have direct controls;1,185 other village totals are spatial estimates within official kecamatan totals, using WorldPop weights and BIG boundaries.

The game represents12,646,700 modelled working trip-makers. In-game residents are not the entire population. Detailed workplace capacity, OD pairs and driving times remain estimates. Comprehensive current workplace counts are unavailable for much of the region. Historical JUTPI2018 regional job shares remain part of the model; registered company membership and establishment counts are proxies, not a complete physical-workplace census.

## Full game assets

The files under [assets/JKT](assets/JKT) use gzip compression. Download and decompress them before parsing. `demand_data.json.gz` contains `points` and `pops`; `government_inputs.json.gz` contains preparation cells and village controls. GeoJSON roads and aeroways are geometry data. `buildings_index.bin.gz` is a binary game index, not JSON. PMTiles files are vector tile archives.

Browser previews and text-only tools may not read compressed assets directly. The linked CSV, JSON methodology, and source manifest provide readable entry points; availability through a public URL does not guarantee automatic indexing by a chat service.
