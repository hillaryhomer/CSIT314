# Audit proyek CSIT314

Tanggal: 22 Oktober 2026. Cakupan: seluruh source dan konfigurasi yang dilacak Git, dokumentasi, aset, dependency terpasang, serta build produksi. Audit ini tidak mengubah implementasi.

## Kesimpulan

Proyek merupakan prototipe antarmuka React/TypeScript, sesuai batasan README. Build berhasil, tetapi ada masalah deployment, konsistensi data antarmuka, validasi, dan aksesibilitas. Belum merupakan aplikasi fungsional lengkap. Tidak tersedia spesifikasi tugas asli untuk memverifikasi klaim cakupan 48 user story secara independen.

## Temuan yang perlu diperbaiki

### 1. P1 — Aset produksi gagal dimuat saat membuka URL bertingkat langsung

Lokasi: `vite.config.ts:3`, `src/App.tsx:46`.

Konfigurasi `base:'./'` menghasilkan referensi `./assets/...` pada `dist/index.html`, sementara navigasi menggunakan pathname dan History API. Pada URL `/admin/profiles`, browser menyelesaikan referensi tersebut menjadi `/admin/assets/...`; file sebenarnya ada di `/assets/...`. Refresh atau membuka tautan langsung ke halaman bertingkat dapat menghasilkan halaman kosong meskipun fallback HTML sudah dikonfigurasi sesuai README.

Verifikasi: build produksi dan resolusi URL menggunakan `new URL()` untuk `/admin/profiles`, `/designer/current`, dan `/manager/reports`. Semua mengarah ke direktori aset yang keliru. Belum diuji pada server hosting aktual.

Rekomendasi: gunakan base absolut `/` untuk hosting di root, lalu uji direct load dan refresh semua route produksi. Deployment pada subdirektori memerlukan penyesuaian base router dan seluruh URL aset juga.

### 2. P2 — Ruang desainer menampilkan proyek studio lain

Lokasi: `src/App.tsx:35`, `src/App.tsx:41`, `src/data.ts:6`, `src/data.ts:24`.

Sidebar menampilkan Studio Kanso, tetapi Portfolio hanya memfilter status dan kata kunci. Proyek P002 (Atelier Vane Design) serta P003 (Soren & Co. Studio) ikut ditampilkan beserta tombol Edit/Delete. Analytics berlabel “Your project” juga memakai seluruh proyek. Ini adalah inkonsistensi prototipe, bukan bukti kebocoran data backend karena backend belum ada.

Rekomendasi: tambahkan identitas pemilik pada fixture dan batasi portofolio serta analytics ke desainer yang dipilih. Saat backend dibuat, terapkan pembatasan kepemilikan di server.

### 3. P2 — Tanda wajib pada formulir tidak menerapkan validasi

Lokasi: `src/App.tsx:18`, `src/App.tsx:33`, `src/App.tsx:34`, `src/App.tsx:35`.

Prop `required` pada Field hanya menambahkan bintang visual. Input, textarea, dan select di dalamnya tidak mendapat atribut `required`. Form akun, perusahaan, kategori, dan proyek dapat disubmit kosong hingga menampilkan notifikasi preview; kategori dengan nilai kosong juga diterima. Pembaca layar tidak memperoleh status wajib dari tanda bintang ini.

Rekomendasi: terapkan `required` pada kontrol sebenarnya dan sediakan pesan kesalahan yang terkait dengan kontrol. Verifikasi submit kosong dan pilihan kategori kosong.

### 4. P2 — Tombol pencarian desktop tidak memiliki nama aksesibel

Lokasi: `src/App.tsx:38`, `src/styles.css:2`.

Tombol submit filter Discover hanya menampilkan ikon pada desktop. Teks “Search” memakai `.mobile-only` yang disembunyikan dengan `display:none` di luar ukuran mobile. Tidak ada `aria-label`, sehingga fungsi tombol tidak memiliki nama teks yang dapat diandalkan oleh pembaca layar.

Rekomendasi: tambahkan `aria-label="Search projects"` atau teks dengan kelas sr-only yang selalu tersedia.

### 5. P3 — Pencarian perusahaan tanpa hasil menghasilkan bidang kosong

