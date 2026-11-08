# Audit kepadatan pekerjaan v4.1

**Stage A — audit dan proposal, 8 November 2026. Belum diinstal dan belum diuji di game.** Produksi tetap Organic v4 / mod 0.2.1, commit `dfec7f2`. Tidak ada perubahan engine, peta, atau aset game.

Angka “penduduk” di dokumen ini adalah seluruh inhabitants; “asal pekerja” adalah model working trip-makers; “jobs” adalah estimasi tujuan kerja. S0 adalah koreksi klasifikasi konservatif. S1 adalah sensitivitas intensitas, **bukan** target pegawai hasil observasi. OD30 dan OD40 adalah skenario terpisah dari koreksi geografis S0.

Batas kecamatan/desa memakai union batas BIG Juni 2026. Kompleks industri memakai poligon OSM bernama; koridor bisnis memakai potongan poligon aktivitas dalam jendela audit. BSD/Gading Serpong/Alam Sutera/Sentul memiliki subset hunian terpetakan atau envelope administratif yang dilabeli: tidak diklaim sebagai batas legal township lengkap. Area tumpang tindih **tidak boleh dijumlahkan**. [Semua batas dan label cakupan](organic-v41/audit_boundaries.geojson.gz).

Audit v4 terdahulu diarsipkan [di sini](organic-v41/archive_v4_EMPLOYMENT_DENSITY_AUDIT.md). Kode aktif yang diperiksa adalah `scripts/organic/allocate.py`, `enrich.py`, `calibrate_jobs.py`, dan `demand.py`, bukan generator grid v3.

## Konsentrasi pusat metropolitan

Angka berikut memakai **core aktivitas terpetakan**, bukan seluruh kecamatan maupun batas township legal. Residential mixed-use corridors yang tidak bertag aktivitas dapat berada di luar core; semua metrik lengkap dan kepastian batas ada di [AREA_DETAILS](organic-v41/AREA_DETAILS.md). Jobs/ha memakai luas poligon, bukan floor-space intensity.

| Pusat | Populasi current→S0 | Asal pekerja current→S0 | Jobs current→S0 | Jobs S1 pilot | Jobs/ha current→S0 |
|---|---|---|---|---|---|
| Sudirman–Thamrin–SCBD | 68,071 → 68,153 | 29,600 → 29,600 | 824,600 → 824,300 | 824,300 | 1114.97 → 1114.57 |
| Kuningan–Mega Kuningan–Rasuna Said | 22,667 → 22,667 | 9,500 → 9,500 | 320,100 → 320,100 | 320,100 | 1317.01 → 1317.01 |
| Gatot Subroto–Semanggi | 30,694 → 30,683 | 13,000 → 13,000 | 494,800 → 494,500 | 494,600 | 1034.85 → 1034.22 |
| TB Simatupang–Cilandak | 23,576 → 23,554 | 9,200 → 9,200 | 137,900 → 137,900 | 138,000 | 393.42 → 393.42 |
| Cikarang–Cibitung–MM2100–Jababeka | 57,720 → 57,720 | 19,500 → 19,500 | 385,900 → 385,900 | 414,200 | 50.4 → 50.4 |
| BSD–Serpong | 26,718 → 26,740 | 9,600 → 9,600 | 135,100 → 135,100 | 135,400 | 234.64 → 234.64 |
| Alam Sutera–Gading Serpong | 22,058 → 22,064 | 8,600 → 8,600 | 153,400 → 153,400 | 153,300 | 248.7 → 248.7 |
| Sunter–Kelapa Gading | 64,151 → 64,151 | 24,800 → 24,800 | 260,700 → 260,900 | 262,600 | 160.7 → 160.82 |
| Cakung–Pulogadung | 38,832 → 38,832 | 13,700 → 13,700 | 183,000 → 183,100 | 186,800 | 84.49 → 84.54 |
| Slipi–Palmerah–Grogol | 67,162 → 67,162 | 28,700 → 28,700 | 146,200 → 146,300 | 146,200 | 411.58 → 411.86 |
| Pluit–PIK–Penjaringan | 49,124 → 47,828 | 18,300 → 17,800 | 155,900 → 155,800 | 154,600 | 164.55 → 164.44 |
| Jatiuwung–Batuceper–Balaraja | 90,157 → 87,940 | 32,600 → 31,700 | 327,800 → 329,200 | 339,500 | 52.52 → 52.75 |
| Margonda–Depok | 15,188 → 15,188 | 5,000 → 5,000 | 36,100 → 36,100 | 36,200 | 239.56 → 239.56 |
| Bekasi Selatan–Summarecon | 53,154 → 53,154 | 21,400 → 21,400 | 78,300 → 78,300 | 78,300 | 205.31 → 205.31 |
| Bogor Tengah–Baranangsiang | 22,102 → 22,102 | 9,200 → 9,200 | 42,800 → 42,800 | 43,000 | 227.82 → 227.82 |

