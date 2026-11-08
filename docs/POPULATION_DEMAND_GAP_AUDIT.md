# Audit selisih penduduk dan travel demand

**Stage A — audit dan proposal, 8 November 2026. Belum diinstal dan belum diuji di game.** Produksi tetap Organic v4 / mod 0.2.1, commit `dfec7f2`. Tidak ada perubahan engine, peta, atau aset game.

| Besaran | Nilai | Makna / sumber |
|---|---|---|
| Seluruh inhabitants | 32,615,007 | Kontrol pemda campuran2022/2025, semua umur |
| Model working trip-makers | 12,646,700 | 38.78% inhabitants; bukan LFPR |
| Selisih inhabitants−model trip-makers | 19,968,307 | Bukan missing workers; mencakup nonworker dan beda cakupan partisipasi |
| Workplace jobs model | 12,646,700 | Harus sama dengan origin untuk skenario commute berimbang |
| BPS pekerja komuter lintas kab/kota2023 | 3,614,673 | Subset employed, bukan semua pekerja / total trip |
| BPS pelajar komuter lintas kab/kota2023 | 800,301 | Subset perjalanan pendidikan lintaswilayah, bukan total student enrollment |
| Potential two-way commute legs | 25,293,400 | Dua leg per modelperson jika seluruhnya berjalan; bukan daily passenger trips terukur |

## Apa yang dibaca engine1.7.2

Inspeksi read-only terhadap bundle terpasang menunjukkan `residenceId`, `jobId`, `size`, dan link `popIds`. Panel Residents menyaring pop pada residenceId dan Workers pada jobId; ukuran populasi pada layer itu berasal dari group yang dimuat. Stok32.615juta inhabitants berada dalam provenance alokasi, bukan layer all-population terpisah di file demand v4.

Engine mempunyai `assignCommuteTimes`, waktu keberangkatan rumah/kerja, student dampening untuk `UNI_`, airport dampening untuk `AIR_`, serta prefix perbatasan `BRD_`. Depot juga menyediakan generator special demand. Jadi **bukan benar bahwa game hanya mendukung kerja**. Namun schema yang diperiksa belum membuktikan arbitrary multi-stop trip-purpose chains. Jenis khusus masih memakai field destination bergaya jobId dan perlu metadata/schema yang sesuai. v4 saat ini memiliki0 titik dengan ketiga prefix khusus itu.

Hash bundle, field aktual serta lokasi simbol: [engine_semantics.json](organic-v41/engine_semantics.json). Full proprietary game bundles tidak disalin ke repo; hanya bukti metadata inspeksi. Engine sama sekali tidak diubah.

## Apakah partisipasi model masuk akal?

| Wilayah / tahun | Asal pekerja model | BPS employed residents | Selisih model−BPS | Interpretasi |
|---|---|---|---|---|
| Jakarta2025 | 4,191,700 | 5,130,000 | -938,300 | BPS mencakupSeribu, perbedaan survey/admin; model sekitar18%lebih rendah, bukan target workplace |
| Kab Bogor2025 | 2,129,800 | 2,620,000 | -490,200 | Pop modelBogor2022; perbedaan tahun/partisipasi penting |
| Kota Bogor2025 | 450,000 | 507,500 | -57,500 | Tabel BPS rounded/search-access; indikatif, tidak dijadikan hard control |

BPS Jakarta melaporkan labour-force5.46juta, TPAK64.75%, unemployment6.05%; working-age yang diturunkan dari angka dibulatkan itu sekitar8,432,432 (bukan hitungan baru presisi). Kabupaten Bogor TPAK64.67%, unemployment7.69%. LFPR memakai denominator usia kerja15+, sedangkan38.78%model memakai semua umur. Informal employment nyata, tetapi residual83%model diBogor tidak dapat disamakan dengan informal share. Seluruh sumber dan cakupan pada [master](ORGANIC_V41_MASTER_AUDIT.md#provenance-dan-tingkat-kepastian).

Dataset administrasi pekerjaan DKI2025 yang tersedia hanya mencakup **8,416,393** catatan jiwa untuk lima kota—lebih rendah dari total kontrolRT. Di subset ini tercatat pelajar/mahasiswa2,057,204, mengurus rumah tangga1,960,669, pensiunan70,853, belum/tidak bekerja135,971. Ini membuktikan kategori nonkerja memang perlu dibedakan, **bukan** partisi lengkap32.615juta penduduk atau angka pengangguran Sakernas. Anak kecil/tidak bekerja, unemployed, retirees, students dan home-makers tidak boleh otomatis menjadi commuters. [Subset occupations](organic-v41/jakarta_occupation_subset.json), [sumber pemprov](../sources/government/source_manifest.json).

Tidak cukup bukti untuk mengonversi semua employed menjadi perjalanan harian fisik: kerja di rumah, tidak bekerja penuh, jadwal bergilir dan frekuensi hadir berbeda. Tabel BPS di atas memperlihatkan **risiko underrepresentation** asal pekerja, bukan izin menambah total tanpa rekonsiliasi cohort. Regional destination jobs bukan jumlah employed residents di wilayah yang sama.

## Non-work demand dan usulan konservatif

Sekolah/kuliah, belanja, kesehatan, leisure dan kunjungan lain tidak muncul sebagai purpose terpisah dalam v4. Staf universitas/rumah sakit/mall yang sudah berada dalam jobs **bukan** mahasiswa/pasien/pembeli.800301 komuter pendidikan hanya slice lintaswilayah; tidak di-ekstrapolasi menjadi seluruh school trips.

S0 mempertahankan12,646,700 working-tripmakers dan semua margin desa. Usulan tahap lanjutan: ledger terpisah `worker`, `student`, `airport_passenger` dan `other_visitor`; tiap tambahan membutuhkan enrollment/attendance, rumah asal, jadwal dan sumber denominasi yang berbeda. `UNI_` dapat diuji untuk kampus berdasarkan attendance, `AIR_` untuk penumpang bandara berdasarkan ground-access passenger data, **bukan** staff bandara. Jangan mengubah totals pekerjaan karena penambahan visitor demand, jangan menggandakan satu pegawai menjadi visitor tanpa tujuan trip berbeda yang terukur.

Skenario demografi terpisah boleh mengkalibrasi asal employed dari Sakernas yang harmonis, lalu menyetarakan tujuan pekerjaan fisik. Belum diimplementasikan atau diasumsikan dalam kandidatS0/S1. Tidak ada model-purpose framework baru yang disisipkan ke engine.
