# Handoff ke Member 2

Gunakan backend Python dan database **data/member1.sqlite** yang sama. Jangan membuat penyimpanan akun kedua.

## Model dan repository

`backend/models.py` berisi UserProfile dan UserAccount. Atribut Python menggunakan snake_case; JSON untuk React tetap camelCase.

- Profil: profile_id, name, role, permissions (list), status.
- Akun: account_id, username, email, password_hash, profile_id, status.
- ID stabil: UP-UUID dan UA-UUID. Akun merujuk ID profil, bukan nama profil.
- `account.to_dict(profile)` menghasilkan data publik tanpa password/hash.

`Repository` di `backend/database.py` menyediakan find_profile, profile_with_name, search_profiles, create_profile, update_profile, find_account, account_with_username, account_with_email, list_accounts, create_account dan update_account. Gunakan `with repository.transaction():` untuk perubahan terkait. update_account hanya mengubah username/email/profile_id; tidak mengubah hash atau status.

Nama profil/username/email dibandingkan dengan normalisasi NFKC, trim, lalu lowercase. Email disimpan lowercase. Pencarian profil berupa substring nama, tanpa wildcard. Username: 3-40 huruf ASCII/angka/titik/underscore/hyphen.

## Password dan login

`backend/validation.py` menyediakan `hash_password(password)` dan `verify_password(password, password_hash)`. Format tetap bcrypt **$2b$, cost 12**, kompatibel dengan akun dari backend sebelumnya. Password minimal 12 karakter, maksimal 72 byte UTF-8, tidak boleh hanya whitespace. Password tidak di-trim atau dinormalisasi sebelum hashing.

Member 2 mengganti `AuthenticatedContext.resolve(request)` di `backend/app.py` untuk mengembalikan account_id dari sesi terverifikasi atau None. Pasang instance-nya melalui `create_app(database_path, auth_context=...)`. Jangan percaya ID/role/permission dari body, query, header buatan browser, atau role selector.

Setelah verifikasi password dan pada setiap request terlindungi, panggil:

```python
from backend.controllers import effective_access
account, profile = effective_access(repository, account_id)
```

Akun dan profil harus Active. **Akun yang profilnya Suspended tidak boleh mengakses fungsi terlindungi; status akun sendiri tidak berubah.** Pemeriksaan membaca database terbaru, sehingga perubahan profil/permission berlaku pada request berikutnya. Tidak ada klaim bahwa sesi dicabut: sesi/login/logout tetap pekerjaan Member 2.

Controller Member 1 membutuhkan role admin serta permission profiles:read/write atau accounts:read/write sesuai operasi. Form akun juga membutuhkan profiles:read untuk pilihan penugasan.

## Aturan yang perlu dijaga

- Update profil mempertahankan ID/status/relasi akun. Suspend tidak menghapus profil.
- Update akun mempertahankan ID/password hash/status. Penugasan baru harus ke profil aktif.
- Akun boleh tetap pada profil suspended saat username/email diubah, tanpa reaktivasi otomatis.
- Admin tidak boleh suspend profilnya sendiri, melepas role/permission admin sendiri, atau memindahkan akunnya ke profil yang menghilangkan aksesnya.
- DevelopmentContext hanya untuk development; default AuthenticatedContext menolak akses.
- Member 2 bertanggung jawab atas sesi, cookie, expiry, logout/invalidation, dan perlindungan CSRF sesi. API saat ini mewajibkan JSON dan menolak Origin yang tidak sesuai APP_ORIGIN.

## Respons error

Format: `{error: {code, message, fields}}`. VALIDATION=400, UNAUTHENTICATED=401, FORBIDDEN=403, NOT_FOUND=404, DUPLICATE/ALREADY_SUSPENDED=409, PERSISTENCE=500. Detail SQL tidak dikirim ke browser.

Integrasi login/sesi asli belum diuji karena implementasi Member 2 belum ada. Tes Member 1 memeriksa repository, bcrypt dan effective_access, termasuk penolakan profil suspended.
