# Checklist Member 1

Semua controller berada di **backend/controllers.py**. Boundary API berada di backend/app.py, entity di backend/models.py, dan SQL/repository di backend/database.py. Layar React tetap di src/member1/AdminManagement.tsx.

| Story | Controller | Endpoint |
| --- | --- | --- |
| US01 Create profil | CreateUserProfileController | POST /api/profiles |
| US02 View profil | ViewUserProfileController | GET /api/profiles/:id |
| US03 Update profil | UpdateUserProfileController | PUT /api/profiles/:id |
| US04 Suspend profil | SuspendUserProfileController | POST /api/profiles/:id/suspend |
| US05 Search nama profil | SearchUserProfileController | GET /api/profiles?name= |
| US06 Create akun | CreateUserAccountController | POST /api/accounts |
| US07 View akun | ViewUserAccountController | GET /api/accounts/:id |
| US08 Update akun | UpdateUserAccountController | PUT /api/accounts/:id |

GET /api/accounts hanya daftar normal, bukan fitur pencarian akun. Tidak ditambahkan suspend/delete/reset password/reaktivasi akun.

## Cara membaca kode

1. Mulai dari route di app.py: input diterima dari React.
2. Lihat class controller sesuai story: cek izin, validasi, lalu jalankan aturan bisnis.
3. Lihat Repository: SQL memakai parameter, foreign key dan transaksi.
4. Lihat models.py: data dikembalikan sebagai JSON publik tanpa hash password.

Validasi yang dipakai bersama ada di validation.py. Backend lama TypeScript beserta Express, bcryptjs, tsx dan concurrently dihapus. Tidak ada abstract repository, service factory, atau UnitOfWork interface tambahan. Database dan format JSON lama dipertahankan agar perubahan tidak merusak tampilan atau data sebelumnya.

## Pengujian

Tes backend memakai unittest bawaan Python di tests/test_member1.py. Tes browser di tests/browser/member1.spec.ts memakai Flask dan database khusus tes.

Cakupan: delapan story, validasi/duplikasi, rename profil, relasi akun, password/hash, suspend, akses admin, pencegahan lockout, transaksi/error penyimpanan, restart database, serta kompatibilitas hash dari backend JavaScript sebelumnya. Tes browser memeriksa reload, cancel, retry, submit ganda, inline error, stale assignment dan mobile.

Hasil verifikasi pada 23 Oktober 2026:

- 16 tes unittest Python: lulus.
- 7 tes browser Chromium dengan API Flask: lulus (30,8 detik).
- TypeScript frontend dan build produksi: lulus.
- Pemeriksaan database lama: ID, relasi, status dan hash akun tetap utuh.
- git diff --check: lulus.

Pengujian memakai Python 3.13.12, Flask 3.1.3 dan bcrypt 5.0.0 yang sudah tersedia melalui pgAdmin. Interpreter embedded tersebut diakses dengan path lengkap dan runpy untuk menambahkan root proyek ke import path. Tidak ada instalasi Python sistem atau perubahan PATH. Panduan README menggunakan instalasi Python standar dan venv, yang tidak tersedia pada interpreter embedded itu.

Tes browser memakai build produksi dan viewport mobile Chromium, bukan perangkat fisik. Login/sesi asli tetap bergantung pada Member 2 dan belum diuji.