Lokasi: `src/App.tsx:34`.

Kata kunci yang tidak cocok menghasilkan `<Details rows={[]}/>` tanpa pesan “tidak ditemukan”. Pengguna tidak mendapatkan penjelasan, berbeda dengan tabel admin dan pencarian proyek yang memakai komponen Empty.

Rekomendasi: tampilkan empty state ketika hasil filter perusahaan kosong.

### 6. P3 — Dokumen pemetaan story yang dijanjikan README tidak ada

Lokasi: `README.md:35`, `src/data.ts:29`.

README merujuk `STORY_COVERAGE.md`, tetapi file itu tidak ada di workspace maupun daftar file Git. Array `storyCoverage` memang tersedia di source, tetapi tidak menggantikan tautan dokumen yang dijanjikan. Peninjau tidak dapat mengikuti pemetaan 48 story sebagaimana didokumentasikan.

Rekomendasi: sertakan dokumen pemetaan dan bedakan cakupan visual dari penerimaan fungsional; cocokkan dengan spesifikasi tugas asli.

## Kesenjangan fungsional yang memang dinyatakan README

- Login/logout belum memeriksa kredensial atau mengelola sesi; pemilih role dan semua route terbuka untuk preview.
- Create/update/delete/suspend, penyimpanan favorit, serta unggah gambar hanya menampilkan notifikasi dan tidak menyimpan perubahan.
- Tidak ada API, database, otorisasi server, isolasi data per pengguna, atau persistensi browser.
- Analytics dan laporan memakai angka contoh; tanggal laporan tidak digunakan untuk perhitungan.
- Tidak ada skrip pengujian otomatis atau lint di package.json dan tidak ditemukan suite pengujian yang dilacak Git.

Hal tersebut sesuai scope prototipe. Jika target penyerahan adalah aplikasi lengkap, autentikasi/otorisasi server, penyimpanan, CRUD, aturan bisnis, serta pengujian integrasi menjadi pekerjaan prioritas sebelum penggunaan nyata.

## Verifikasi dan batas audit

- `npm.cmd run build`: lulus, termasuk `tsc --noEmit` dan Vite production build.
- `npm.cmd ls --depth=0`: seluruh dependency langsung yang dideklarasikan terpasang tanpa laporan missing/invalid.
- Pemeriksaan source: tidak ditemukan penggunaan fetch, localStorage, sessionStorage, eval, atau dangerouslySetInnerHTML pada source yang ditinjau. Ini bukan jaminan keamanan menyeluruh.
- Lisensi dan notices font tersedia. Asal/lisensi foto tidak dapat diverifikasi dari berkas proyek yang tersedia.
- Pemeriksaan interaksi browser, kontras visual, pembaca layar, dan viewport aktual belum dijalankan; Playwright/Puppeteer tidak terpasang. Klaim pemeriksaan browser di README bukan hasil pengujian ulang audit ini.
- Build menghasilkan ulang direktori dist yang diabaikan Git. Implementasi source tetap tidak diubah.

## Temuan dependency: P1 — Vite memiliki advisory tingkat high

Lokasi: package.json:20 (vite 8.1.5), package.json:7 (dev server pada 0.0.0.0).

npm audit berhasil setelah akses registry diizinkan dan melaporkan satu dependency rentan, Vite, dengan tingkat tertinggi high dan lima advisory terkait. Salah satunya GHSA-587h-7wmj-h5pm menjelaskan bypass pemeriksaan path pada Windows yang dapat digabungkan dengan masalah escaping untuk command injection ketika penyerang mengontrol argumen file. Kondisi eksploitasi belum diuji dalam audit ini. Temuan terkait tooling/server pengembangan; tidak membuktikan kerentanan pada hasil dist yang dihosting statis.

Sumber: https://github.com/advisories/GHSA-587h-7wmj-h5pm

Rekomendasi: perbarui Vite ke versi yang menangani seluruh advisory (npm audit menawarkan 8.3.5), perbarui lockfile, jalankan ulang audit dan build. Tinjau kebutuhan bind dev server ke seluruh antarmuka jaringan. Tidak dilakukan upgrade otomatis dalam audit ini.
