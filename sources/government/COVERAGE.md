# Data pemda dan estimasi wilayah

Versi 3 memakai data pemda untuk penduduk. Jumlah dan lokasi pekerjaan yang belum tercatat lengkap tetap berupa estimasi; tabel ini tidak menyatakan sensus tempat kerja lengkap.

| Wilayah | Tahun penduduk | Rincian sumber | Penduduk |
|---|---|---|---:|
| Bekasi | 2025 | 23 kecamatan | 3,469,242 |
| Bogor | 2022 | 40 kecamatan | 5,473,476 |
| Kota Bekasi | 2025 | 56 kelurahan | 2,595,927 |
| Kota Bogor | 2025 | 6 kecamatan | 1,156,543 |
| Kota Depok | 2025 | 11 kecamatan | 2,038,354 |
| Kota Jakarta Barat | 2025 | 56 kelurahan | 2,525,856 |
| Kota Jakarta Pusat | 2025 | 44 kelurahan | 1,034,626 |
| Kota Jakarta Selatan | 2025 | 65 kelurahan | 2,297,065 |
| Kota Jakarta Timur | 2025 | 65 kelurahan | 3,188,091 |
| Kota Jakarta Utara | 2025 | 31 kelurahan | 1,805,579 |
| Kota Tangerang | 2025 | 13 kecamatan | 1,976,599 |
| Kota Tangerang Selatan | 2025 | 7 kecamatan | 1,486,118 |
| Tangerang | 2025 | 29 kecamatan | 3,567,531 |

317 kelurahan mempunyai kontrol penduduk langsung. 1.185 desa/kelurahan lain diestimasi dari total kecamatan dengan proporsi raster WorldPop 100 m. Hasilnya diringkas ke grid500 m. Total setiap unit sumber tetap dipertahankan. Batas desa/kelurahan memakai layanan BIG Juni2026; kecocokan nama/kode diperiksa sebelum model dibuat.

Residents di game mewakili pekerja model, bukan semua penduduk. Bobot pekerja memakai pekerjaan SIAK Jakarta dan Tangsel jika tersedia. Untuk wilayah lain, rasio partisipasi diperkirakan dari median sumber yang tersedia. Dataset pekerjaan Jakarta tidak mencakup seluruh populasi pada tabel RT, sehingga tidak dianggap sensus tenaga kerja lengkap.

## Tempat kerja

- Jakarta: pembagian pekerjaan antarkota memakai proporsi anggota Jamsostek pada perusahaan terdaftar2024. Kantor pendaftaran bisa berbeda dari tempat kerja fisik; jumlah keanggotaan tidak ditambahkan sebagai pekerjaan baru.
- Kabupaten Bekasi:526 titik industri dari Satu Peta, memakai jumlah lokasi sebagai bobot tanpa mengarang jumlah pegawai per perusahaan. Koordinat identik dideduplikasi.
- Kota Bekasi:daftar industri2025 dikelompokkan menurut kecamatan, bukan diperlakukan sebagai hitungan pegawai.
- Kota Tangerang:sebaran105 industri besar menurut kecamatan2023 menjadi salah satu bobot lokasi industri.
- Wilayah lain:lokasi rinci tetap diestimasi dengan lahan komersial/industri OSM dan sebaran penduduk. Data izin pembangunan, lowongan, pencari kerja, dan peserta pelatihan tidak dianggap sebagai pekerjaan yang sudah ada.

Total pekerjaan antarkabupaten/kota masih memakai proporsi historis JUTPI2018, disesuaikan ke total pekerja model. Jadi belum seluruh pekerjaan berasal dari hitungan tempat kerja pemda terkini. Hubungan rumah–kerja dan waktu berkendara juga masih dimodelkan.

## Pemeriksaan dan sumber

- Semua446 kontrol penduduk dan total hasil pembagian lulus pemeriksaan.
- Semua13 total asal/tujuan model cocok dengan hasil demand yang ditulis.
- `population_controls.json`:angka sumber, periode, dan penanda turunan.
- `kelurahan_estimates.csv`:penduduk, pekerja model, dan pekerjaan estimasi per desa/kelurahan.
- `source_manifest.json`:produsen, URL, tingkat rincian dan hash unduhan.
- `quality_issues.json`:tabel yang ditolak serta keterbatasan data.

Tabel kepadatan Kabupaten Tangerang dan dataset17266 Kabupaten Bogor ditolak karena angka bergeser terhadap nama kecamatan. Untuk Kota Tangerang, Larangan dihitung sebagai sisa total kota karena kecamatannya hilang dari tabel cetak; statusnya ditandai turunan.