## Mengapa fallback bisa mengencerkan pusat kerja

Aturan v4 aktual: `floor = min(0.8 × regional_jobs × capacity / sum_capacity, 2 × capacity)`. Sisa dibagi memakai kapasitas residential/mixed. Minimum residual20% timbul dari desain80/20; saat coverage workplace tipis, residual menjadi jauh lebih besar. Ini **prior lokasi untuk pekerjaan tak terklasifikasi**, bukan pengukuran share informal/home-working. Tidak semua pekerjaan yang menempel residential benar-benar berada di rumah.

| Region | Jobs current=S0 | v4 neighborhood-prior share | S0 share | S1 pilot share | S0 jobs dipindah |
|---|---|---|---|---|---|
| Bekasi | 1,255,400 | 56.9% | 56.9% | 54.7% | 0 |
| Bogor | 1,963,600 | 83.3% | 83.3% | 82.8% | 0 |
| Kota Bekasi | 840,200 | 73.5% | 73.5% | 73.4% | 0 |
| Kota Bogor | 437,400 | 63.4% | 63.4% | 63.1% | 0 |
| Kota Depok | 529,100 | 66.2% | 66.2% | 66.3% | 0 |
| Kota Jakarta Barat | 634,000 | 20.0% | 20.0% | 20.0% | 0 |
| Kota Jakarta Pusat | 1,199,200 | 22.4% | 22.4% | 22.4% | 800 |
| Kota Jakarta Selatan | 2,080,800 | 43.8% | 43.8% | 43.8% | 1,000 |
| Kota Jakarta Timur | 582,700 | 26.1% | 26.2% | 25.5% | 700 |
| Kota Jakarta Utara | 706,600 | 20.0% | 20.0% | 20.0% | 600 |
| Kota Tangerang | 852,700 | 73.5% | 73.3% | 72.2% | 2,200 |
| Kota Tangerang Selatan | 522,100 | 49.9% | 49.9% | 48.7% | 0 |
| Tangerang | 1,042,900 | 47.3% | 47.3% | 46.9% | 400 |

S0 tidak mengganti pembagian total regional. Dampak5700jobs hanya koreksi fasilitas/titik dan pembulatan ulang. S1 mengubah4,472 kapasitas fasilitas bertag: factory75→50m²/model-worker, warehouse140→180, terminal150→80, hanggar150→100. Nilai itu **asumsi sensitivitas**, bukan employee-per-building yang teramati; inferred factory dari industrial landuse tidak otomatis dinaikkan. Perubahan ini belum cukup menutup kekurangan bukti pekerjaan di Kabupaten Bogor atau membuktikan workforce Jababeka.

`function_observed` di provenance v4 sering berarti tag bangunan non-generik; itu bukan observasi staf. `capacity_mix` adalah kapasitas relatif konstituen cluster, bukan hitungan pekerjaan per fungsi yang diamati. Perbandingan floor/neighborhood dipisah menurut flag dalam [employment_evidence_components.csv](organic-v41/employment_evidence_components.csv). Memakai footprint nyata tidak membuat angka staffing menjadi observed.

## Fungsi dan intervensi yang tepat

| Fungsi | v4 m² / relative worker | Intervensi proposal |
|---|---|---|
| Corporate offices | 20 | Pertahankan; perbaiki lantai/parts dari bukti gedung, jangan blanket CBD multiplier |
| Government | 25 | Alamat instansi dan lantai; jangan ikutkan semua warga administratif |
| Factory | 75 | S0 tetap; S1=50 hanya tag positif, uji tenaga kerja fasilitas |
| Warehouse / logistics | 140 | S0 tetap; S1=180, bukan factory intensity |
| Retail / mall | 35 | Bedakan podium retail dari tower mixed-use; no arbitrary mall staffing target |
| Traditional market | 45 | Gunakan pasar nyata, hindari duplikasi toko dan polygon pasar |
| University / school | 50 / 70 | Untuk staf; enrolment pelajar bukan jobs staf |
| Hospital | 45 | Staf saja; patient trips perlu ledger berbeda |
| Hotel | 100 | Staf; bukan occupancy pengunjung |
| Transport | 150 | Hanggar CGK dipulihkan pada S0; airport-specific intensities hanya S1 |
| Neighborhood / informal | Residual regional | Tetap ada; tidak dihapus hanya untuk membesarkan CBD |
| Generic large mixed | 60%res /40%activity | Inferred; perlu screening fasilitas operasional/tangki/parkir |

## Diagnosis sumber underrepresentation

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
