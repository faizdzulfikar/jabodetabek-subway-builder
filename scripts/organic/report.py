"""Write final Stage B report from validated outputs and actual runtime evidence."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
import importlib.metadata as metadata
OUT=ROOT/'docs/organic-stage-b'
def load(name):return json.loads((OUT/name).read_text())
def num(x):return f'{x:,.0f}'
def table(h,rows):return '| '+' | '.join(h)+' |\n|'+'|'.join(['---']*len(h))+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |'for r in rows)+'\n'
if __name__=='__main__':
 q=load('validation.json');d=load('demand_checks.json');run=load('runtime_verification.json');assert run['candidate_sha256']==q['candidate_sha256'];en=load('inventory_enrichment.json');fallback=load('fallback_coverage.json');capacity=load('employment_capacity_regularization.json');centers=load('center_comparison.json');a=readgz(OUT/'proposed_allocations.json.gz');b=json.loads((ROOT/'docs/organic-stage-a/baseline_metrics.json').read_text());route=load('route_sample.json');sensitivity=load('capacity_sensitivity.json');p=a['points'];parcel=[x for x in p if x['anchor_kind']=='builtup_parcel'];env={'python':sys.version,'packages':{n:metadata.version(n)for n in ['numpy','scipy','shapely','pyproj','rasterio','osmium','ortools','matplotlib']}};(OUT/'environment.json').write_text(json.dumps(env,indent=2))
 sources=ROOT/'sources/organic';sources.mkdir(exist_ok=True);manifest={'retrieved_on':'2026-11-07','osm':json.loads((ROOT/'docs/organic-stage-a/reproduction_environment.json').read_text())['pbf'],'worldcover':{'url':'https://esa-worldcover.org/en/data-access','tile_url':'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_S09E105_Map.tif','year':2021,'version':'v200','sha256':fallback['worldcover_sha256'],'classification_used':50,'attribution':'©ESA WorldCover project2021 / Contains modified Copernicus Sentinel data2021 processed by ESA WorldCover consortium','license':'CC BY4.0','role':'historical built-up evidence for road-accessible developed parcels; not2026 observed building function'},'population_covariate':{'source':'sources/worldpop.json','crop_sha256':hashlib.sha256(Path('work/demand-v2/crop.tif').read_bytes()).hexdigest(),'year':2025,'role':'positive modelled population support for fallback; stricter threshold in industrial context'},'coverage_support':'sources/organic/coverage_support.json','government_sources':'sources/government/source_manifest.json','source_year_warning':'Population controls mostly2025, Bogor Regency2022; job regional priors JUTPI2018 and registered-company proxies202406 retained','fallback_actual_use':{'villages':len(set(x['admin_id']for x in parcel)),'anchors':len(parcel),'population':sum(x['population']for x in parcel),'working_residents':sum(x['model_residents']for x in parcel)}};(sources/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
 complete=run.get('in_game_verified',False)
 if complete:
  intro=f"**Selesai dan terpasang lokal**, modv{run['mod_version']}. Diuji di **Subway Builder1.7.2**, termasuk fresh sandbox, Residents/Workers, pemilihan titik, pan/zoom dan save/load. Engine game tidak diubah. Aset v3 disimpan untuk rollback."
  runtime_block=f"Pengujian UI1.7.2 selesai untuk modv{run['mod_version']}: fresh sandbox, Residents/Workers, total12.646.700, titik{num(run['inspected_point_workers'])}workers/{run['inspected_point_workers']//100}pops, pan/zoom, save baru **{run['save_name']}**, lalu load dan pengecekan total/layer lagi. Save yang sudah ada tidak ditimpa. [Catatan runtime](organic-stage-b/runtime_verification.json).\n\nRSS snapshot proses game: {run['game_process_rss_kib_before']/1024:.1f}MiB sebelum dan{run['game_process_rss_kib_after']/1024:.1f}MiB sesudah. Viewport/cache berbeda dan mod lain aktif; ini bukan benchmark terisolasi, pengukuran FPS, atau simulasi jaringan besar. Respons UI diperiksa secara kualitatif.\n\n![Bukti game sesudah load](organic-stage-b/game-v4-reloaded.jpg)"
 else:
  intro="**Data final sudah terpasang lokal dan lulus pemeriksaan file. Uji layar terakhir tertahan karena Mac terkunci.** Target modv0.2.1 pada Subway Builder1.7.2. Engine tidak diubah; aset v3 disimpan untuk rollback."
  runtime_block="**Kalibrasi final belum dinyatakan lolos uji layar.** Alat computer-use melaporkan Mac terkunci dan meminta pengguna membukanya secara manual. Fresh-load, pengecekan layer/point details dan save/load hasil akhir menunggu langkah tersebut. [Status runtime](organic-stage-b/runtime_verification.json).\n\nPrototypev4 awal sudah pernah diuji di1.7.2 termasuk save/load. Bukti itu diarsipkan sebagai [runtime prototype](organic-stage-b/runtime_prototype_v4.json); tidak digunakan sebagai bukti bahwa kalibrasi final sudah diuji. File `prototype-game-*` adalah gambar prototype, bukan hasil akhir."
 text=f'''# Organic demand v4 — hasil Stage B

{intro}

## Hasil utama

{table(['Ukuran','v3','v4'],[
('Inhabitants yang dikontrol',num(b['population_control_total']),num(q['population_geolocated'])),('Penduduk belum terlokasi','Tidak diperiksa','0'),('Kontrol resmi','446','446 eksak di lokasi'),('Working origins dan jobs',num(b['model_tripmakers']),num(d['workers'])+' masing-masing'),('Anchor alokasi inhabitants/workplaces',num(b['points']),num(d['allocation_anchors'])),('Titik aktif engine',num(b['points']),num(d['engine_points'])),('Grup pekerja100orang',num(b['groups']),num(d['groups'])),('Jobs terbesar pada satu anchor',num(b['largest_point_jobs']['jobs']),num(capacity['max_anchor_jobs'])),('Komuter lintas13region','8,886,200 /70.3%',num(d['cross_region_workers'])+' /40.0%'),('Median /p90 jarak lurus','16.81 /38.37km',f"{d['straight_distance_km_p10_p50_p90_p95_p99'][1]:.2f} /{d['straight_distance_km_p10_p50_p90_p95_p99'][2]:.2f}km"),('Gzip demand','3,094,248bytes',num(d['candidate_gzip_bytes'])+'bytes')])}

{num(d['engine_points'])} adalah titik aktif engine, sedangkan{num(d['allocation_anchors'])} anchor juga mencatat penduduk yang tidak menjadi pekerja dan sebagian menerima0unit pekerja setelah rounding.{d['onsite_clone_points']} titik engine tambahan adalah destination alias di koordinat yang sama untuk commute on-site; ini memenuhi aturan ID asal≠tujuan tanpa menggeser lokasi. {load('final_spatial_metrics.json')['duplicate_coordinate_records_excluding_onsite_clones']}koordinat anchor kebetulan sama dari geometri sumber; bukan jitter atau lattice buatan.

## Geografi, coverage dan kapasitas

Koordinat primer mengikuti point-on-surface bangunan pada inventaris OSM penuh, bukan index ringan30.000 bangunan. Class fungsi dan desa harus sama dalam agregasi. Radius maksimum200m untuk dense low-rise,350m untuk urban lainnya dan500m untuk sparse/periurban; garis dari kontributor ke anchor tidak boleh menyeberang jalan utama normal atau air. Perpindahan kontributor p50/p90/p99 sekitar{'/'.join(f'{v:.1f}'for v in load('proposal_checks.json')['cluster_distance_unweighted_p50_p90_p99_m'])}m. Bukti membership tersimpan di scratch `cluster_members.npz`; provenance anchor tersedia di [allocationJSON](organic-stage-b/proposed_allocations.json.gz).

Pengayaan: {num(en['poi_inside_eligible_footprints'])} POI dan{en['official_sites_inside_eligible_footprints']} dari526 situs industri resmi berada langsung dalam footprint eligible. Yang tidak cocok tidak dipaksa ke bangunan terdekat. {en['parts_contained_90pct_in_parent']} parts dengan levels cocok≥90% di parent; union per floor-band memperbaiki{en['parents_with_incremental_floor_union']} parent. {en['levels_inferred_from_nearby_comparable_buildings']} bangunan memakai median levels bangunan berfungsi sama, berukuran sebanding, dalam500m; tetap dilabeli inferred. {num(en['large_unknown_footprints_mixed_use_inferred'])} footprint generik>=800m² memakai prior mixed-use60%hunian/40%aktivitas, dengan90m² per relative worker. Ini inferensi morphology, bukan fungsi gedung yang terukur. {en['dense_small_generic_industrial_context_mixed_inferred']}bangunan generik kecil pada konteks industrial landuse diklasifikasikan mixed-use bila footprint<180m², delapan tetangga dalam60m dan WorldPop2025>=10orang/sel100m; fungsi eksplisit pabrik/office tidak ditimpa. Ini mencegah kawasan campuran dibaca sebagai seluruh bangunannya pabrik. Kasus Jatake memperlihatkan poligon industri OSMw515754822 bertumpang tindih dengan sekitar40,6ha landuse permukiman OSMw516581429; dukungan hunian yang lebih spesifik itulah yang dipakai, bersama built-up dan akses jalan, tanpa menaikkan kapasitas rumah secara sewenang-wenang.

{fallback['villages']} wilayah mendapat dukungan{num(fallback['parcels'])} parcel fallback yang telah disaring, mencakup gap awal dan263desa yang ditandai berisiko kekurangan coverage. [Daftar risiko awal yang dibekukan untuk reproduksi](../sources/organic/coverage_support.json). Hanya{num(len(parcel))} anchor parcel di{len(set(x['admin_id']for x in parcel))} desa benar-benar diperlukan pada alokasi akhir, menampung{num(sum(x['population']for x in parcel))} inhabitants dan{num(sum(x['model_residents']for x in parcel))} working origins. Sisanya menggunakan bangunan. Semua footprint OSM yang sudah ada dikurangi dahulu dengan toleransi2m, sehingga suplementasi tidak menghitung atap yang sama dua kali. WorldPop2025 positif menjadi dukungan tambahan. Pada overlap landuse, permukiman terpetakan mendapat prioritas sebagai dukungan hunian. Di luar dukungan residential itu, konteks industrial hanya menerima parcel kecil<=1200m² dengan WorldPop>=10orang/sel100m; ini inferensi permukiman kecil dalam kawasan campuran, bukan rumah yang ditempatkan pada footprint pabrik terpetakan. Fallback merupakan komponen built-up WorldCover2021 yang di-clip ke wilayah, dikurangi air/hutan/airside/fasilitas nonhunian/badan jalan, dan harus berada dalam200m dari jalan. Titik diambil di sisi akses parcel pada interior yang valid, mengikuti geometri jalan; bukan pusat sel500m atau random scatter.

[Review kapasitas hunian](organic-stage-b/residential_capacity_review.json) setelah suplementasi menandai{load('residential_capacity_review.json')['villages_over5x_prior_capacity']}desa dengan rasio penduduk terhadap prior kapasitas>5. Rasio itu adalah diagnostik coverage/floor/occupancy, bukan overcrowding yang diukur; kontrol penduduk tetap dipertahankan di desa asal.

**WorldCover adalah sumber2021**, bukan observasi2026. Poligon built-up tidak membuktikan fungsi hunian atau okupansi bangunan saat ini. [Sumber, SHA dan atribusi](../sources/organic/source_manifest.json) serta [poligon fallback](organic-stage-b/fallback_parcels.geojson.gz) menyimpan batas ketidakpastian itu.

## Perubahan parameter yang diperlukan selama implementasi

Pilot memperlihatkan satu mall dapat menerima67.100 jobs karena kapasitas fungsi yang jarang dipetakan dinormalisasi>10kali pada Bogor. Itu tidak diterima sebagai jumlah pekerja riil. Komponen fungsi/lantai sekarang dibatasi pada maksimum2×kapasitas relatif, kurang-lebih ujung intensitas tinggi pada rentang StageA. Sisa regional tetap dipertahankan melalui prior pekerjaan lingkungan/mixed-use yang belum terklasifikasi. Batas ini bekerja pada komponen kapasitas, **bukan cap total jobs seragam per bangunan**.

Porsi residual tersebut berbeda menurut region dan harus dibaca sebagai ukuran ketidaklengkapan fungsi yang terpetakan—**bukan persentase informal-sector atau home-working yang teramati**:

{table(['Region','Jobs regional tetap','Komponen lingkungan belum terklasifikasi'],[[r['region'],num(r['jobs']),f"{100*r['unclassified_neighborhood_component_share']:.1f}%"]for r in capacity['regions']])}

Terutama Bogor masih sangat bergantung pada prior. Kontrol regional historis/registrasi dipertahankan sesuai urutan kalibrasi yang disetujui; tidak dinyatakan sebagai physical-workplace census2026. Sebelum rebalancing regional berikutnya, diperlukan staffing/lokasi fisik perusahaan dan tabel workplace komuter yang sebanding. [Regularisasi lengkap](organic-stage-b/employment_capacity_regularization.json).

Sembilan skenario ceiling1,5/2/3 × minimum-komponen-lingkungan10/20/30% sudah dihitung; semuanya menjaga jobs12.646.700. Nilai jobs maksimum per anchor bervariasi{num(min(s['largest_anchor_jobs']for s in sensitivity['scenarios']))}–{num(max(s['largest_anchor_jobs']for s in sensitivity['scenarios']))}. [Sensitivity per pusat dan region](organic-stage-b/capacity_sensitivity.json) adalah skenario ketidakpastian, bukan confidence interval.

## Pusat pekerjaan sebelum/sesudah

{table(['Prioritas / pusat','Jobsv3','Jobsv4'],[[r['priority']+' '+r['center'],num(r['before_jobs']),num(r['proposal_jobs'])]for r in centers])}

Jendela saling overlap dan bukan batas pusat ekonomi; tidak boleh dijumlahkan. Tidak ada boost berdasarkan nama pusat. Angka adalah model alokasi, bukan staffing yang diobservasi. [CSV](organic-stage-b/employment_centers.csv) dan [cluster tambahan](organic-stage-b/discovered_clusters.json) membantu audit lanjutan.

![CBD dan Kuningan](organic-stage-b/focus_cbd.png)
![Industri Cikarang](organic-stage-b/focus_cikarang_industrial.png)

## OD dan waktu perjalanan

18km decay dengan skenario40% lintas region dipertahankan sebagai pilihan review StageA.40% **bukan fitted rate2026**. IPF membentuk point-to-region probabilities, kemudian min-cost integer rounding dan matching jarang dalam169 pasangan region menjaga semua point margins serta13×13 quota. Seed20261107, stochastic cost scale6km; maksimal32 nearest/random candidates cukup pada snapshot ini. Setiap grup tetap100orang. Rounding quota memberi{num(d['cross_region_workers'])} pekerja lintas region({d['cross_region_fraction']*100:.4f}%).

Tidak ada origin/destination yang hilang akibat local weighted sampling seperti generator lama. [Pemeriksaan independen](organic-stage-b/validation.json) merekonstruksi margin dan `popIds` dari seluruh126.467 grup, termasuk alias on-site. [Matriks OD](organic-stage-b/regional_od.csv) dan [pasangan titik](organic-stage-b/od_pairs.npz) adalah hasil aktual generator, bukan sampel kernel StageA.

![RegionalOD](organic-stage-b/regional_od_comparison.png)
![Jarak actual syntheticOD](organic-stage-b/od_distance_comparison.png)

DrivingDistance/Seconds tetap **proksi**1,35×jarak lurus,24km/jam+180s. Sampel96pasangan berbobot demand pada graph2.574.993 node/2.716.500 edge jalan mendapat{route['reachable_pairs']}pasangan terhubung; median detour{route['detour_ratio_median_p90'][0]:.2f},p90{route['detour_ratio_median_p90'][1]:.2f}. Ini mendukung faktor median kira-kira1,35 tetapi menunjukkan ekor yang lebih panjang. Semua jalan minor dimasukkan; access/turn restrictions dan kemacetan tidak tersedia. {96-route['reachable_pairs']}pasangan tak terhubung adalah keterbatasan graph, bukan bukti tidak ada jalan di kenyataan. **Jangan sebut setiap trip sudah diroute pada jalan.** [Detail sampel](organic-stage-b/route_sample.json).

## QA dan runtime

446 kontrol penduduk lulus dengan residual0; asal/tujuan per titik dan region eksak; seluruh referensi/linkpop valid;{num(q['allocation_building_anchors_checked'])} anchor berada di footprint sumber,{num(q['allocation_parcel_anchors_checked'])} di parcel valid; semua di admin dan bbox yang benar. Nol hit terhadap mask air pantai/daratan, hutan/wetland, airside dan buffer jalan utama8m yang tersedia. Ini validasi dataset, bukan survei lapangan atau jaminan semua objek terpetakan.

Dua generasi demand identik byte demi byte. SHA256 terpasang:`{q['candidate_sha256']}`. Validator paket asli juga lulus:30.000 indexbuildings,414.732 roads,454aerowayfeatures,{num(d['engine_points'])} points,126.467groups. Map tiles, roads, aeroways, foundations dan building index tidak dibesarkan/diubah. Net tambahan demand{num(d['candidate_gzip_bytes']-3094248)}bytes(~{(d['candidate_gzip_bytes']-3094248)/1024**2:.2f}MiB).

{runtime_block}

## File, reproduksi dan rollback

- [Data penduduk/pekerjaan per1.502desaCSV](organic-stage-b/proposed_village_allocations.csv), [kontrol446](organic-stage-b/population_control_checks.json), [metadata alokasi lengkap](organic-stage-b/proposed_allocations.json.gz).
- Aset runtime:[demand_data.json.gz](../assets/JKT/demand_data.json.gz), [metodev4](../assets/JKT/demand-method.json), [status build](../BUILD_STATUS.json).
- Raw PBF, SQLite penuh, WorldCover34MB dan candidate arrays tetap di scratch; tidak dimasukkan payload game.
- Dari workspace:`work/map-venv/bin/python outputs/jabodetabek-mod/scripts/organic/rebuild.py`. Memerlukan inventaris StageA, tile WorldCover dan cropWorldPop2025 yang SHA-nya tercatat. Versi paket:[environment.json](organic-stage-b/environment.json). Default staging; `--install` memasang hanya setelah gate dan reproducibility lulus. Uji UI wajib diulangi sesudah install; script tidak boleh mengklaim in-game verified otomatis.
- [Rollbackv3](organic-stage-b/rollback-v3/manifest.json): salin kembali file pada manifest ke path relatif repo yang sama, lalu hot-reload/scan mod dan buka city/savev3. Jangan menjalankan generator lama tanpa sengaja ketika hanya ingin memulihkan aset. Docs/provenancev4 boleh tetap disimpan.

Perubahan source/asset ini masih lokal. Laporan StageA tetap tersedia sebagai baseline; angka dan file preview StageA tidak menggantikan hasil StageB ini.
'''
 (ROOT/'docs/ORGANIC_DEMAND_STAGE_B.md').write_text(text);(OUT/'README.md').write_text('# Organic demand v4\n\n[Hasil StageB](../ORGANIC_DEMAND_STAGE_B.md), [validasi](validation.json), [runtime](runtime_verification.json), [data desa](proposed_village_allocations.csv), [provenance](proposed_allocations.json.gz), [rollback](rollback-v3/manifest.json).\n\nPenduduk dan working tripmakers adalah konsep berbeda. Seluruh jobs/OD tetap model estimates. Fallback parcel memakai WorldCover2021 yang dilabeli.\n');print('Final StageB report written')
