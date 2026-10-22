# CSIT314 - Member 1

Backend menggunakan **Python + Flask + SQLite**. Frontend React yang sudah ada tetap dipakai agar tampilan tidak berubah. Cakupan: **US01-US08**, yaitu kelola profil dan buat/lihat/ubah akun.

## Struktur sederhana

```text
backend/
  app.py          menerima request HTTP (Boundary)
  controllers.py  delapan controller user story (Control)
  models.py       UserProfile dan UserAccount (Entity)
  database.py     baca/tulis SQLite (Repository)
  validation.py   validasi input dan hashing password
  schema.sql      tabel database
src/member1/      layar React dan pemanggilan API
tests/            tes Python dan tes browser
```

Alurnya: **Form React -> API Flask -> Controller -> Repository -> SQLite**.

Backend berisi lima file Python utama dengan komentar bahasa Indonesia.

## Instalasi

Butuh **Python 3.11+** dan **Node.js 22.12+**. Jalankan dari folder proyek:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
.venv\Scripts\python.exe -m backend.app --dev --seed
```

Perintah seed membuat tabel dan data contoh development. Cukup sekali; tidak mereset data yang sudah ada. Database tersimpan di `data/member1.sqlite`. Skema, ID dan hash bcrypt lama tetap kompatibel.

## Menjalankan

Terminal 1 - backend:

```powershell
.venv\Scripts\python.exe -m backend.app --dev
```

Terminal 2 - frontend:

```powershell
npm.cmd run dev
```

Buka http://127.0.0.1:5173/admin/profiles atau http://127.0.0.1:5173/admin/accounts.

Frontend meneruskan request `/api` ke Flask di port 3001. Data tetap tersimpan setelah refresh/restart. Pilihan role pada header hanya untuk berpindah tampilan.

## Pengujian

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
npm.cmd run build
npm.cmd exec playwright install chromium
$env:PYTHON = (Resolve-Path '.venv\Scripts\python.exe').Path
npm.cmd run test:e2e
```

`PYTHON` pada perintah terakhir memilih interpreter untuk tes browser. Tes browser memakai database terpisah, bukan data pengguna. [Checklist dan hasil tes](docs/MEMBER1.md).

Jika `python --version` tidak berjalan, instal Python standar atau pilih interpreter yang sudah tersedia. Pada komputer sesi ini, pengujian menggunakan Python 3.13.12 bawaan pgAdmin; alias `python` di PATH belum berfungsi. Interpreter embedded itu tidak memiliki modul venv, jadi langkah venv di atas memerlukan instalasi Python standar.

## Batas pekerjaan

Login/logout, pencarian akun dan suspend akun tetap milik Member 2. Mode `--dev` memakai identitas admin dari server untuk demonstrasi, bukan login asli. Tanpa `--dev`, API menolak akses sampai Member 2 memasang pemeriksaan sesi. Mode development ditolak jika APP_ENV (atau NODE_ENV) ditetapkan production.

[Kontrak Member 2](docs/MEMBER2_HANDOFF.md) menjelaskan penggunaan repository, hash password, dan pemeriksaan akses bersama. Halaman anggota lain tetap berupa preview seperti sebelumnya.
