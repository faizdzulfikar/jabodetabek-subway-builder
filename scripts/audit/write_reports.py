"""Assemble reviewable Stage A reports from measured diagnostics."""
from baseline import *

def load(n):return json.loads((OUT/n).read_text())
def f(n):return f'{n:,.0f}'
def pct(n):return f'{100*n:.1f}%'
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |'for r in rows)+'\n'
if __name__=='__main__':
 b=load('baseline_metrics.json');a=load('proposal_checks.json');inv=load('inventory_metrics.json');qa=load('validation.json');od=load('od_scenarios.json');centers=load('center_comparison.json');regions=np.load(OUT/'baseline_arrays.npz');env=load('reproduction_environment.json');alloc=readgz(OUT/'proposed_allocations.json.gz');inp=readgz(ROOT/'assets/JKT/government_inputs.json.gz');vs={v['id']:v for v in inp['villages']}
 issues=[
 ('Geometri sel 500 m','Kode mengagregasi ke sel; histogram modulo500 memuncak di tengah. Hanya 2,29% titik tepat dekat pusat pada kedua sumbu.','Tampilan lattice terutama berasal dari centroid berbobot sel; bukan semua titik tepat di pusat.','Koordinat dari point-on-surface footprint; grid hanya untuk diagnostik.','Batas agregasi awal500m; perkecil150–250m di pusat padat setelah evaluasi.'),
 ('Inventaris bangunan ringan','Index game30.000; ekstrak audit5.111.995 footprint>=10m² sebelum batas admin/mask.','Index collision lengkap sebagai file tidak berarti inventaris kota lengkap.','Gunakan inventaris penuh offline, pertahankan index ringan terpisah.','Ambang10m² sensitif terhadap rumah kampung kecil; audit duplikat dan bagian bangunan.'),
 ('Air dan garis pantai',f"{f(qa['packaged_water_hits_baseline']['points'])} titik lama mengenai poligon air paket, memuat {f(qa['packaged_water_hits_baseline']['jobs'])} jobs.",'Sebagian centroid jatuh ke lokasi yang tidak mewakili aktivitas daratan.','Mask air daratan + laut; titik baru wajib berada dalam footprint valid.','Batas air zoom12 tergeneralisasi; periksa tepi reklamasi secara visual.'),
 ('Airside, hutan dan jalan','Lama:9 titik airside,498 hutan/wetland/nature-reserve,330 dalam8m garis tengah jalan utama normal.','Mask dan lebar proksi bisa menandai permukiman atau fasilitas sah; bukan survei lapangan.','Tolak runway/apron; tinjau overlap hutan; uji road buffers4/8/12m dan struktur bridge/tunnel.','8m adalah proksi sensitif, bukan lebar carriageway terukur.'),
 ('Campuran periode penduduk','Kontrol32.615.007; Bogor kab2022, sebagian besar lainnya2025.','Total bukan observasi serentak2025–26.','Pertahankan tahun asal per kontrol; cari pembaruan sah sebelum ekstrapolasi temporal.','Tidak menaikkan Bogor dengan persentase pertumbuhan yang diciptakan.'),
 ('Coverage tidak merata',f"52 desa tanpa footprint eligible; {a['unlocated_village_count']-52} desa tambahan tanpa kapasitas hunian; {f(a['unlocated_population'])} penduduk ditahan tanpa lokasi.",'Mengalokasikan hanya pada OSM akan menghilangkan penduduk atau memadatkannya ke fasilitas yang salah.','Ledger konservasi terpisah; fallback ke parcel developed/built-up tervalidasi di desa yang sama.','Tidak mengisi hutan/air atau desa tetangga demi menutup jumlah.'),
 ('Asal kerja lokal dan SIAK','633 desa menyimpang>max(100,10%) dari ekspektasi bobot asal; pekerjaan SIAK Jakarta tidak lengkap.','Reported occupation bukan sensus pekerja; sampling juga mengubah margin lokal.','Pisahkan inhabitants dari tripmakers; apportion margin desa dan titik secara eksak.','Preview mempertahankan margin pekerja desa lama untuk isolasi perubahan spasial; rasio0,389 masih perlu review.'),
 ('Kontrol pekerjaan historis/registrasi','JUTPI2018 diskalakan; splitDKI memakai kepesertaan perusahaan terdaftar202406.','Alamat registrasi dapat berbeda dari tempat bekerja; pusat suburban baru bisa kurang terwakili.','Redistribusi dalam region dahulu; cek pekerja per physical establishment sebelum rebalancing.','Tidak menyebut semua jobs regional sebagai jumlah pekerjaan2025 teramati.'),
 ('Lantai/tinggi tidak dipakai',f"Model lama hanya permukaan; {pct(inv['missing_levels_fraction'])} kandidat audit tidak punya levels/height.",'Footprint sama bisa mewakili rumah, gudang atau menara dengan intensitas berbeda.','Luas lantai usable + fungsi + confidence; gabungkan building parts tanpa double-count.','Level fallback dan occupancy adalah prior; wajib sensitivity, bukan fakta.'),
 ('Fungsi gedung/kompleks',f"{pct(inv['inferred_function_fraction'])} fungsi tidak eksplisit;659 parts dan30.375 nodePOI tersedia.",'Tag commercial bukan selalu kantor; mall, pabrik ber-office=company, tower/podium perlu hierarki.','Utamakan shop/industrial aktual; campuran fungsi per bagian; POI hanya join bila berada di footprint.','Preview belum join nodePOI/parts; worship dan transport dipisahkan dari hunian.'),
 ('Konsentrasi ekstrem','dp_24075 memiliki164.600 jobs; koordinatnya berada pada footprint ITC Cempaka Mas.','Overlap membuktikan lokasi mall, bukan jumlah pekerja; 1 point juga dapat mewakili beberapa bangunan.','Audit floor capacity, cluster catchment, rasio normalisasi region, dan outlier per kategori.','Tidak memotong pusat nyata dengan cap seragam hanya agar grafik terlihat rata.'),
 ('Margin tujuan lokal bergeser','TV distance lokal terhadap bobot target5,3–19,5% per region.','Sampling32 kandidat + distance decay mengubah distribusi tujuan yang sudah dirancang.','Apportion jobs titik dahulu; transport dengan margin asal/tujuan eksak.','Toleransi margin pekerja0 unit100, bukan persentase longgar.'),
 ('Jarak centroid regional','Kernel lama memakai centroid regional; preview kernel dari256 asal+256 tujuan per region.','Region luas tidak dapat diwakili satu jarak; mengganti centroid saja tidak mengkalibrasi komuter.','Integrasikan kernel lintas anchor dan uji12/18/30km.','Sampel256 adalah pendekatan numerik; naikkan512 untuk uji kestabilan StageB.'),
 ('Komuter lintas batas berlebihan','Lama8.886.200 lintas region(70,3%); pembanding2023 sekitar3,6juta komuter bekerja.','Tahun/definisi berbeda; indikasi kuat, bukan alasan memaksakan persis3,6juta.','Uji diagonal preference dengan cross-region30/40/50%, pertahankan margin13region.','40% hanya skenario review; kalibrasi final membutuhkan tabel pekerja-OD BPS yang sebanding.'),
 ('Waktu perjalanan dan validasi','Rumus1,35×jarak lurus,24km/h+180s; median59,9menit,p90132,8menit; validator lama hanya bbox.','Angka bukan waktu kemacetan terukur; grafik menarik tidak membuktikan realisme atau performa game.','Route-cost/proxy berbasis jaringan, masks, kontrol lokal, outlier, uji memori/FPS/load setelah approval.','Jangan klaim preview sudah terverifikasi in-game; tidak ada engine change.')]
 audit=f'''# Organic demand audit — Stage A

Tanggal audit:2026-11-07. Baseline:`{b['production_commit']}`. **Aset produksi tidak diubah.** Ini audit dan proposal, bukan demand pengganti yang siap dipasang.

Rekomendasi: lanjutkan metode berbasis footprint dengan konservasi administratif dan transport ber-margin eksak, tetapi selesaikan coverage, fungsi/floor-area dan kalibrasi OD sebelum memasang hasil. Menghapus grid saja tidak cukup.

## Yang sudah diperiksa

`DATA_GUIDE.md`, seluruh7 sumber pemerintah yang diminta (coverage, estimates, population controls, workplace proxies, manifest, quality issues), `demand-method.json`, `BUILD_STATUS.json`, preparasi pemerintah/WorldPop/land-use, generatorv2/v3, sampling bangunan, validator, installer dan konfigurasi mod. Sumber pemerintah ditinjau dengan keterbatasan yang sudah tercatat; tidak menghidupkan kembali tabel Bogor/Tangerang/Depok yang sebelumnya ditolak.

Engine memakai **geographic demand points** dan grup `pops` yang mereferensikan ID asal/tujuan; building index adalah aset geometri terpisah. Ini didukung [panduan custom cities resmi](https://www.subwaybuilder.com/docs/guides/custom-cities) dan jalur renderer1.7.2 `buildPopLocations` yang membaca `point.location`. Anchor tidak harus tercantum dalam index30.000 bangunan. Tidak ada alasan mengubah engine.

## Temuan terukur

{table(['Ukuran','Baseline','Preview non-produksi'],[
('Titik',f(b['points']),f(a['points'])),('Inhabitants dikontrol',f(b['population_control_total']),f(a['population_target'])+' termasuk ledger'),('Working origins terlokasi',f(b['model_tripmakers']),f(a['origins'])),('Working origins belum terlokasi','—',f(a['unlocated_working_residents'])),('Jobs dialokasikan',f(b['model_tripmakers']),f(a['destinations'])),('Penduduk belum terlokasi','Tidak diuji',f(a['unlocated_population'])),('Jobs maksimum per titik',f(b['largest_point_jobs']['jobs']),f(a['largest_anchor_jobs'])),('Jobs pada top1% titik',pct(b['top_1_percent_points_job_share']),pct(a['top_1percent_job_share'])),('Titik di footprint sumbernya','3.564 berada pada suatu footprint',f(qa['own_footprint_matches'])+' / '+f(a['points'])),('Titik mengenai air paket',f(qa['packaged_water_hits_baseline']['points']),str(qa['packaged_water_hits_proposal'])),('Kontrol penduduk resmi','446 source-level','446 eksak jika ledger dihitung'),('File produksi berubah','—',str(len(qa['production_tracked_files_changed'])))])}

21.379/24.943 titik lama berada di luar footprint terpetakan; ini **bukan** bukti semua titik tersebut berada di lokasi mustahil—parcel berkembang juga dapat menjadi anchor yang sah. Namun metode lama tidak memberi jejak bangunan/parsel. Histogram menunjukkan centroid sel; tidak tepat mengatakan semua titik lama berada tepat di tengah grid.

Preview menahan {f(a['unlocated_population'])} penduduk dan {f(a['unlocated_working_residents'])} pekerja dalam **ledger tanpa koordinat**. Lokasi mereka tidak direkayasa. Total pada peta preview karena itu lebih rendah daripada total administratif. Kontrol source-level tetap eksak dalam ledger, tetapi proposal **belum lolos konservasi geografis lengkap** untuk deployment.

## 15 masalah paling konsekuensial

Setiap baris membedakan bukti yang diamati, inferensi spasial dan asumsi model. Angka dari hasil komputasi bukan observasi jumlah pekerja di lapangan.

{table(['# / masalah','Bukti / observed','Inferensi','Koreksi spesifik','Asumsi / batas'],[[str(i+1)+' '+r[0],*r[1:]]for i,r in enumerate(issues)])}

## OD: jangan menganggap model lama terlalu lokal

Baseline hanya29,74% dalam kab/kota, bukan self-containment berlebihan. Komuter lintas region8.886.200. Jarak lurus p50/p90 adalah16,81/38,37km;3,03% melampaui50km. [Publikasi BPS2023](https://www.bps.go.id/en/publication/2024/03/28/33b6bef825944e576e7ea3ba/commuter-statistics-of-jabodetabek-results-of-jabodetabek-commuter-surveys-2023.html) mencakup mobilitas antar kab/kota. [Ringkasan pemerintah, Bab3](https://www.maritim.go.id/uploads/magazine/20241021153528-2024-10-21magazine153520.pdf) melaporkan4.414.914 komuter semua aktivitas;81,9% bekerja, sekitar3,6juta. Ini bukan total semua pekerja ataupun jumlah boarding transit; perbedaan tahun, umur, batas dan aktivitas harus disamakan sebelum fitting.

Minimum lintas region yang dipaksakan oleh ketimpangan margin saat ini adalah2.071.500 pekerja. Dua belas skenario regional mempertahankan semua margin secara eksak. Skenario review40% lintas batas berarti sekitar5,06juta, **bukan estimasi observasi2026**. Penggantian centroid oleh kernel anchor saja justru menghasilkan sekitar80% lintas region pada18km; karena itu tidak direkomendasikan tanpa kalibrasi.

![Geometri sebelum dan sesudah](organic-stage-a/geometry_diagnostics.png)
![OD regional](organic-stage-a/regional_od_comparison.png)

## Hasil dan batas penerimaan

Lihat [kalibrasi](ORGANIC_DEMAND_CALIBRATION.md), [audit employment](EMPLOYMENT_DENSITY_AUDIT.md), [hasil pemeriksaan](organic-stage-a/validation.json), [kontrol446](organic-stage-a/population_control_checks.json), [metrik baseline](organic-stage-a/baseline_metrics.json). Nol hit pada mask tersedia adalah hasil terukur terhadap dataset, bukan jaminan tidak ada air/hutan/jalan yang belum terpetakan.

StageB harus menutup ledger lokasi, memvalidasi fungsi fasilitas, menghubungkan parts/POI dan situs industri resmi, menyelesaikan OD sampai titik, lalu menjalankan verifikasi1.7.2 in-game. **Jangan deploy preview ini langsung.**
'''
 (ROOT/'docs/ORGANIC_DEMAND_AUDIT.md').write_text(audit)
 notes=[
 'Prioritas lantai menara meningkatkan bobot; cek podium, parts dan okupansi sebelum menerima lonjakan.',
 'Office corridor terdeteksi; pisahkan menara, rumah dan retail Rasuna tanpa booster seluruh kelurahan.',
 'Overlap SCBD/Kuningan; hitungan jendela tidak boleh dijumlahkan.',
 'Penurunan preview adalah flag kemungkinan office/floor coverage lemah; bukan bukti penurunan pekerjaan riil.',
 'Pertahankan footprint pabrik terpisah gudang; join526 situs industri sebagai bukti lokasi, bukan staffing.',
 'Angka jendela relatif stabil; BSD punya office/retail/institusi, jangan ratakan seluruh Serpong.',
 'Pusat suburban menguat dari geometri; validasi mall versus kantor dan area kosong.',
 'Penurunan harus diperiksa terhadap warehouse, pelabuhan dan fungsi low-rise yang kurang bertag.',
 'Pisahkan estate/factory/logistics dari rumah di Cakung; angka sama tidak membuktikan distribusi sama.',
 'Koridor retail/institusi beragam; fallback neighborhood membantu tetapi masih asumsi.',
 'Reklamasi, perairan dan perkembangan baru sensitif terhadap tanggal coastline dan coverage.',
 'Jendela sangat lebar dan menggabungkan pusat terpisah; footprint estate adalah unit yang tepat.',
 'Penurunan preview tidak boleh langsung diterima: UI, kampus, retail dan mixed towers perlu parts/POI.',
 'Pusat lokal meningkat; cek kantor/retail Summarecon dan kerja lingkungan secara terpisah.',
 'Pusat kota/institusi terwakili; jangan geser jobs dari desa Bogor yang minim mapping ke sini.']
 employment='''# Employment density audit — Stage A

Semua hitungan jobs di bawah adalah **alokasi model**, bukan jumlah pekerja teramati. Jendela audit saling tumpang tindih dan bukan batas pusat ekonomi. Tidak ada Gaussian boost, faktor multiplier berbasis nama pusat, atau bobot seragam seluruh kecamatan.

## 15 pusat prioritas

'''+table(['Prioritas / pusat','Jobs lama','Jobs preview','Perubahan','Penilaian dan tindak lanjut'],[[r['priority']+' '+r['center'],f(r['before_jobs']),f(r['proposal_jobs']),pct((r['proposal_jobs']-r['before_jobs'])/r['before_jobs']),n]for r,n in zip(centers,notes)])+'''

Total jendela tidak aditif; khusus Jatiuwung–Batuceper–Balaraja gunakan tiga subarea saat inspeksi lanjutan. Perubahan batas jendela juga dapat mengubah jumlah tanpa perubahan ekonomi. Lihat [CSV](organic-stage-a/employment_centers.csv) dan [bbox eksplisit](organic-stage-a/employment_centers.json).

## Bukti fisik, fungsi dan kapasitas

Footprint dan tag OSM merupakan bukti geometri/fungsi yang dicatat pemeta, bukan pengukuran okupansi. Point-on-surface berada di gedung sumbernya. Dalam preview, kontributor hanya diagregasi dalam fungsi dan desa yang sama dengan radius maksimum500m. Kuota jobs tetap per region. Residential/mixed use juga menerima komponen neighborhood employment20%; ini prior skenario, bukan statistik terukur.

Office, government, factory, warehouse, retail, pasar, universitas, sekolah, rumah sakit, hotel, exhibition, community dan transport dibedakan. Tag `shop=mall` mendahului `building=commercial`; `building=industrial` mendahului `office=company`. Storage tanks dan hangar airside dikeluarkan; terminal bandara diperlakukan nonhunian; tempat ibadah dan bangunan transport tidak dihitung sebagai rumah generik. Mall dengan envelope lebih dari8lantai ditandai mixed-use secara inferensial; podium/tower harus diperiksa sebelum produksi.

Potensi distorsi tersisa: banyak fungsi tidak bertag; factory1lantai dan kantor3lantai adalah fallback; parts659 belum digabung; nodePOI30.375 belum di-join; situs industri resmi belum dimasukkan kembali ke preview. Floor area yang tersedia di-normalisasi ke margin region sehingga kandidat yang jarang bisa tetap menerima terlalu banyak jobs. Karena itu outlier baru bukan kapasitas bangunan yang terukur.

ITC Cempaka Mas menerima164.600 jobs di model lama. Titik itu berada dalam footprint OSM mall13lantai; tidak ditemukan sumber staffing yang membenarkan angka tersebut. Ini contoh kebutuhan pemeriksaan fungsi campuran, luas lantai dan besaran catchment, bukan alasan menghapus konsentrasi ekonomi di sana.

## Regional: pertahankan dahulu, jangan jadikan registrasi sebagai physical census

'''+table(['Region','Asal pekerja tetap','Jobs tetap','Rasio jobs/asal'],[[str(n),f(h),f(j),f'{j/h:.2f}']for n,h,j in zip(regions['names'],regions['od'].sum(1),regions['od'].sum(0))])+'''

JUTPI2018 adalah prior historis. Jamsostek202406 mendistribusikan porsi DKI berdasarkan alamat perusahaan terdaftar, berisiko mengonsentrasikan payroll kantor pusat. JICA [Annex04 socioeconomic](https://openjicareport.jica.go.jp/pdf/12356382.pdf), Table39, merupakan sumber historis, bukan kontrol2026. Jumlah perusahaan,105 industri besar Tangerang,526 situs Bekasi dan daftar perusahaan Bekasi Kota adalah proksi keberadaan/struktur, bukan jumlah pekerja. Jangan mengubahnya menjadi staffing presisi.

Rekomendasi StageA: **tidak mengubah margin regional sekarang**. Uji redistribusi dalam region dahulu. Sebelum rebalancing, bandingkan payroll menurut alamat fisik, tenaga kerja perusahaan/kawasan, commuter workplace survey dan luas lantai aktif. Jalankan skenario pemindahan5/10/15% porsi jobs pusat ke suburban hanya bila bukti independen mendukung, dengan zero-sum regional ledger dan interval ketidakpastian. Skenario tersebut belum dijalankan dan tidak disajikan sebagai fakta.

## Cluster tambahan

Algoritme mengurutkan jobs dalam radius500m, kemudian mengambil puncak yang terpisah minimal2,5km. Ini menemukan konsentrasi **model**, bukan pusat nyata yang sudah terverifikasi. [Daftar30 cluster](organic-stage-a/discovered_clusters.json) mencatat koordinat, region, desa dan apakah berada di jendela prioritas. Kandidat di luar jendela perlu penamaan/verifikasi manual terhadap fungsi bangunan; jangan otomatis menambahkan booster dari puncak model sendiri.

## Visual untuk pemeriksaan

![Pusat kantor](organic-stage-a/focus_cbd.png)
![Industri Cikarang](organic-stage-a/focus_cikarang_industrial.png)
![BSD](organic-stage-a/focus_bsd_mixed_urban_fabric.png)

Simbol dan skala warna identik untuk before/after; jumlah per titik adalah agregat, bukan karyawan gedung anchor. Footprint abu-abu memberikan konteks fisik. Sumbu lon/lat; lokasi dapat dicocokkan melalui OSM ID pada allocation JSON.
'''
 (ROOT/'docs/EMPLOYMENT_DENSITY_AUDIT.md').write_text(employment)
 params={'stage':'A_PROPOSAL_NOT_APPROVED_FOR_PRODUCTION','seed':20261107,'crs_allocation':'EPSG:32748','crs_output':'EPSG:4326','building_min_footprint_m2':10,'anchor_target_before_category_and_radius_reservations':60000,'cluster_max_radius_m':500,'cluster_constraints':['same administrative village','same inferred/explicit function','actual building point-on-surface'],'residential_sqm_per_person':{'dense_lowrise':18,'other_lowrise':25,'sparse_periurban_rural':30,'apartments':32},'usable_floor_factor':.8,'residential_share_lowrise_apartment':.95,'mixed_residential_share':.6,'employment_sqm_per_worker_prior':{'office':20,'government':25,'factory':75,'warehouse':140,'retail':35,'market':45,'university':50,'school':70,'hospital':45,'hotel':100,'exhibition':140,'community':100,'transport':150,'mixed':40},'employment_neighborhood_mixture':.2,'od_distance_km_scenarios':[12,18,30],'od_cross_region_fraction_scenarios':[.3,.4,.5],'regional_controls':'baseline unchanged','population_rounding':'largest remainder per kecamatan; direct village counts unchanged','population_unlocated_policy':'retain explicit ledger; do not move to neighboring village or nonresidential-only buildings'};params['fallback_levels']={'unknown_lowrise':1.5,'residential':1.5,'apartments':6,'office':3,'government':2,'factory':1,'warehouse':1,'retail':2,'market':1,'university':3,'school':2,'hospital':4,'hotel':4,'mixed':2,'exhibition':1};dump('proposed_parameters.json',params)
 cal=f'''# Organic demand calibration — proposal Stage A

**Status: minta persetujuan metode, bukan persetujuan memasang preview saat ini.** Tidak ada perubahan aset game atau engine. TahapB baru boleh melakukan rebuild dan uji game sesudah disetujui.

## Desain yang diusulkan

1. Inventaris penuh OSM offline; deduplikasi parent/part dan multi-relation. Simpan provenance OSM ID, tanggal sumber, fungsi observed/inferred, levels observed/inferred, admin ID dan confidence.
2. Utamakan footprint dan fungsi nyata. Join nodePOI hanya bila berada di footprint yang cocok; jangan tempelkan POI ke bangunan terdekat tanpa uji containment. Untuk parts, union per floor band/parent agar podium dan tower tidak dihitung dua kali.
3. Estimasi usable residential/employment floor area dengan kategori fungsi. Gunakan kepadatan lingkungan sebagai inferensi morphology; bentuk cluster jalan/parsel dibutuhkan untuk membedakan kampung dan perumahan terencana secara lebih baik.
4. Distribusikan penduduk menurut kontrol paling rinci yang reliabel. 317 kelurahan langsung tetap;129 kecamatan menjadi batas keras bagi1.185 estimasi desa. Preview mempertahankan estimasi desa sebelumnya, hanya membulatkan dalam kecamatan dengan largest remainder; perubahan antar desa memerlukan coverage audit dan sensitivity.
5. Pilih anchor deterministik dari **bangunan nyata**, weighted priority sampling dengan seed20261107, reservasi tiap fungsi/desa dan tambah anchor untuk catchment jauh. Tidak memakai jitter, fixed spacing atau centroid grid. Histogram fase datar bukan target optimasi; bukti berasal dari geometri dan aktivitas yang masuk akal. Grid boleh untuk QA, tidak menentukan koordinat.
6. Agregasi kapasitas hanya dalam fungsi dan desa yang sama; radius preview maksimal500m. Produksi sebaiknya adaptif150–250m di pusat padat dan hingga500m di rural, ditambah barrier jalan/sungai/estate agar tidak berpindah antar kompleks. Jangan menyamakan ukuran semua bangunan.
7. Tetapkan inhabitants per point dalam unit1, working origins/jobs dalam unit100 secara largest remainder; keduanya konsep berbeda. Prior kerja lingkungan20% dari margin jobs melengkapi fungsi terpetakan; uji10/20/30%, bukan menganggapnya nilai observasi.
8. Susun OD regional dari distribusi anchor; kalibrasi deterrence dan lintas-batas menurut populasi survei yang sebanding. Selesaikan transport sampai titik dengan margin eksak sebelum membuat `pops`.

## Parameter preview dan ketidakpastiannya

[JSON parameter](organic-stage-a/proposed_parameters.json) merekam koefisien. Semua intensitas di bawah adalah **prior modelling relatif**, bukan angka lapangan Jabodetabek.

{table(['Komponen','Nilai preview','Sensitivity / pekerjaan StageB'],[
('Usable floor area','footprint × levels ×0,8','0,7/0,8/0,9; cek bagian gedung dan fungsi aktif'),('Levels bila hilang','lowrise1,5;apartment6;office3;factory/warehouse1;government/school2;hospital/hotel4','0,5×/1×/2× inferred floor area; jangan ubah levels observed tanpa alasan'),('Hunian','95% usable lowrise/apartment;60% mixed','Hunian aktif/occupancy tidak diketahui; uji0,8–1 faktor tambahan'),('Dense lowrise','18m²/person jika footprint<150m² dan radius8 tetangga<50m','Inferensi morphology; bukan label kampung teramati'),('Lowrise lain / sparse / apartment','25 /30 /32m²/person','Uji±25%; apartment tidak otomatis lebih padat daripada kampung'),('Office / government','20 /25m² per relative worker','12–30 /18–40'),('Factory / warehouse','75 /140m²','40–120 /80–220; tenaga kerja per perusahaan bila tersedia'),('Retail / market','35 /45m²','20–70 /25–90; pisahkan podium dan area sirkulasi'),('University / school / hospital','50 /70 /45m²','30–100 /40–120 /30–90; jangan hitung mahasiswa/pasien sebagai workers'),('Hotel / exhibition','100 /140m²','Hotel idealnya beds/rooms dan kelas layanan; hall tidak seperti kantor'),('Neighborhood jobs','20% regional jobs melalui residential capacity','10/20/30%; bukan survei informal sector'),('Road mask','8m dari centerline major/highway normal','4/8/12m; bridge/tunnel dibedakan'),('Road access','Jarak ke semua ruas dipantau; tidak otomatis drop>250m','Private/local roads tidak lengkap; buat fallback entrance/parcel dahulu'),('Anchor count',f(a['points']),'Bandingkan sekitar40k/60k/80k dengan displacement berbobot dan game performance')])}

[Employment Density Guide2015 dari HCA pada situs Westminster](https://www.westminster.gov.uk/sites/default/files/media/documents/Employment%20density%20guide%20%28Homes%20and%20Communities%20Agency%2C%20November%202015%29.pdf) menunjukkan bahwa densitas berbeda menurut fungsi dan basis area. Benchmark luar negeri ini hanya pemeriksaan kewajaran metode; koefisien preview di atas bukan angka yang diambil sebagai observasi Jakarta, dan NIA/GIA/GEA tidak boleh dicampur begitu saja.

## Fallback coverage dan konservasi

Inventaris audit memiliki5.111.995 footprint>=10m² di ekstrak complete-ways, termasuk bangunan di luar admin yang ikut tersalin. Setelah admin/mask pantai terdapat sekitar4,50juta kandidat sebelum koreksi fungsi tambahan. Jumlah ini tidak sama dengan bangunan game30.000 maupun hitungan preparasi lama yang memakai filter lain.

{f(a['unlocated_population'])} penduduk dan {f(a['unlocated_working_residents'])} pekerja di{a['unlocated_village_count']} desa belum memiliki lokasi yang layak:52 tanpa footprint eligible dan sisanya tanpa kapasitas hunian yang teridentifikasi. Mereka berada dalam `unlocated_allocations`; tidak ditempatkan di pabrik/tempat ibadah hanya untuk menutup total.

Urutan penyelesaian setelah approval: validasi batas admin dan footprint; cari developed residential parcels/kompleks yang nyata; periksa coverage built-up dan hunian dengan sumber citra/permukiman bertanggal; gunakan titik dalam **parcel developed yang terhubung jalan**, di luar carriageway/mask, masih di desa kontrol yang sama. Bila buktinya belum cukup, ledger tetap pending dan build produksi gagal dengan alasan eksplisit. Jangan pindahkan ke desa tetangga atau ratakan seluruh poligon. Lapisan built-up historis hanya fallback evidence dan harus diberi tahun, bukan dianggap2026 otomatis.

**Kontrol446 dan total32.615.007 sudah eksak ketika ledger dihitung.** Titik terlokasi sendiri hanya{f(a['population'])} inhabitants dan{f(a['origins'])} origins; sehingga preview tidak memenuhi deploy gate “semua demand mempunyai geografi”. Jobs12.646.700 tetap eksak di13region. [Hasil kontrol](organic-stage-a/population_control_checks.json) membedakan `located` dari `allocated_including_unlocated`.

## OD yang diusulkan dan yang benar-benar dihitung

Dihitung:12 matriks13×13; decay12/18/30km, tanpa penyesuaian serta target lintas batas30/40/50%. Kernel memakai256 sampel proportional-to-mass dari home/jobs anchor tiap region, bukan jarak antar centroid. IPF memastikan margin; LP rounding pada unit100 mempertahankan total baris/kolom eksak. Jumlah lintasregion minimum dari ketimpangan margin2.071.500.

{table(['Skenario','Lintas region','Diagonal multiplier','P50 / P90 jarak bersyarat km'],[[s['id'],pct(s['cross_region_fraction']),f"{s['diagonal_multiplier']:.2f}",' / '.join(f'{v:.1f}'for v in s['conditional_sample_distance_km_p50_p90'])]for s in od['scenarios']])}

Jarak pada tabel adalah distribusi **sampel pasangan bersyarat** yang dibobot OD regional; bukan micro-OD yang mempertahankan margin setiap point. Jangan membandingkannya sebagai perbaikan tervalidasi terhadap OD lama. Asal{f(a['unlocated_working_residents'])} yang belum terlokasi juga belum terwakili di kernel spasial. Tidak ada `pops` baru yang dibuat.

Rekomendasi review:`tau18_cross40`, sambil memeriksa30/50% dan tabel BPS.40% adalah pilihan sensitivitas yang disengaja, bukan fitted estimate2026. Preferensi diagonal tidak boleh menjadi satu-satunya cara kalibrasi: orang yang tinggal dan bekerja dekat perbatasan region tetap perlu trips lintas batas yang murah. StageB perlu jaringan/biaya dan observed OD agar efek administratif tidak menciptakan discontinuity.

Transport StageB yang mempertahankan semua margin: (a) tiap origin-region membagi supply point ke13 job-region dengan quota OD regional; (b) tiap job-region membagi demand point ke13 origin-region dengan quota yang sama; (c) dalam setiap pasangan region, cocokkan supply/demand teralokasi melalui sparse min-cost transport, menambah edges bila tidak feasible. Dengan demikian point home/jobs dan13×13 quota tidak bergeser oleh sampling. Simpan seed, cost, tie-break dan integer unit. Uji flows Depok/Bekasi→Jakarta, Tangerang/Tangsel→CBD/lokal, residential→Cikarang, BSD/Alam Sutera serta cross-suburban tanpa CBD; jangan menetapkan flows tersebut sebagai observasi.

Driving distance/time lama tetap proksi, bukan routing. Proposal StageB memakai jaringan jalan dan penalti akses/kemacetan yang dikalibrasi; bila belum tersedia, tampilkan status proxy secara eksplisit dan uji detour1,2/1,35/1,6 serta kecepatan18/24/30km/h. Tidak menafsirkan waktu sintetis sebagai pengukuran perjalanan.

## Performa dan kompatibilitas1.7.2

{table(['Pemeriksaan','Hasil / batas'],[
('Anchor count',f(a['points'])+f" ({a['points']/b['points']:.2f}× baseline)"),('JSON allocation dengan metadata',f(qa['proposed_allocation_json_bytes'])+' bytes'),('Gzip allocation',f(qa['proposed_allocation_gzip_bytes'])+' bytes'),('Parse JSON Python,3run',' / '.join(f'{x:.3f}s'for x in qa['allocation_json_parse_seconds_three_runs'])),('Ekstraksi inventaris penuh','503,1s; scratchSQLite~813MB; tidak dimasukkan paket game'),('Klasifikasi+preview full run teramati','sekitar124s sebelum koreksi/coast/cached pass; bukan benchmark game'),('Cached allocation terakhir',f"{a['seconds']:.1f}s; peak RSS {a['peak_rss_bytes_macos']/1024**3:.2f}GiB"),('Index bangunan / PMTiles','Tidak dibesarkan atau diubah'),('Engine schema','points[id,location,jobs,residents,popIds]; pops[id,size,residenceId,jobId,drivingSeconds,drivingDistance]'),('Bukti runtime baru','Belum ada; StageA tidak memasang demand atau memodifikasi engine')])}

Jumlah anchor baru mengurangi displacement dan mempertahankan fungsi; tidak ada hard engine limit yang ditemukan dalam pemeriksaan format, tetapi itu **bukan jaminan** performa. Allocation JSON berisi provenance dan ledger, bukan format demand engine. Jangan salin file ini ke `demand_data.json.gz`. `population` metadata tidak boleh dimasukkan sebagai working `residents` secara langsung.

Gate StageB: unique IDs/valid references, point totals sama dengan pop-derived totals, exact source-level population dan point/regional OD margins; seluruh ledger lokasi selesai; zero unreviewed mask hits; documented job outliers; reproducibility byte-identical asset; lalu uji load/save, worker/resident overlays, memory, pan/zoom dan frame time pada skenario40k/60k/80k. Laporkan hasil aktual; jangan menjanjikan FPS dari benchmark Python.

## Reproduksi dan deliverables

Snapshot OSM:[Geofabrik Java](https://download.geofabrik.de/asia/indonesia/java.html),2026-11-05T21:23:02Z. SHA256 PBF:`{env['pbf']['sha256']}`. OSM©OpenStreetMap contributors, ODbL; attribution tetap diperlukan. [Environment dan versi](organic-stage-a/reproduction_environment.json). Source download/raw full inventory tetap di scratch, tidak menambah ukuran aset game.

Dari workspace, gunakan Python environment dengan versi paket pada environment JSON:

```sh
osmium extract --strategy=complete_ways --bbox=106.30,-6.85,107.35,-5.90 work/organic-audit/java.osm.pbf -o work/organic-audit/jabodetabek.osm.pbf
osmium tags-filter work/organic-audit/jabodetabek.osm.pbf wr/building wr/building:part wr/landuse wr/natural wr/leisure wr/aeroway wr/amenity wr/office wr/shop wr/tourism n/amenity n/office n/shop n/tourism -o work/organic-audit/activity.osm.pbf
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/audit/extract_inventory.py work/organic-audit/activity.osm.pbf work/organic-audit/inventory.sqlite
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/audit/baseline.py
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/audit/water_mask.py work/organic-audit/packaged_water.wkb
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/audit/propose.py work/organic-audit/inventory.sqlite
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/audit/od_preview.py
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/audit/visualize.py work/organic-audit/inventory.sqlite
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/audit/verify_stage_a.py work/organic-audit
work/map-venv/bin/python outputs/jabodetabek-mod/scripts/audit/write_reports.py
```

`extract_inventory.py` menolak append keDB yang sudah ada. Untuk rerun allocation memakai kandidat scratch yang sama, tambahkan `--reuse`. Baseline hash manifest harus dibuat sebelum perubahan dari tracked files commit baseline;44 hash awal diperiksa ulang oleh verifier. Semua output proposal berada di `docs/organic-stage-a`, bukan `assets/`.

File utama: [allocationsJSON.gz](organic-stage-a/proposed_allocations.json.gz), [ringkasan desaCSV](organic-stage-a/proposed_village_allocations.csv), [parameterJSON](organic-stage-a/proposed_parameters.json), [skenarioOD dan keterbatasan](organic-stage-a/od_scenarios.json), [validasi](organic-stage-a/validation.json), [coverage gaps](organic-stage-a/coverage_gaps.csv) dan [uji determinisme](organic-stage-a/reproducibility.json). `baseline_arrays.npz`, `proposed_arrays.npz` dan `od_scenarios.npz` menyimpan arrays untuk reproduksi grafik. Ledger lokasi berada di allocationJSON; confidence function/levels dan OSM ID ada pada setiap anchor. Metadata kapasitas adalah agregat cluster, bukan estimasi staffing gedung anchor tunggal.

![Metropolitan preview](organic-stage-a/metro_before_after.png)
![Kampung padat](organic-stage-a/focus_dense_kampung.png)
![Periurban](organic-stage-a/focus_peri-urban_south_bogor.png)

Persetujuan yang diminta: lanjutkan StageB untuk melengkapi coverage/fungsi dan menerapkan metode konservatif ini, dengan validasi sebelum penggantian aset. Preview dan angka distribusi lokal belum dianggap final. Instruksi pengguna sendiri mensyaratkan “StageB—Implementation after approval”; karena itu rebuild produksi dan in-game verification belum dilakukan.
'''
 (ROOT/'docs/ORGANIC_DEMAND_CALIBRATION.md').write_text(cal)
 (OUT/'README.md').write_text('''# Stage A — review bundle

Mulai dari [audit utama](../ORGANIC_DEMAND_AUDIT.md), [employment](../EMPLOYMENT_DENSITY_AUDIT.md) dan [metode](../ORGANIC_DEMAND_CALIBRATION.md).

Semua file di sini adalah diagnostik/proposal non-produksi. Allocation JSON bukan demand engine yang siap dipasang. Penduduk tanpa bukti lokasi dipertahankan dalam ledger; lihat `validation.json` dan `unlocated_allocations`.

Grafik memakai skala simbol/warna yang sama pada before/after. Pusat audit saling overlap; angka jobs adalah hasil model, bukan observasi staffing. OD sampai tingkat regional saja; point-level OD serta game testing menunggu StageB.
''')
 print('three reports and review index written')
