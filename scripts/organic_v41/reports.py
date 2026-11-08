"""Generate the six StageA v4.1 audit/proposal documents from measured outputs."""
from pathlib import Path
import json,csv,gzip,hashlib,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41'
def load(n):return json.loads((OUT/n).read_text())
def rows(n):return list(csv.DictReader((OUT/n).open()))
def num(x):return f'{float(x):,.0f}'
def pct(x):return f'{float(x)*100:.1f}%'
def table(headers,data):return '| '+' | '.join(headers)+' |\n|'+'|'.join('---'for _ in headers)+'|\n'+'\n'.join('| '+' | '.join(str(x).replace('|','/')for x in row)+' |'for row in data)+'\n'
def write(n,s):(ROOT/'docs'/n).write_text(s,encoding='utf-8')
def link(n,label=None):return '['+(label or n)+'](organic-v41/'+n+')'
if __name__=='__main__':
 checks=load('completion_checks.json');audit=load('audit_checks.json');val=load('validation.json');d=load('demand_checks.json');perf=load('performance.json');od=load('od_diagnostics.json');sens=load('od_sensitivity.json');diag=load('diagnostic_checks.json');regional=rows('regional_comparison.csv');areas=rows('area_comparison.csv');cor=rows('residential_anchor_corrections.csv');sources=load('source_evidence.json')['sources'];roles=rows('airport_role_comparison.csv');sub=[r for r in areas if r['kind'].startswith('residential')];ind=[r for r in areas if r['kind']=='industrial'];centers=[r for r in areas if r['kind']=='employment_core'];airport=next(r for r in areas if r['kind']=='airport');discovered=rows('additional_coverage_review.csv');districts=rows('all_district_comparison.csv');occupation=load('jakarta_occupation_subset.json')
 banner='**Stage A — audit dan proposal, 8 November 2026. Belum diinstal dan belum diuji di game.** Produksi tetap Organic v4 / mod 0.2.1, commit `dfec7f2`. Tidak ada perubahan engine, peta, atau aset game.\n\n'
 scope='''Angka “penduduk” di dokumen ini adalah seluruh inhabitants; “asal pekerja” adalah model working trip-makers; “jobs” adalah estimasi tujuan kerja. S0 adalah koreksi klasifikasi konservatif. S1 adalah sensitivitas intensitas, **bukan** target pegawai hasil observasi. OD30 dan OD40 adalah skenario terpisah dari koreksi geografis S0.

Batas kecamatan/desa memakai union batas BIG Juni 2026. Kompleks industri memakai poligon OSM bernama; koridor bisnis memakai potongan poligon aktivitas dalam jendela audit. BSD/Gading Serpong/Alam Sutera/Sentul memiliki subset hunian terpetakan atau envelope administratif yang dilabeli: tidak diklaim sebagai batas legal township lengkap. Area tumpang tindih **tidak boleh dijumlahkan**. [Semua batas dan label cakupan](organic-v41/audit_boundaries.geojson.gz).

'''
 source_text='## Provenance dan tingkat kepastian\n\n**Observed:** angka kontrol/survei, tag/footprint terpetakan, dan pernyataan operator; tidak otomatis berarti staffing aktual. **Inferred:** fungsi dari konteks/nama, lantai berguna, lokasi penduduk/pekerjaan. **Gameplay calibration:** rasio kapasitas, ceiling, parameter dan pasangan OD. Semua jobs rinci tetap estimasi.\n\n'
 source_text+=table(['ID','Sumber / periode','Cakupan dan penggunaan'],[[x['id'],f"[{x['publisher']}]({x['url']}) / {x.get('year') or 'tidak bertanggal'}",x['scope']]for x in sources])
 source_text+='\nSumber pemda yang sudah dipakai tetap tersedia dalam [manifest pemerintah](../sources/government/source_manifest.json), [kontrol penduduk](../sources/government/population_controls.json), dan [quality issues](../sources/government/quality_issues.json). Detail akses, fakta terpilih dan keterbatasan: '+link('source_evidence.json')+'. Tidak ada pengumuman fasilitas masa depan yang dianggap sudah terbangun.\n'
 # area detail appendix: every important area has requested current/proposed metrics.
 detail='# Tabel seluruh area v4.1\n\n'+banner+scope
 for a in areas:
  detail+='## '+a['name']+'\n\n'+a['boundary_source']+'. '+a['scope']+'.\n\n'
  detail+=table(['Metrik','Current v4','Proposed S0','Bukti'],[['Seluruh penduduk',num(a['population_current']),num(a['population_proposed']),'Kontrol pemda; pembagian subwilayah inferred'],['Asal pekerja model',num(a['working_origins_current']),num(a['working_origins_proposed']),'Kelurahan/kecamatan tetap, titik dapat berubah'],['Workplace jobs model',num(a['jobs_current']),num(a['jobs_proposed']),'Alokasi kapasitas; bukan sensus pegawai'],['Jobs / ha poligon',a['jobs_per_area_ha_current'],a['jobs_per_area_ha_proposed'],'Denominator batas terpetakan, bukan occupied floor area'],['Jobs / ha built-up historis',a['jobs_per_worldcover2021_builtup_ha_current'],a['jobs_per_worldcover2021_builtup_ha_proposed'],f"WorldCover 2021 class50: {a['worldcover2021_builtup_proxy_ha']}ha; bukan sensus developed2025"],['Confidence',a['confidence'],a['confidence'],'Observed boundary subset; inferred local amounts']])
  detail+=f"\nS1 capacity pilot jobs: **{num(a['jobs_pilot_s1'])}**. Eligible roofs {a['eligible_roof_ha']}ha, {num(a['eligible_mapped_buildings'])} bangunan; tag fungsi eksplisit {pct(a['explicit_function_building_fraction'])}, level tercatat {pct(a['observed_levels_building_fraction'])}. Penduduk pada fallback parcel: {num(a['population_on_parcel_fallback'])}. Angka tag eksplisit bukan validasi fungsi lapangan.\n\n"
 (OUT/'AREA_DETAILS.md').write_text(detail.replace('](organic-v41/','](').rstrip()+'\n')
 # archive old document once, preserving older report references.
 archived=OUT/'archive_v4_EMPLOYMENT_DENSITY_AUDIT.md'
 if not archived.exists():
  old=(ROOT/'docs/EMPLOYMENT_DENSITY_AUDIT.md').read_text();old=old.replace('](organic-stage-a/','](../organic-stage-a/').replace('](organic-stage-b/','](../organic-stage-b/');archived.write_text(old)
 summary=table(['Metrik','Current v4','S0 + OD30 review'],[['Penduduk',num(checks['total_population']),num(checks['total_population'])],['Asal pekerja / jobs',num(checks['total_jobs']),num(checks['total_jobs'])],['Allocation anchors',num(audit['allocation_anchors_current']),num(audit['allocation_anchors_proposed'])],['Engine points aktif',num(perf['current']['points']),num(perf['S0_OD30_candidate']['points'])],['Demand gzip bytes',num(perf['current']['gzip_bytes']),num(perf['S0_OD30_candidate']['gzip_bytes'])],['Kontrol penduduk tepat',446,446],['Pekerja lintas kab/kota',num(od['current']['cross_region_workers']),num(od['proposed_S0_tau18_cross30']['cross_region_workers'])],['Median jarak lurus (km)',f"{od['current']['distance_km_p10_p50_p90_p95_p99'][1]:.2f}",f"{od['proposed_S0_tau18_cross30']['distance_km_p10_p50_p90_p95_p99'][1]:.2f}"]])
 problems=[
 ('Partisipasi pekerja belum dikalibrasi penuh','Asal DKI4,191,700 vs Sakernas5.13juta; Kab Bogor2,129,800 vs2.62juta, dengan cakupan berbeda','Observed reference / inferred model','Audit cohort dan work-at-home; skenario demografi terpisah, bukan tambah20juta workers'),
 ('Regional jobs historis / alamat kantor','13 total tujuan masih kontrol historis JUTPI dan Jamsostek untuk kota Jakarta','Observed provenance / inferred physical jobs','Jangan pindahkan jobs lintasregion tanpa bukti physical-workplace independen'),
 ('Fallback pekerjaan mendominasi wilayah satelit','Kab Bogor83.34%; Kota Bekasi73.46%; Kota Tangerang73.51% jobs melalui prior hunian','Inferred','Perluas inventaris/fungsi dan facility controls sebelum mengurangi fallback'),
 ('Kawasan industri luas, fungsi gedung jarang eksplisit',f"GIIC explicit-tag {pct(next(x for x in ind if x['name'].startswith('GIIC'))['explicit_function_building_fraction'])}; Jababeka {pct(next(x for x in ind if x['name']=='Jababeka')['explicit_function_building_fraction'])}",'Observed tags / inferred function','Jangan konversi semua atap industri jadi pabrik dengan densitas identik'),
 ('OD40 belum fit pada survei pekerja','5,058,600 model cross-boundary; BPS2023 pekerja-komuter3,614,673, beda tahun/definisi','Gameplay calibration / observed survey','Bandingkan30/35/40%; harmonisasi sebelum fit final'),
 ('Tidak ada perjalanan khusus non-kerja pada v4','0 UNI_/AIR_/BRD_ points; BPS800,301 komuter sekolah/kuliah/kursus lintaswilayah','Observed engine/data','Tambahkan ledger tujuan non-kerja dengan data pendidikan/pengunjung tersendiri'),
 ('Penduduk di fungsi yang jelas nonhunian',f"33 anchors; {num(sum(int(x['population_removed_from_anchor'])for x in cor))} inhabitants dan {num(sum(int(x['working_origins_removed_from_anchor'])for x in cor))} asal pekerja pada anchor terindikasi",'Observed tags / inferred operational names','S0 pindahkan dalam desa yang sama; audit ulang anggota cluster sebelum implementasi penuh'),
 ('Hanggar bandara terhapus dari kesempatan kerja','6 footprint hanggar,0 current jobs pada anchor hanggar; S0 menambah2,200 dihanggar','Observed geometry / inferred capacity','Pulihkan interior hanggar; cek pintu pekerja/access di StageB'),
 ('Ekosistem CGK belum tercakup pasti','13,500 current,15,000 S0,21,300 S1 dalam aerodrome; benchmark2022 tidak sebanding','Inferred / historical statement','Audit payroll/contractor per fasilitas; jangan force50,000'),
 ('Lantai dan fungsi tempat kerja masih inferensi',f"CGK level tercatat {pct(airport['observed_levels_building_fraction'])}; CBD tag fungsi tidak mengukur pegawai",'Observed completeness / inferred heights','Gunakan building parts, operator facility evidence; jangan pakai footprint saja'),
 ('Prior mixed-use besar bisa meresidentialkan fasilitas','Atap generic>=800m² diasumsikan60%residential/40%activity pada v4','Inferred','Identifikasi fasilitas nonhunian dulu; S0 memperbaiki bukti positif, bukan blanket airport exclusion'),
 ('Ceiling2 dan residual dapat mengencerkan pusat kerja','Sensitivitas ceiling1/2/3 dihitung dengan semua marginal regional tepat','Gameplay calibration','Tahan threshold produksi; S1 hanya uji diagnosis, bukan pengganti data'),
 ('Coverage perumahan terputus dan referensi tua',f"{discovered[0]['kecamatan']} fallback-share {pct(discovered[0]['population_fallback_share'])}; WorldCover2021, Bogor population2022",'Observed provenance / inferred spatial stock','Update geometri terbangun dan skenario pertumbuhan dengan sumber; jangan boost visual'),
 ('Waktu berkendara belum routing terukur','1.35×jarak lurus,24km/jam+180s; sample v4 saja, tanpa kemacetan/turn restrictions','Gameplay calibration','Kalibrasi detour/speed dan jaringan pada StageB; tidak klaim waktu aktual'),
 ('Agregasi/display dapat disangka kekurangan penduduk','78,404 active engine points vs115,929 anchors; game building index30,000; group100','Observed format / display limitation','Bedakan inhabitants, origins dan visual index; COVERAGE.md lama masih menyebut grid500m v3')]
 ranked=table(['Rank','Masalah','Ukuran/bukti','Kelas','Aksi'],[[i+1,*x]for i,x in enumerate(problems)])
 master='# Organic v4.1 — master audit\n\n'+banner+scope+'## Hasil yang dapat langsung ditinjau\n\n'+summary+f'''\nS0 merelokasi **{num(audit['population_moved_half_l1'])} penduduk**, **{num(audit['working_origins_moved_half_l1'])} asal pekerja**, dan **{num(audit['jobs_moved_half_l1'])} jobs** (masing-masing half-L1), dengan semua total desa/region tetap.33 anchor ditandai (28 berdasar tag positif,5 berdasar nama operasional bandara yang masih inferred);6 hanggar dipulihkan. Perbedaan4,700 pekerja yang berada pada anchor salah vs4,800 yang pindah total berasal dari pembulatan ulang100orang di desa terdampak.

Tidak ditemukan dasar untuk menaikkan semua pinggiran dengan multiplier. Alokasi administratif sudah tepat; masalah yang terukur terutama lokasi intra-desa, coverage dan fungsi gedung. S0 bukan penyelesaian seluruh kekurangan bukti pekerjaan. Pilot S1 hanya menunjukkan pengaruh prior fasilitas dan ceiling.

## Lima belas masalah paling konsekuensial

Urutan adalah penilaian dampak realistis/geografis oleh auditor, **bukan** ranking statistik hasil survei atau skor kepastian. Ukuran pada tiap baris dihitung dari data atau sumber yang disebut.

'''+ranked+'''\n## Hasil validasi

446 kontrol diperiksa ulang secara independen. Populasi32,615,007; origins/jobs12,646,700; seluruh point/pop references dan OD marginal tepat. Seluruh anchor berada di building/parcel yang dirujuk dan administrasinya. Nol hit pada **mask terpetakan yang tersedia**: water/coast, forest/wetland, runway/taxiway/apron, major-road8m proxy. Ini tidak membuktikan seluruh akses airside diketahui: pintu karyawan dan jalan privat perlu pemeriksaan fasilitas sebelum game release.

Koordinat v4 tidak digeser;6 titik tambahan adalah interior hanggar nyata. Tidak ada grid/jitter/penyebaran uniform. Raster internal hanya mengukur coverage historis, tidak menjadi titik final. [Validasi kandidat](organic-v41/validation.json), [pemeriksaan selesai](organic-v41/completion_checks.json), [seluruh detail area](organic-v41/AREA_DETAILS.md).

![Geografi sebelum/sesudah](organic-v41/metro_before_after.png)

## Dokumen dan data

- [Audit perumahan](SUBURBAN_RESIDENTIAL_AUDIT.md).
- [Audit pekerjaan](EMPLOYMENT_DENSITY_AUDIT.md).
- [Audit bandara dan industri](AIRPORT_INDUSTRIAL_EMPLOYMENT_AUDIT.md).
- [Audit populasi–demand](POPULATION_DEMAND_GAP_AUDIT.md).
- [Proposal yang perlu persetujuan](ORGANIC_V41_CALIBRATION_PROPOSAL.md).
- [Point current/proposed](organic-v41/point_comparison.csv.gz), [kelurahan](organic-v41/village_comparison.csv), [regional](organic-v41/regional_comparison.csv), [area](organic-v41/area_comparison.csv), [skenario OD](organic-v41/od_sensitivity.json).

'''+source_text
 write('ORGANIC_V41_MASTER_AUDIT.md',master)
 subtable=table(['Area / cakupan','Penduduk current→S0','Asal pekerja current→S0','Jobs current→S0','Fallback inhabitants','Bukti'],[[x['name'],num(x['population_current'])+' → '+num(x['population_proposed']),num(x['working_origins_current'])+' → '+num(x['working_origins_proposed']),num(x['jobs_current'])+' → '+num(x['jobs_proposed']),num(x['population_on_parcel_fallback']),x['boundary_source']]for x in sub])
 subdoc='# Audit perumahan suburban\n\n'+banner+scope+'''## Batas dan pembanding yang sah

Setiap kecamatan/desa prioritas mempunyai geometri BIG dan total terkontrol; BSD/Gading Serpong/Alam Sutera/Sentul memakai subset/envelope yang dinyatakan. Total township pemasaran tidak dibandingkan langsung dengan potongan poligon. “Nambo” di sini adalah desa Nambo di Klapanunggal, bukan sekadar radius stasiun; Sentul dibandingkan pula dengan Babakan Madang dan Sukaraja. Kota Bekasi dan Kota Bogor diaudit sebagai kota serta kecamatan sekitar.

Seluruh **'''+str(diag['all_districts_reviewed'])+''' kecamatan** dan1,502desa/kelurahan dibandingkan.317 kontrol kelurahan langsung,129 kontrol kecamatan:1,185 angka desa sisanya adalah pembagian perkiraan yang tetap dipertahankan. Semua total desa dan kecamatan current/S0 identik; perbedaan potongan area semata hasil relokasi intra-desa, bukan menambah penduduk.

'''+subtable+'''\n## Morfologi dan coverage

Kampung padat memakai banyak atap kecil; estate modern bisa mempunyai atap lebih besar dan ruang terbuka lebih luas. Apartemen perlu floor area, tidak hanya luas tapak. Jumlah titik yang tampak jarang dapat berasal dari agregasi200/350/500m atau pembulatan100 working trip-makers; **bukan bukti inhabitants hilang**. Rincian jumlah bangunan, apartment-tag, roof area, coverage fungsi/level serta rasio population/capacity tersedia untuk setiap area dalam [tabel detail](organic-v41/AREA_DETAILS.md) dan [CSV](organic-v41/area_comparison.csv).

S0 meninjau33 anchor:28 bertag nonhunian positif,5 fungsi operasional bandara diinferensi dari nama dan konteks. Kelima kasus inferred perlu pemeriksaan fasilitas sebelum implementasi.12,142 inhabitants dipindah hanya ke anchor residential yang sudah ada dalam desa yang sama. Unknown airport buildings tidak otomatis dikosongkan;5,104 inhabitants masih berada dalam batas aerodrome, dengan fungsi rumah yang belum terverifikasi. Itu **risiko residual**, bukan klaim ada5,104 penghuni bandara sebenarnya. Sebelum StageB penuh, anggota cluster di sekitar bangunan yang dikoreksi perlu diklasifikasi kembali; preview ini mempertahankan geometri/cluster lama agar dampak mudah diukur.

## Cluster tambahan untuk pemeriksaan coverage

Peringkat ini memilih ketergantungan fallback tinggi, bukan menyatakan underpopulation. Jumlah penduduknya tetap sesuai kontrol; yang lemah adalah bukti sebaran internal. Sumber fallback WorldCover2021 lebih tua dari kondisi2025–2026.

'''+table(['Wilayah / kecamatan','Penduduk current=S0','Asal pekerja','Penduduk pada fallback','Population / relative-capacity'],[[x['region']+' / '+x['kecamatan'],num(x['population_current']),num(x['working_origins_current']),pct(x['population_fallback_share']),f"{float(x['population_to_relative_capacity']):.2f}"]for x in discovered])+'''\n![Penduduk BSD dan sekitarnya](organic-v41/bsd_residential.png)

![Penduduk Bekasi dan koridor industri](organic-v41/bekasi_residential.png)

![Bogor dan koridor Nambo](organic-v41/bogor_residential.png)

Gambar ini membandingkan **seluruh inhabitants** pada anchor aktual, dengan panel selisih relokasi. Itu bukan layer Residents di game. Stok inhabitants dan jobs pada [peta metro](organic-v41/metro_before_after.png). Tidak ada alasan kuantitatif dalam audit ini untuk menerapkan multiplier suburban menyeluruh. Untuk Bogor, pertumbuhan2022→2025 perlu skenario terpisah dengan sumber terbaru, bukan diekstrapolasi diam-diam.

Data: [seluruh kecamatan](organic-v41/all_district_comparison.csv), [desa](organic-v41/village_comparison.csv), [koreksi anchor](organic-v41/residential_anchor_corrections.csv), [batas](organic-v41/audit_boundaries.geojson.gz). Provenance dan batas definisi: [master audit](ORGANIC_V41_MASTER_AUDIT.md#provenance-dan-tingkat-kepastian).
'''
 write('SUBURBAN_RESIDENTIAL_AUDIT.md',subdoc)
 emppar=table(['Region','Jobs current=S0','v4 neighborhood-prior share','S0 share','S1 pilot share','S0 jobs dipindah'],[[x['region'],num(x['jobs_current']),pct(x['v4_fallback_share']),pct(x['proposed_fallback_share']),pct(x['pilot_fallback_share']),num(x['reallocated_jobs_half_l1'])]for x in regional])
 empdoc='# Audit kepadatan pekerjaan v4.1\n\n'+banner+scope+'''Audit v4 terdahulu diarsipkan [di sini](organic-v41/archive_v4_EMPLOYMENT_DENSITY_AUDIT.md). Kode aktif yang diperiksa adalah `scripts/organic/allocate.py`, `enrich.py`, `calibrate_jobs.py`, dan `demand.py`, bukan generator grid v3.

## Konsentrasi pusat metropolitan

Angka berikut memakai **core aktivitas terpetakan**, bukan seluruh kecamatan maupun batas township legal. Residential mixed-use corridors yang tidak bertag aktivitas dapat berada di luar core; semua metrik lengkap dan kepastian batas ada di [AREA_DETAILS](organic-v41/AREA_DETAILS.md). Jobs/ha memakai luas poligon, bukan floor-space intensity.

'''+table(['Pusat','Populasi current→S0','Asal pekerja current→S0','Jobs current→S0','Jobs S1 pilot','Jobs/ha current→S0'],[[x['name'],num(x['population_current'])+' → '+num(x['population_proposed']),num(x['working_origins_current'])+' → '+num(x['working_origins_proposed']),num(x['jobs_current'])+' → '+num(x['jobs_proposed']),num(x['jobs_pilot_s1']),x['jobs_per_area_ha_current']+' → '+x['jobs_per_area_ha_proposed']]for x in centers])+'''\n## Mengapa fallback bisa mengencerkan pusat kerja

Aturan v4 aktual: `floor = min(0.8 × regional_jobs × capacity / sum_capacity, 2 × capacity)`. Sisa dibagi memakai kapasitas residential/mixed. Minimum residual20% timbul dari desain80/20; saat coverage workplace tipis, residual menjadi jauh lebih besar. Ini **prior lokasi untuk pekerjaan tak terklasifikasi**, bukan pengukuran share informal/home-working. Tidak semua pekerjaan yang menempel residential benar-benar berada di rumah.

'''+emppar+'''\nS0 tidak mengganti pembagian total regional. Dampak5700jobs hanya koreksi fasilitas/titik dan pembulatan ulang. S1 mengubah4,472 kapasitas fasilitas bertag: factory75→50m²/model-worker, warehouse140→180, terminal150→80, hanggar150→100. Nilai itu **asumsi sensitivitas**, bukan employee-per-building yang teramati; inferred factory dari industrial landuse tidak otomatis dinaikkan. Perubahan ini belum cukup menutup kekurangan bukti pekerjaan di Kabupaten Bogor atau membuktikan workforce Jababeka.

`function_observed` di provenance v4 sering berarti tag bangunan non-generik; itu bukan observasi staf. `capacity_mix` adalah kapasitas relatif konstituen cluster, bukan hitungan pekerjaan per fungsi yang diamati. Perbandingan floor/neighborhood dipisah menurut flag dalam [employment_evidence_components.csv](organic-v41/employment_evidence_components.csv). Memakai footprint nyata tidak membuat angka staffing menjadi observed.

## Fungsi dan intervensi yang tepat

'''+table(['Fungsi','v4 m² / relative worker','Intervensi proposal'],[['Corporate offices',20,'Pertahankan; perbaiki lantai/parts dari bukti gedung, jangan blanket CBD multiplier'],['Government',25,'Alamat instansi dan lantai; jangan ikutkan semua warga administratif'],['Factory',75,'S0 tetap; S1=50 hanya tag positif, uji tenaga kerja fasilitas'],['Warehouse / logistics',140,'S0 tetap; S1=180, bukan factory intensity'],['Retail / mall',35,'Bedakan podium retail dari tower mixed-use; no arbitrary mall staffing target'],['Traditional market',45,'Gunakan pasar nyata, hindari duplikasi toko dan polygon pasar'],['University / school','50 / 70','Untuk staf; enrolment pelajar bukan jobs staf'],['Hospital',45,'Staf saja; patient trips perlu ledger berbeda'],['Hotel',100,'Staf; bukan occupancy pengunjung'],['Transport',150,'Hanggar CGK dipulihkan pada S0; airport-specific intensities hanya S1'],['Neighborhood / informal','Residual regional','Tetap ada; tidak dihapus hanya untuk membesarkan CBD'],['Generic large mixed','60%res /40%activity','Inferred; perlu screening fasilitas operasional/tangki/parkir']])+'''\n## Diagnosis sumber underrepresentation

1. **Geometry:** enam hanggar dibuang dari eligible allocation; banyak polygon industri tidak punya fungsi gedung eksplisit.
2. **Classification:** generic mixed membolehkan penghuni pada fungsi operasional/tangki/parkir; bukti positif teridentifikasi33anchor.
3. **Levels:** airport hanya sedikit level tercatat; tower kantor bisa terlalu rendah, tetapi jumlah pegawai aktual belum tersedia.
4. **Area per worker:** berbeda antara factory, warehouse, data center, office dan terminal; S1 menguji, tidak mengklaim mengukur.
5. **Ceiling2:** membatasi ekspansi kapasitas sparse; tabel1/2/3 menunjukkan tradeoff terhadap residual dan konsentrasi.
6. **Fallback:**83% Kabupaten Bogor membuat pekerjaan mengikuti prior residential lebih kuat daripada pusat ekonomi teramati.
7. **Regional totals:** JUTPI2018/alamat perusahaan bisa mengunci jobs di region keliru; tidak diperbaiki dengan multiplier dalamregion.
8. **Aggregation:** jobs masuk anchor sefungsi dalam desa, sehingga jarak200–500m dapat menggeser tampilan relatif ke compound kecil. StageB perlu batas fasilitas sebagai barrier tambahan dan entry point pekerja; tidak hanya menambah points.

No independent current physical-workplace census supports a numeric regional rebalancing here. All13job margins remain baseline. An employer registered in South Jakarta but staffed in Cikarang must be assigned once to its physical workplace when evidence exists, rather than added to both.

[Jobs menurut kelas anchor](organic-v41/function_comparison.csv), [capacity sensitivity](organic-v41/capacity_sensitivity.csv), [per-fasilitas](organic-v41/facility_capacity_changes.csv), [regional](organic-v41/regional_comparison.csv). [Provenance](ORGANIC_V41_MASTER_AUDIT.md#provenance-dan-tingkat-kepastian).
'''
 write('EMPLOYMENT_DENSITY_AUDIT.md',empdoc)
 airportdoc='# Audit bandara dan kawasan industri v4.1\n\n'+banner+scope+'''## Kawasan industri: apa yang benar-benar diukur

Poligon industri bernama bukan ukuran pasti lahan **sudah ditempati**. Density dibawah adalah semua jobs model dalam batas dibagi class50 WorldCover2021 di batas itu; ia hanya proxy built-up historis. Kolom luas penuh/mapped industrial, nonnatural-land proxy, roof area dan density pada denominator lain disediakan dalamCSV. Tidak ada klaim telah memetakan occupied industrial hectares2025 secara lengkap. Landbank GIIC/Jababeka dan roof coverage yang kurang bisa membias denominator. Pending data operator occupied-lots per fasilitas, jangan gunakan jobs/ha proxy sebagai target observasi.

'''+table(['Kawasan / batas terpetakan','Luas ha','Built-up2021 ha','Jobs v4','S0','S1 pilot','Jobs/built-up ha v4→S0','Factory / warehouse eligible'],[[x['name'],x['area_ha'],x['worldcover2021_builtup_proxy_ha'],num(x['jobs_current']),num(x['jobs_proposed']),num(x['jobs_pilot_s1']),x['jobs_per_worldcover2021_builtup_ha_current']+' → '+x['jobs_per_worldcover2021_builtup_ha_proposed'],x['mapped_factory_buildings']+' / '+x['mapped_warehouse_buildings']]for x in ind])+'''\n**Perbandingan operator dan cakupan:** EJIP menyebut320ha dan91tenant; poligon OSM302.43ha adalah pendekatan footprint, bukan jaminan coverage pegawai. MM2100 operator menyebut±2000ha termasuk partner; OSM1890.74ha mendekati luas itu tetapi bukan occupied-land proof. Profil Jababeka menyebut700000workers pada township5600ha; audit ini memakai1433.03ha poligon fase industri bernama. Publikasi pemasaran lain memakai captive-market1juta workers. Angka-angka itu **tidak dijumlahkan** atau dipakai sebagai target pada subset industrial yang berbeda. GIIC melaporkan tenant termasuk data center; tenant tidak dikonversi menjadi pegawai seragam. Sumber rinci dan tahun/akses ada di [master](ORGANIC_V41_MASTER_AUDIT.md#provenance-dan-tingkat-kepastian).

Cibitung sebagai alamat pemasaran tidak selalu sama dengan kecamatan BIG Cibitung. MM2100 sebagian besar berada dalam footprint yang ditabelkan sendiri; subset industrial Cibitung yang kecil tidak menjadi alasan untuk memindahkan MM2100 ke kecamatan bernama sama pada alamat surat. Jatiuwung dan Cakung memakai industrial parcels dalam batas kecamatan, Marunda menggabungkan subset bernama yang bisa melintasi region. Hindari menjumlahkan footprint estate dengan envelope koridor.

**Rekomendasi per fasilitas:** verifikasi tenant aktif dan jenis factory/warehouse/data center; gunakan building parts/floor space dan staffing fisik bila terbit. Operator/estate-management, individual tenants dan retail pendukung harus masuk ledger unik. Tidak ada total pegawai tepercaya yang sebanding ditemukan untuk setiap estate; tabel S1 tidak boleh dibaca sebagai kekurangan pegawai yang telah terkonfirmasi.

![Industri Cikarang](organic-v41/focus_cikarang.png)

## Soekarno–Hatta

'''+table(['Metrik','Current','S0','S1 sensitivity'],[['Inhabitants dalam aerodrome',num(airport['population_current']),num(airport['population_proposed']),num(airport['population_proposed'])],['Asal pekerja model',num(airport['working_origins_current']),num(airport['working_origins_proposed']),num(airport['working_origins_proposed'])],['Jobs model',num(airport['jobs_current']),num(airport['jobs_proposed']),num(airport['jobs_pilot_s1'])],['Allocation anchors',airport['allocation_anchors_current'],airport['allocation_anchors_proposed'],airport['allocation_anchors_proposed']],['Jobs / ha aerodrome',airport['jobs_per_area_ha_current'],airport['jobs_per_area_ha_proposed'],f"{float(airport['jobs_pilot_s1'])/float(airport['area_ha']):.2f}"]])+'''\nPembagian berikut **saling eksklusif pada anchor**, sehingga tidak menambahkan staffing kantor ke tenant lagi. Pekerjaan agregat cluster tidak selalu mempunyai detail setiap subtenant. Kategori yang tak dapat dipisah tetap terlihat sebagai unclassified, bukan diberi jumlah staff rekaan.

'''+table(['Fungsi anchor','Jobs current','Jobs S0','S1 pilot','Inhabitants current→S0'],[[x['airport_role'],num(x['current_jobs']),num(x['proposed_jobs_S0']),num(x['pilot_jobs_S1']),num(x['current_population'])+' → '+num(x['proposed_population'])]for x in roles])+'''\nKargo, keamanan, airline operations, operator, retail dan ground-handling belum semuanya dapat dipisahkan dari generic building/warehouse. **Tidak teridentifikasi sebagai kategori terpisah bukan berarti pekerjanya nol.** Tidak dibuat target pegawai subfungsi yang tidak terverifikasi. Pelacakan fasilitas: [airport_facility_capacity.csv](organic-v41/airport_facility_capacity.csv).

Sumber yang berhasil diverifikasi adalah pernyataan Presiden Direktur AP II pada8Desember2022, disiarkan ANTARA, tentang komunitas pekerja harian50000–60000. Ini bukan target40000–50000payroll2025 dengan geografi yang identik. Angka harian tidak dapat dijadikan jumlah serentak dalam satu shift; pekerja bergilir/kontraktor dan fasilitas offsite belum direkonsiliasi. Tidak ada Terminal4/Cargo Village masa depan yang ditambahkan berdasarkan rencana dalam artikel itu.

S0: pulihkan6 interior hanggar pada prior transport lama150m²/relative-worker; nol inhabitants pada tank/parking/named operational anchors yang terbukti. S1: terminal80 dan hanggar100 sebagai sensitivitas, bukan global transport boost. **Airport employee commutes tetap regular job IDs**, bukan `AIR_` passenger demand. Waktu shift/akses staff memerlukan data terpisah.

Nol hit available runway/taxiway/apron masks, tetapi akses jalan privat/pintu staff belum dibuktikan untuk seluruh fasilitas. StageB wajib menggunakan sisi akses pekerja pada bangunan dan memeriksa grouping tidak melintasi fasilitas.5,104 inhabitants yang tersisa dalam aerodrome adalah flag klasifikasi residual; jangan otomatis menganggapnya residential nyata atau menghapus semua tanpa bukti.

![Bandara](organic-v41/focus_airport.png)

[Semua metrik area](organic-v41/AREA_DETAILS.md), [boundary GeoJSON](organic-v41/audit_boundaries.geojson.gz), [sensitivity ceiling](organic-v41/capacity_sensitivity.csv).
'''
 write('AIRPORT_INDUSTRIAL_EMPLOYMENT_AUDIT.md',airportdoc)
 dki=sum(int(x['working_origins_current'])for x in regional if 'Jakarta'in x['region']);bogor=next(x for x in regional if x['region']=='Bogor');city=next(x for x in regional if x['region']=='Kota Bogor');dkiage=5460000/.6475
 demotable=table(['Besaran','Nilai','Makna / sumber'],[['Seluruh inhabitants',num(32615007),'Kontrol pemda campuran2022/2025, semua umur'],['Model working trip-makers',num(12646700),f"{12646700/32615007*100:.2f}% inhabitants; bukan LFPR"],['Selisih inhabitants−model trip-makers',num(32615007-12646700),'Bukan missing workers; mencakup nonworker dan beda cakupan partisipasi'],['Workplace jobs model',num(12646700),'Harus sama dengan origin untuk skenario commute berimbang'],['BPS pekerja komuter lintas kab/kota2023',num(3614673),'Subset employed, bukan semua pekerja / total trip'],['BPS pelajar komuter lintas kab/kota2023',num(800301),'Subset perjalanan pendidikan lintaswilayah, bukan total student enrollment'],['Potential two-way commute legs',num(2*12646700),'Dua leg per modelperson jika seluruhnya berjalan; bukan daily passenger trips terukur']])
 gapdoc='# Audit selisih penduduk dan travel demand\n\n'+banner+demotable+'''\n## Apa yang dibaca engine1.7.2

Inspeksi read-only terhadap bundle terpasang menunjukkan `residenceId`, `jobId`, `size`, dan link `popIds`. Panel Residents menyaring pop pada residenceId dan Workers pada jobId; ukuran populasi pada layer itu berasal dari group yang dimuat. Stok32.615juta inhabitants berada dalam provenance alokasi, bukan layer all-population terpisah di file demand v4.

Engine mempunyai `assignCommuteTimes`, waktu keberangkatan rumah/kerja, student dampening untuk `UNI_`, airport dampening untuk `AIR_`, serta prefix perbatasan `BRD_`. Depot juga menyediakan generator special demand. Jadi **bukan benar bahwa game hanya mendukung kerja**. Namun schema yang diperiksa belum membuktikan arbitrary multi-stop trip-purpose chains. Jenis khusus masih memakai field destination bergaya jobId dan perlu metadata/schema yang sesuai. v4 saat ini memiliki0 titik dengan ketiga prefix khusus itu.

Hash bundle, field aktual serta lokasi simbol: [engine_semantics.json](organic-v41/engine_semantics.json). Full proprietary game bundles tidak disalin ke repo; hanya bukti metadata inspeksi. Engine sama sekali tidak diubah.

## Apakah partisipasi model masuk akal?

'''+table(['Wilayah / tahun','Asal pekerja model','BPS employed residents','Selisih model−BPS','Interpretasi'],[['Jakarta2025',num(dki),num(5130000),num(dki-5130000),'BPS mencakupSeribu, perbedaan survey/admin; model sekitar18%lebih rendah, bukan target workplace'],['Kab Bogor2025',num(bogor['working_origins_current']),num(2620000),num(int(bogor['working_origins_current'])-2620000),'Pop modelBogor2022; perbedaan tahun/partisipasi penting'],['Kota Bogor2025',num(city['working_origins_current']),num(507500),num(int(city['working_origins_current'])-507500),'Tabel BPS rounded/search-access; indikatif, tidak dijadikan hard control']])+f'''\nBPS Jakarta melaporkan labour-force5.46juta, TPAK64.75%, unemployment6.05%; working-age yang diturunkan dari angka dibulatkan itu sekitar{num(dkiage)} (bukan hitungan baru presisi). Kabupaten Bogor TPAK64.67%, unemployment7.69%. LFPR memakai denominator usia kerja15+, sedangkan38.78%model memakai semua umur. Informal employment nyata, tetapi residual83%model diBogor tidak dapat disamakan dengan informal share. Seluruh sumber dan cakupan pada [master](ORGANIC_V41_MASTER_AUDIT.md#provenance-dan-tingkat-kepastian).

Dataset administrasi pekerjaan DKI2025 yang tersedia hanya mencakup **{num(occupation['dataset_total'])}** catatan jiwa untuk lima kota—lebih rendah dari total kontrolRT. Di subset ini tercatat pelajar/mahasiswa{num(occupation['occupation_counts']['PELAJAR/MAHASISWA'])}, mengurus rumah tangga{num(occupation['occupation_counts']['MENGURUS RUMAH TANGGA'])}, pensiunan{num(occupation['occupation_counts']['PENSIUNAN'])}, belum/tidak bekerja{num(occupation['occupation_counts']['BELUM/TIDAK BEKERJA'])}. Ini membuktikan kategori nonkerja memang perlu dibedakan, **bukan** partisi lengkap32.615juta penduduk atau angka pengangguran Sakernas. Anak kecil/tidak bekerja, unemployed, retirees, students dan home-makers tidak boleh otomatis menjadi commuters. [Subset occupations](organic-v41/jakarta_occupation_subset.json), [sumber pemprov](../sources/government/source_manifest.json).

Tidak cukup bukti untuk mengonversi semua employed menjadi perjalanan harian fisik: kerja di rumah, tidak bekerja penuh, jadwal bergilir dan frekuensi hadir berbeda. Tabel BPS di atas memperlihatkan **risiko underrepresentation** asal pekerja, bukan izin menambah total tanpa rekonsiliasi cohort. Regional destination jobs bukan jumlah employed residents di wilayah yang sama.

## Non-work demand dan usulan konservatif

Sekolah/kuliah, belanja, kesehatan, leisure dan kunjungan lain tidak muncul sebagai purpose terpisah dalam v4. Staf universitas/rumah sakit/mall yang sudah berada dalam jobs **bukan** mahasiswa/pasien/pembeli.800301 komuter pendidikan hanya slice lintaswilayah; tidak di-ekstrapolasi menjadi seluruh school trips.

S0 mempertahankan12,646,700 working-tripmakers dan semua margin desa. Usulan tahap lanjutan: ledger terpisah `worker`, `student`, `airport_passenger` dan `other_visitor`; tiap tambahan membutuhkan enrollment/attendance, rumah asal, jadwal dan sumber denominasi yang berbeda. `UNI_` dapat diuji untuk kampus berdasarkan attendance, `AIR_` untuk penumpang bandara berdasarkan ground-access passenger data, **bukan** staff bandara. Jangan mengubah totals pekerjaan karena penambahan visitor demand, jangan menggandakan satu pegawai menjadi visitor tanpa tujuan trip berbeda yang terukur.

Skenario demografi terpisah boleh mengkalibrasi asal employed dari Sakernas yang harmonis, lalu menyetarakan tujuan pekerjaan fisik. Belum diimplementasikan atau diasumsikan dalam kandidatS0/S1. Tidak ada model-purpose framework baru yang disisipkan ke engine.
'''
 write('POPULATION_DEMAND_GAP_AUDIT.md',gapdoc)
 # candidate comparison40 isolates geography from cross fraction; point marginals validated.
 c40=load('od40/demand_checks.json');current=perf['current'];candidate=perf['S0_OD30_candidate'];cperf=perf['S0_OD40_control']
 proposal='# Proposal kalibrasi Organic v4.1\n\n'+banner+'''## Pilihan yang konkret untuk ditinjau

**Rekomendasi utama: setujui koreksi spasialS0.** Untuk OD,30% adalah opsi review yang memerlukan pilihan eksplisit;40% tersedia sebagai kontrol agar perubahan lokasi tidak tercampur dengan perubahan mobilitas. **S1 tidak direkomendasikan sebagai release default** tanpa bukti staffing fasilitas tambahan. Persetujuan S0 saja dapat mempertahankan OD40; perubahan ke OD30 harus dipilih terpisah.

'''+table(['Komponen','Current','Proposal / status'],[['Seluruh penduduk',num(32615007),'Tetap;446kontrol dan1,502desa cocok'],['Asal pekerja / jobs',num(12646700),'Tetap; regional destinations dipertahankan'],['33 anchor salah/terindikasi fungsi','Penduduk pada parkir/tangki/operasional','S0: pindah12,142inhabitants dalam desa yang sama; worker origins berpindah4,800 setelah rounding'],['HanggarCGK','0jobs pada6hangaranchor','S0:pulihkan6interior;2,200modeljobs total pada prior transport150m²'],['JobsCGK dalam aerodrome','13,500','S0:15,000; bukan klaim workforce sebenarnya'],['Jobs yang berganti anchor','—','S0:5,700 half-L1, total region tetap'],['Floor/ceiling priors','Factory75;warehouse140;transport150;ceiling2','S0 tetap;S1 sensitivity terpisah50/180/80/100'],['OD cross-region','40.00%','Review30.00% atau pertahankan40%; exact point candidates keduanya tersedia'],['Distance decay','18km','Tetap pada kandidat;12/18/30 diuji regional'],['Demografi/nonwork','Tidak lengkap','Audit/source plan saja; tidak ditambah tanpa approval dan attendance/physical-workplace data']])+'''\nS0 adalah preview yang sengaja mempertahankan cluster lama. Sebelum implementasi release, semua anggota cluster yang sumber anchornya salah fungsi perlu direklasifikasi; hindari satu anchor kantor/parkir menampung cluster mixed/hunian dari tetangganya. Tambahkan facility boundary sebagai barrier agregasi dan periksa worker-access side pada hanggar. Jika hasil rebuild mengubah lokasi atau jumlah titik, hitung ulang seluruh tabel dan minta review jika ruang lingkup berubah material; jangan menyamakan preview ini dengan release otomatis.

## OD dan definisi pembanding

BPS2023 memisahkan3,614,673 pekerja-komuter dan800,301 pelajar-komuter lintas kab/kota. Pembagian angka pekerja itu dengan total model adalah28.58%, tetapi berbeda tahun dan universe sehingga **bukan observed share untuk model2025**. Skenario30%lebih dekat secara besaran, tanpa mengklaim fit. Jumlah lintasregion30%adalah3,793,900, bukan3.6juta all-workertrips. DKI terdiri dari lima kota sehingga perjalanan JakartaSelatan→JakartaPusat juga cross-region.

'''+table(['Decay km','Cross scenario','Actual cross workers','Origin residual','Destination residual'],[[x['decay_km'],pct(x['cross_region_fraction']),num(x['cross_region_workers']),x['regional_origin_residual'],x['regional_job_residual']]for x in sens['scenarios']])+'''\nSample256per region/role membentuk kernel; region IPF+integer transport menjaga margin. Pair-level sparse min-cost matching mempertahankan semua marginpoint; cost noise6km tetap sensitivitas, bukan observed route choice. Pemilihan30% menambah diagonal preference dari baseline, sehingga self-containment lokal perlu diuji terhadap survei asal–tujuan yang harmonis. Seluruh model tidak diarahkan ke CBD: [asal Bekasi/Depok/Tangerang/Bogor→Jakarta dan lokal](organic-v41/regional_corridor_od.csv), [koridor lokal Nambo/Cikarang/BSD dan industri](organic-v41/local_corridor_od.csv). OD40 kandidat penuh mengisolasi efekS0 dari perubahan persentase.

![OD current dan review30%](organic-v41/regional_od_comparison.png)

## Kinerja dan kompatibilitas

'''+table(['Metrik','v4 produksi','S0+OD30','S0+OD40 kontrol'],[['Active engine points',current['points'],candidate['points'],cperf['points']],['Allocation anchors',115929,115935,115935],['Commuter groups',126467,126467,126467],['Gzip bytes',current['gzip_bytes'],candidate['gzip_bytes'],cperf['gzip_bytes']],['Fresh Python parse seconds',f"{current['parse_seconds']:.3f}",f"{candidate['parse_seconds']:.3f}",f"{cperf['parse_seconds']:.3f}"],['Fresh Python peakRSS MiB',f"{current['python_peak_rss_bytes_macos']/2**20:.1f}",f"{candidate['python_peak_rss_bytes_macos']/2**20:.1f}",f"{cperf['python_peak_rss_bytes_macos']/2**20:.1f}"],['In-game render/save/load','Verified1.7.2','Not run /StageA','Not run /StageA']])+f'''\nGeneration cached full-point candidateOD30:{d['seconds']:.2f}s; audit cached inventory:{audit['stage_a_seconds']:.2f}s; independent spatial/schema gate:{val['seconds']:.2f}s. Python parse measurements are one fresh process each with warm OS cache, **not game memory/FPS benchmarks**.122additional active enginepoints atOD30 arise chiefly from different pair matching/on-site split and rounding, not a point-density target. OD40 has{c40['engine_points']-78404}additional activepoints; underlying geographical anchors only add6hangars.

The production v4 game was tested1.7.2 with save/load previously. StageA intentionally does not load these candidate files into the installed city or claim proposed save/load compatibility. Static schema/link/margin checks passed forOD30; full point marginals also checked forOD40. Existing tiles/index/roads unchanged. [Performance JSON](organic-v41/performance.json), [static validation](organic-v41/validation.json).

## StageB setelah persetujuan

1. PilihS0 dan opsiOD30/OD40 secara eksplisit;S1 hanya bila disetujui sebagai eksperimen.
2. Perbaiki klasifikasi konstituen cluster, boundary fasilitas, dan entry point pekerja; pertahankan semua kontrol yang disetujui.
3. Rebuild staging, ulang conservation/geometry/OD tests serta reproducibility; simpan manifest dan rollback v4 padaSHAproduksi saat ini.
4. Install hanya hasil approved; cold-load sandbox1.7.2, Workers/Residents, poin/OD, pan/zoom, waktu/memori kualitatif;save/load dengan nama baru.
5. Perbarui metadata hanya setelah bukti UI aktual; engine tidak diubah. Perubahan demografi/regional totals/nonwork tetap butuh skenario dan approval terpisah.

Aset produksi tidak disentuh padaStageA. Hash demand tetap`8c6f5a75ec22fac174fd664359baccde19ed832c6a2dea3cb2bcd57e61fd4808`. Proteksi seluruh path game tercatat pada[completion checks](organic-v41/completion_checks.json).

## Berkas review dan reproduksi

- [Point current/S0/S1](organic-v41/point_comparison.csv.gz), [desa](organic-v41/village_comparison.csv), [kawasan](organic-v41/area_comparison.csv), [regional](organic-v41/regional_comparison.csv).
- [Kandidat alokasiS0](organic-v41/proposed_allocations.json.gz), [S1 pilot](organic-v41/pilot_allocations.json.gz).
- [Kandidat demandOD30](organic-v41/candidate-demand.json.gz), [kontrolOD40](organic-v41/od40/candidate-demand.json.gz). **Review files only; not installed.**
- [Parameter](organic-v41/scenario_parameters.json), [source evidence](organic-v41/source_evidence.json), [detail semua area](organic-v41/AREA_DETAILS.md).

Jalankan dari workspace dengan Pythonvenv yang telah tercatat: `audit.py`, `demand_preview.py`, `demand_preview.py --cross40`, `od_review.py`, `verify.py`, `diagnostics.py`, `developed_area.py`, `performance.py`, `extract_engine.mjs` (read-only dengan Node), `research_sources.py`, `final_checks.py`, lalu `reports.py` dalam`scripts/organic_v41/`. Full inventory/cluster caches4.5juta bangunan diperlukan; tidak dimasukkan ke runtime mod. Script tidak menginstal. Input caches dan versi lingkungan dicatat dalam [reproduction manifest](organic-v41/reproduction_manifest.json). Full point OD30 diregenerasi byte-identik pada seed yang sama; [hasil reproduksi](organic-v41/reproducibility.json).

[Master audit dan provenance](ORGANIC_V41_MASTER_AUDIT.md). Review dapat menyetujuiS0 saja sambil mempertahankanOD40; tidak perlu menerima intensitasS1 atau kenaikan jumlah pekerja untuk memperbaiki kesalahan lokasi.
'''
 write('ORGANIC_V41_CALIBRATION_PROPOSAL.md',proposal)
 (OUT/'README.md').write_text('# Organic v4.1 — Stage A review\n\n[Master audit](../ORGANIC_V41_MASTER_AUDIT.md), [proposal](../ORGANIC_V41_CALIBRATION_PROPOSAL.md), [all areas](AREA_DETAILS.md), [checks](completion_checks.json).\n\nProductionv4 unchanged. S0 spatial correction; S1 intensity sensitivity only. BothOD30andOD40 are non-installed review candidates. No proposed runtime verification claimed.\n')
 print('Six requested reports plus62-area detailed appendix generated')
