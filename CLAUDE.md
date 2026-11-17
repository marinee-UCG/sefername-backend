# CLAUDE.md — Sefernâme (uygulama adı, kullanıcı kararı 2026-11-04; repo adları hâlâ seafarer-panel)
> Logo: "S" şeklinde teal rota çizgisi, iki ucunda mevki halkaları (kalkış: içi dolu halka, varış: boş halka) — "Rota + Mevki". Yazı: "Sefernâme", Manrope 700 (kullanıcı kararı: tek font; serif denendi, istenmedi). Altında isteğe bağlı ince italik slogan: "A voyage, recorded day by day." (Sefernâme = Farsça sefer + nâme, yolculuğun gün gün kaydedildiği kitap). `<Logo tagline />`. Frontend: `components/Logo.jsx` (`Logo` = işaret + yazı, `LogoMark` = sadece işaret, renkler tokenlardan), `public/favicon.svg` (açık/koyu tema), sekme başlığı "Sefernâme".

Bu dosya, bu projede Claude Code ile nasıl çalışacağımızı anlatır. Her oturumun başında oku.

---

## 1. Çalışma şekli: öğretmen modu (EN ÖNEMLİ KURAL)

Bu proje bir öğrenme projesi. Kullanıcı (Uğur) gemi makine mühendisi; backend, sistem mimarisi ve DevOps öğreniyor. Hedefi junior developer olarak işe girmek ve DevOps / sistem mimarisinde uzmanlaşmak.

- **Kodu mümkün olduğunca kullanıcı yazar.** Sen mantığı anlatırsın, gereksinimleri ve adımları verirsin, yazdığını gözden geçirirsin.
- **Önce plan, sonra kod.** Yeni bir özellikte önce kullanıcıya planı sor veya birlikte planla (endpoint'ler, schema'lar, kurallar). Sonra yazmaya geç.
- **Adım adım git.** Bir mesajda tek bir adım. Kullanıcı "yavaş gidelim" derse daha da küçük parçalara böl.
- **Her şeyin "neden"ini açıkla.** Sadece ne yapıldığını değil, neden yapıldığını ve büyük resimde nereye oturduğunu anlat. Mümkünse denizcilik/gemi benzetmeleri kullan (kullanıcı bunlarla iyi anlıyor).
- **Kullanıcı açıkça "sen yaz" derse yaz**, ama satır satır açıkla.
- **Yeni ve karmaşık kütüphane kodu** (ör. dosya işlemleri, OCR boru hattı) için kodu sen verebilirsin; iş mantığını kullanıcı yazar.
- Gözden geçirirken: önce doğru olanları kısaca belirt, sonra hataları önem sırasına göre açıkla. Sessiz hataları (kod çalışır ama yanlış çalışır) özellikle vurgula.
- Her çalışan adımdan sonra **commit** hatırlat.
- Dil: **Türkçe** konuş. Kod, değişken adları ve commit mesajları İngilizce.
- Kullanıcı doğrudan, dolgusuz anlatım seviyor.

### Kullanıcının sık yaptığı hatalar (gözden geçirirken bunlara bak)
- Sorguyu kurmadan çalıştırmak: önce `select(...)`, sonra `db.scalar(...)` / `db.scalars(...).all()`
- Tek sonuç için `scalar`, liste için `scalars(...).all()`; karıştırma
- Fonksiyon sonunda `return` unutmak (sessiz hata: `None` döner)
- Create schema'sında opsiyonel alanlarda `= None` eksik
- `Field(...)` kullanırken `default=None`'ı Field'in içine yazmamak
- Out schema'sı modelin aynası olmalı; `from_attributes` doğru yazılmalı; Out'ta `Field` kısıtı olmaz
- Hatayı susturmak için bir alanı opsiyonel yapmak (yapma; gerçekte boş olamıyorsa zorunlu kalır)
- `HTTPException(...)` içinde argümanlar arası virgül eksik
- Sözlükte `d["key"]` ile anahtar varlığını kontrol etmeden okumak → önce `"key" in d`
- Kopyala-yapıştır sonrası satırları kontrol etmemek (yanlış ForeignKey, yanlış schema)
- Python konsolu açıkken dosya değiştirip yeniden import etmek (önce `exit()`)
- PowerShell'e Python kodu yazmak (önce `python` ile konsola gir)

---

## 2. Güvenlik ve gizlilik (her kararda öncelik)

Uygulama ileride App Store'da yayınlanacak ve kimlik belgeleri tutuyor. Gizlilik ve güvenlik pazarlık konusu değil.

- Sırlar sadece `.env`'de; `.env` ve `uploads/` asla git'e girmez.
- Şifreler Argon2 ile hash'lenir; düz şifre hiçbir yerde saklanmaz veya dönmez.
- `user_id` her zaman token'dan (`current_user.id`) gelir; asla istek gövdesinden değil.
- Başkasının kaynağı istenirse **404** dönülür (403 değil): başkasının verisinin varlığı bile sızmaz.
- Login hatası tek mesaj: "email veya şifre hatalı" (hangisinin yanlış olduğu söylenmez).
- Out schema'larında sadece gerekenler: `hashed_password`, `user_id`, `file_path` dışarı çıkmaz.
- Dosya yükleme: tür içerikten (magic bytes) kontrol edilir, boyut sınırı var, dosya adı rastgele (UUID), dosyalara sadece sahiplik kontrollü endpoint'ten ulaşılır.
- Otomatik çıkarılan veri (OCR) asla otomatik "doğru" kabul edilmez: `verified=False`, kullanıcı onaylar.
- Hassas veri: pasaport numarası vb. KVKK/GDPR kapsamında. İleride dosyaların ve hassas alanların şifrelenmesi planlanacak.
- Sosyal özelliklerde varsayılan **gizli**; paylaşım opt-in. Fotoğraflarda EXIF/GPS silinir. Mevcut gemi ve mevcut liman, güvenlik için gecikmeli gösterilir (bkz. bölüm 6).
- Yeni bir özellik tasarlarken her seferinde sor: "Bu veri sızarsa ne olur? Kim görebilir?"

---

## 3. Teknik yapı

**Ortam:** Windows, PowerShell, VS Code, Python 3.14, venv (`venv\Scripts\activate`).

**Backend:** FastAPI · SQLAlchemy 2.0 (`Mapped` / `mapped_column` stili) · PostgreSQL (şimdilik lokal; ileride Neon) · psycopg 3 · Alembic · pydantic-settings · pwdlib[argon2] · PyJWT · python-multipart · email-validator · pytesseract · pymupdf · pillow

**Sistem bağımlılığı:** Tesseract OCR (`C:\Program Files\Tesseract-OCR`, PATH'te). Docker'a geçince Dockerfile'a yazılacak.

**Frontend:** React 19 + Vite, düz JavaScript, kendi CSS token'larımız (Tailwind yok). Kütüphaneler: react-router, @headlessui/react, @mui/icons-material, sonner (toast), vaul (sheet), @number-flow/react, react-day-picker. Frontend'i Claude yazar; backend öğretmen modunda.

### Klasör yapısı
```
seafarer-panel-backend/
├── .env, .gitignore, requirements.txt, alembic.ini
├── alembic/            (env.py, versions/)
├── uploads/            (git'e girmez; uploads/<user_id>/<uuid>.<ext>)
└── app/
    ├── main.py
    ├── database.py     (engine, SessionLocal, Base, get_db)
    ├── core/           (config.py, security.py, deps.py, storage.py)
    ├── models/         (user, vessel, contract, certificate, identity_document)
    ├── schemas/        (user, vessel, contract, certificate, identity_document)
    ├── routers/        (auth, contracts, vessels, certificates, identity_documents)
    └── services/       (iş mantığı: mrz.py, mrz_ocr.py)
```

### Mimari kurallar
- Router'lar ince: trafiği yönetir. İş mantığı `services/`, dosya işleri `core/storage.py`.
- `core/` ve `services/` HTTP'den habersiz: kendi hata sınıflarını fırlatır, router bunları HTTP koduna çevirir.
- Her kaynak için sahiplik dependency'si: `get_user_<kaynak>_or_404` (id + user_id ile arar, yoksa 404).
- Saklanan değil hesaplanan değerler (single source of truth): kontrat aktifliği (`end_date is None`), süre, belge süresinin dolması.
- Yapılandırılabilir değerler `core/config.py` → `settings`.

---

## 4. Konvansiyonlar

### Modeller
- `Mapped[str]` zorunlu, `Mapped[str | None]` opsiyonel. Uzunluk `String(n)`.
- Kimlik numaraları (IMO, belge no) `str`; hesaplanan sayılar (DWT, GT, kW) `int`.
- FK: sahibi silinince gitsin → `CASCADE`; bağlı veri korunsun → `RESTRICT` (ör. gemi → kontrat).
- Python tarafı varsayılan `default=`, veritabanı tarafı `server_default=`; zorunlu alanlarda ikisi birden.
- Tablo adları snake_case çoğul; URL'ler kebab-case (`/identity-documents`).

### Schema'lar (her kaynak için üç kalıp)
- **Create:** zorunlular zorunlu; opsiyoneller `= None` veya `Field(default=None, ...)`; metinlerde `min_length=1` + modeldeki `max_length`. `id`, `user_id` ve sistemin doldurduğu alanlar yok.
- **Update:** hepsi opsiyonel ama Create'in kısıtları korunur.
- **Out:** `from_attributes=True`, `id` dahil, modelin aynası, `Field` yok, iç alanlar yok.
- Sabit değer kümeleri `Literal[...]` (ör. `DocType`).

### Endpoint'ler
- CRUD kalıbı: `GET ""`, `POST ""` (201), `GET /{id}`, `PATCH /{id}`, `DELETE /{id}` (204, gövde yok).
- İsimler: `list_x`, `create_x`, `get_x_by_id`, `update_x`, `delete_x`.
- **PATCH kalıbı:** `model_dump(exclude_unset=True)` → modelde zorunlu alanlara `null` kontrolü (422) → birleştirilmiş değerlerle (`update_data.get(alan, mevcut)`) iş kuralı kontrolleri → `setattr` döngüsü → commit/refresh.
- Önce doğrula, sonra değiştir (fail fast). Birden çok kayıt tek transaction'da; ara adımlarda `flush`, sonda `commit`.
- Kodlar: 401 kimlik, 404 bulunamadı/başkasının, 409 çakışma, 413 dosya büyük, 415 tür desteklenmiyor, 422 mantıksız içerik (`status.HTTP_422_UNPROCESSABLE_CONTENT`).
- Hata mesajları kullanıcıya sorunu ve çözümü söyler.

### Alembic kuralları
- Akış: modeli değiştir → `alembic/env.py` importuna ekle (yeni modelse) → `alembic revision --autogenerate -m "..."` → **dosyayı oku** → `alembic upgrade head` → commit.
- Uygulanmış migration dosyası **asla elle silinmez**. Geri almak için önce `alembic downgrade -1`, sonra sil.
- Silmeden önce `alembic current` ve dosya adı kontrol edilir.
- Kolon yeniden adlandırma autogenerate'te sil+ekle olarak çıkar (veri kaybı); elle düzenlenmeli.
- Kontrol: `alembic current`, `alembic heads`, `alembic check`.

---

## 5. Mevcut durum

### Bitenler
- Auth: `POST /auth/register` (sadece email + şifre, min 7), `POST /auth/login` (OAuth2 form, JWT 30 dk, httpOnly cookie), `POST /auth/logout`, `GET /auth/me`, `PATCH /auth/me` (`UserUpdate`: full_name, rank; full_name bir kez girilince null yapılamaz → 422); `home_timezone` (2026-11-10, migration `efd3e2f18975`): IANA adı, `zoneinfo.available_timezones()` dışındaki değer 422, null ile silinir. Gemide telefon gemi saatini tuttuğu için evin saati burada saklanır (frontend üst bardaki ev saati)
- **Account** (`/account`, 2026-11-10): `POST /password` (mevcut şifre + yeni min 7; yanlışsa 400, 5 hatada 429; diğer cihazların oturumları kapanır, bu cihaz devam eder), `GET /export` (JSON indirme: profil, kontratlar, seferler, sertifikalar, belgeler; dosyalar ve `file_path`/`user_id`/hash yok), `POST /delete` (şifre tekrar istenir; DB cascade + `uploads/<user_id>/` silinir, cookie'ler temizlenir). App Store 5.1.1(v) ve KVKK için.
- **Contracts** (`/contracts`): tam CRUD. Kurallar: tek aktif kontrat (409), bitiş > başlangıç (422), POST'ta `vessel_id` **veya** yeni `vessel` (tam olarak biri), yeni gemi + kontrat tek transaction, PATCH'te yeniden açma kontrolü. Cevapta iç içe `vessel`.
- **Vessels** (`/vessels`): `GET` (alfabetik), `PATCH /{id}`. Gemi kontrat üzerinden eklenir.
- **Certificates** (`/certificates`): tam CRUD; liste bitiş tarihine göre, süresizler sonda (`nulls_last`).
- **Identity documents** (`/identity-documents`): pasaport + liman cüzdanı tek tablo (`doc_type`). Elle giriş CRUD (`verified=True`), `POST /upload` (multipart, `verified=False`), `GET /{id}/file` (korumalı indirme), DELETE dosyayı da siler.

### Modeller (özet)
- **User:** email (unique), hashed_password, full_name? (kayıtta boş, onboarding'de dolar; migration `dd9b57159b60`), rank?, created_at
- **Vessel:** user_id, name, imo?, vessel_type?, flag?, dwt?, gt?, main_engine?, kw?
- **Contract:** user_id, vessel_id (RESTRICT), company, rank, start_date, end_date? (boş = aktif), `vessel` relationship
- **Certificate:** user_id, cert_name (150), cert_number, issue_date, expiry_date?, issuing_inst
- **IdentityDocument:** user_id, doc_type, document_number?, issuing_country?, issue_date?, expiry_date?, file_path?, extracted_data (JSONB)?, verified, created_at

### Pasaport MRZ okuyucu (AI'sız, lokal OCR) — devam ediyor
- **`app/services/mrz.py`** (saf metin mantığı, Tesseract'sız test edilebilir):
  - `char_value`, `compute_check_digit` — **kullanıcı yazdı.** ICAO 9303: rakam=değeri, A–Z=10–35, `<`=0; ağırlıklar 7,3,1; toplam % 10. Test: `"740812"`→2, `"L898902C3"`→6, `"120415"`→9
  - `parse_td3(line1, line2)` → dict (`extracted_data`'ya doğrudan yazılabilir; tarihler ISO metin). Kontrol hanesi tutmazsa hata **fırlatmaz**, `checks` içinde `False` + `all_checks_passed` döner. Sadece yapısal sorunlarda `MRZError`.
  - Yüzyıl kuralı: doğum → gelecekteyse 1900'ler; son kullanma → hep 2000'ler. Okunamayan tarih → `None`.
- **`app/services/mrz_ocr.py`**: `extract_passport_data(path)` → PDF (300 DPI, en fazla 3000 px genişlik) / JPG / PNG → alt %35, tüm sayfa, 180° çevrilmiş → gri ton + siyah-beyaz varyant → Tesseract (`eng`, whitelist `A-Z0-9<`) → konuma göre düzeltme (harf alanlarında 0→O, rakam alanlarında O→0) → tüm kontrolleri geçen ilk sonuç, yoksa ilk okunabilen. Bulunamazsa `MRZNotFoundError` (`MRZError` alt sınıfı).
- ICAO örneği (`P<UTOERIKSSON<<ANNA<MARIA...` / `L898902C36UTO7408122F1204159ZE184226B<<<<<10`) sentetik görsellerde okunuyor.
- **Açık sorun:** Tesseract `eng` modeli pasaport fontunu (OCR-B) tanımıyor. Gerçek bir pasaportla denemede `<`→`K` (ad alanında dolgu karakterleri harf okundu) ve `9`→`I` (bir tarih hanesi; kontrol hanesi yakaladı) hataları var; süre ~17 sn. Çözüm: OCR-B / MRZ `.traineddata` modeli (projede bir klasöre, `--tessdata-dir` ile). Henüz kurulmadı.

### Sıradaki işler (sırayla)
1. ~~MRZ endpoint'i~~ **bitti:** `POST /identity-documents/{id}/extract` (sırayla: pasaport değil 422, dosya yok 422, dosya diskte yok 404, onaylı 409, `MRZError` 422). `personal_number` (TC kimlik no) **saklanmaz** (veri minimizasyonu). `verified=False` kalır.
2. **pytest — yarıda bırakıldı, frontend'den sonra dönülecek:** kurulu (`pytest.ini`: `pythonpath = .`, `testpaths = tests`). `tests/test_mrz.py`'de 5 test var (3 kontrol hanesi, `pytest.raises` ile küçük harf, ICAO `parse_td3` sözlük+döngü). Kaldığı yer: 6. adım, OCR hatası testi (`L898`→`LB98`; `checks.document_number` False, `birth_date` True). Sonra endpoint testleri (httpx2 + TestClient).
3. **Frontend:** palet, tipografi ve hareket kuralları **belirlendi** (bölüm 7, `design/preview.html`). Kurulum bitti (Vite + React, tokenlar, Manrope, CORS, `/api` proxy, `dev:lan`). Sıradaki: **login sayfası.** **KARAR (2026-11-03): token httpOnly cookie'de** (localStorage değil; XSS ile çalınamasın). Plan, sırayla: (1) backend `POST /auth/login` token'ı cookie olarak gönderir: `HttpOnly`, `SameSite=Lax`, `Secure` sadece yayında (ayar), `max_age` = token süresi; (2) `get_current_user` önce cookie'yi, yoksa `Authorization` başlığını okur (Swagger ve ileride iOS için); (3) `POST /auth/logout` cookie'yi siler; (4) frontend token'ı hiç görmez, giriş durumu `GET /auth/me` ile anlaşılır (200/401); (5) login sayfası. Backend adımları (1)–(3) **bitti**: login cookie bırakır (gövdede token Swagger için durur), `get_current_user` önce cookie sonra başlık (`auto_error=False`), `POST /auth/logout` 204. Logout token'ı iptal etmez (JWT 30 dk geçerli kalır; çözüm refresh token). Şifre kuralı: min 7 (kullanıcı kararı; 8 önerildi), max 128. Frontend (4)–(5) **bitti**: `LoginPage` (state, `onSubmit`, hata + bekleme durumu, tasarım), `App` kullanıcıyı tutar (`onLogin` prop), açılışta `useEffect` ile `/auth/me` kontrolü (`checking` iken `null` çizer), çıkış butonu. Login arka planı: `components/ChartBackground.jsx` (OSM İstanbul Boğazı kıyı çizgisi, 5′ ızgara, Mercator; veri `scripts/make_chart.py` ile üretilir; `© OpenStreetMap contributors` yazısı lisans gereği kalmalı). Router (react-router 8) kuruldu; `RegisterPage` (email, şifre + şifre tekrarı, frontend'de eşleşme kontrolü). **Kullanıcı kararı: sıradaki iş ONBOARDING, sonra uygulama iskeleti.**

### Onboarding — hazır olan iskelet (2026-11-04)
- Kural: `full_name` boşsa kullanıcı onboarding'i bitirmemiş sayılır. `App.jsx`'te `needsOnboarding`; `/` → `/onboarding`'e, onboarding bitmişse `/onboarding` → `/`'e yönlendirir. Bilinmeyen adresler → `/`.
- `src/pages/OnboardingPage.jsx` şimdilik **yer tutucu** (karşılama + çıkış). Hazır prop'lar: `user`, `onComplete(updatedUser)` (PATCH sonrası çağrılınca App ana sayfayı açar), `onLogout`.
- Backend: `PATCH /auth/me` ile ad ve rütbe kaydedilir.
- **Kesin:** ilk soru ad soyad (kayıt formundan kaldırıldı).
- **GÜNCEL (2026-11-13):** 4 ekran: (1) ad soyad, (2) departman (seçince kendiliğinden ilerler), (3) rütbe (kaydırılabilir açılır menü), (4) **profil kartı / özet**. "Şu an gemide mi evde mi" ve tarih soruları **kaldırıldı**: kontratsız kullanıcıda yanlış durum oluşturuyordu; gemide/evde bilgisi artık sadece kontratlardan hesaplanır. `OnboardingIn.at_sea` / `status_since` opsiyonel (`= None`), frontend göndermiyor. Kontratı olmayan yeni hesap dashboard'da "Are you on board now?" başlangıç kartını görür (Sign on / Add a past contract → `/contracts?add=1`).
- Eski karar (2026-11-04, artık geçerli değil): (1) ad soyad, (2) departman, (3) rütbe, (4) gemide mi evde mi, (5) tarih, (6) **profil kartı / özet** — kullanıcı tüm cevapları görür, her satırdan ilgili ekrana dönüp düzeltebilir; "Confirm" ile `POST /auth/onboarding` gider (kullanıcı kararı 2026-11-04), Confirm → `onComplete(user)` → doğrudan dashboard. **Belge yükleme onboarding'den çıkarıldı (2026-11-04), dashboard'dan yapılacak.** Onboarding BİTTİ.

### Sertifika / belge / kontrat sayfaları — KARARLAR (2026-11-09)
- Seyir defteri paneli **ertelendi** (harita ve "Sea chart" düğmesi çalışıyor, sol panel boş). Önce uygulamanın ilk kısmı bitecek: Certificates, Contracts, Documents sayfaları.
- **Sertifikalara dosya eklenebilir (kullanıcı kararı 2026-11-09, önceki "dosya yok" kararının yerine):** her sertifikaya isteğe bağlı PDF/JPG/PNG. Sıra: `Certificate.file_path` + `has_file` + migration, `POST /certificates/{id}/file`, `GET /certificates/{id}/file`, sertifika silinince dosya da silinir; `file_path` API'den çıkmaz.
- Sertifika adı **listeden seçilir** (+ "Other"). Sayfa tasarımı: `design/certificates-reference.html`; "Dosyayı aç", "Liste · PDF" ve "Geçmiş" **çıkarıldı** (2026-11-09).
- **Arayüz şimdilik İngilizce; ileride TR dil seçeneği eklenecek** (kullanıcı isteği).
- **DURUM (2026-11-09): frontend ilk kısım BİTTİ (kullanıcı "sen yap" dedi, commit'leri kendisi atacak).** Sayfalar: `CertificatesPage` (özet, `ExpiryStrip`, gruplu liste, detay, STCW kodları `utils/certificates.js`, kodlar kullanıcı tarafından doğrulanacak), `ContractsPage` (özet, 5 yıl hizmet çubuğu, `MiniRoute`, sefer ekleme/EOSP/silme: `VoyageForms.jsx`, `ContractForm`), `DocumentsPage` (`DocumentForms.jsx`: tarama = upload + extract, "To check" onayı, dosya açma `apiFile`). Ortak: `components/Register.css`, `DetailPane`, `DeleteButton`, `SidePanel`. `SeaMap`: seyir defteri paneli, sefer seçince yakınlaşma, 60 sn drift + 14 sn tur, etiket çakışması gizleme. Dashboard: Sea Ledger'da nm, "Complete your account" kartı. Formda saat cihazın saat dilimiyle gönderilir (gemi saati seçeneği yok).
- **Tasarım kararı (2026-11-09, güncel):** Certificates sayfası kullanıcının eklediği `design/cert wallet.html` gibi olacak (sertifika kartları, mühür, kâğıt dokusu, durum cümlesi, Attention/Valid/No expiry grupları). Bunu uygularken netleştir: tasarımda "Dosya yükle"/dosya ve hatırlatma var; backend'de sertifika dosyası ve hatırlatma yok, önceki karar "normal sertifikaya dosya yok, sadece ekstra sertifika yükleme" idi. Beğenildi, uygulanacak: `design/documents-wallet-reference.html` (özellikle) ve `design/contracts-timeline-reference.html`.
- **Kart sayfaları koda geçti (2026-11-09):** `CertificatesPage` (`cert wallet.html`: gruplu kart yığınları, mühür, sheet içinde dosya yükle/aç/değiştir ve sil) ve `DocumentsPage` (`documents-wallet-reference.html`). Detay satırı stilleri `CertificatesPage.css`'te, Documents de onu import ediyor. Hatırlatma ve "Geçmiş" satırları backend olmadığı için çıkarıldı. `ContractsPage` da `contracts-timeline-reference.html`'e geçti (gemi başına kulvar, seçilen kontrat çizelgenin altında sheet, telefonda peek kartı + tam ekran detay; backend değişikliği gerekmedi). Eski özet kartı ve 5 yıl çubuğu kalktı, 5 yıl bilgisi başlık satırında.
- **Backend isteyen eksikler:** ekstra sertifika yükleme (`DocType` sadece passport/seaman_book; referanstaki sağlık/vize/aşı türleri de yok), ~~`GET /ports` sıralaması~~ (yapıldı 2026-11-15: LOCODE tam eşleşme → kullanıcının seferlerinde geçen limanlar → adla başlayan → içinde geçen), hatırlatma ayarı, hizmet dökümü/PDF, kontratta sign-off limanı (sign-on limanı 2026-11-17'de eklendi), `IdentityDocumentOut`'a "dosya var mı" bilgisi.
- Tasarım araçları: `design-builder` / `design-reviewer` ajanları, `/tasarim` komutu, `sefername-design` skill'i. Kullanıcı istemedikçe çalıştırılmaz.
- Ekleme formu: ilgili sayfada açılan panel (masaüstü sağdan, mobil alttan; öneri, kullanıcı onayı bekliyor). Dashboard sadece özet gösterir.

### Dashboard — KARARLAR (2026-11-05)
- Referans: `design/dashboard-reference (1).html` (görsel + davranış; üretim kodu değil). Bölümler: üst bar (logo, menü: Overview/Contracts/Documents/Certificates, "Sea chart" düğmesi, tema, avatar), başlık (tarih + selamlama + "Scan document"/"Add contract"), **Gemide kartı** (gemi, tip · şirket · rütbe, gün sayacı, ilerleme, sign-on / planlanan sign-off), **Hesabını tamamla** listesi, **Sea Ledger** (denizde gün, nm, gemi sayısı/tip, kontrat), **Belgeler** listesi (süre rozetleri: doldu/kalan gün/geçerli), **Seyir çizelgesi** (kontrat zaman çizelgesi), arka planda harita + seyir defteri paneli. Mobil: alt sekme çubuğu, seyir defteri alt sayfa (sheet).
- **Dil İngilizce** (referans Türkçe yazılmış; metinler çevrilecek).
- **Tema: otomatik (cihaz) + düğme;** kullanıcı seçerse hatırlanır (localStorage'da sadece tema tercihi, hassas veri değil).
- **Kontrata opsiyonel `planned_end_date` eklenecek** (migration): doluysa kalan gün + ilerleme çubuğu.
- Referanstaki Google Fonts ve Newsreader serif kullanılmaz: fontlar self-host, tek font Manrope (kullanıcı serif istemedi). Logo: `components/Logo.jsx`.
- **DURUM (2026-11-06):** (1)–(9) **bitti**: `AppLayout` (üst bar + mobil sekme çubuğu, `NavLink`), `DashboardPage` (başlık, Gemide kartı, Sea Ledger, Documents, Sea time chart), kontrata `planned_end_date` (migration `85cb3cbe84d3`), tema (`index.html` inline script + `data-theme` + `ThemeToggle`; koyu renkler `index.css`'te İKİ yerde: `@media` içi ve `[data-theme="dark"]`, değiştirirken ikisini de güncelle). Demo hesap: `demo@sefername.app` (şifresi dokümanda yazmaz; Second Engineer, 4 kontrat, 4 sertifika + pasaport + cüzdan). **Sıradaki: (10) harita + seyir defteri → önce backend voyage şemaları/endpoint'leri.**
- **Yapılacak (kullanıcı istedi, 2026-11-09):** dashboard arka planındaki harita sürekli, yavaşça hareket etsin (referansta `.mapdrift`: 60 sn ileri-geri kayma + 14 sn'de bir seferler arası geçiş; "hareketi azalt" açıksa kapalı). Seyir defteriyle birlikte veya ilk kısım bitince yapılacak.
- **İnce ayar durumu (2026-11-10):** harita kayması + 14 sn tur, yakın liman etiketleri (sola al / gizle), harita açıkken sayfa kayması, "X days over" ve 180. meridyen (Pasifik rotaları bölünür) **yapıldı**. Kalanlar aşağıda.
- **İnce ayar listesi (en sona, kullanıcı istedi):** genel boyutlandırma hâlâ referanstan büyük görünüyor (kullanıcıya göre; body line-height 1.4'e, bardaki logo 24px'e indirildi, ölçümler eşit ama his aynı değil → tarayıcı zoom'u / Windows ölçeklemesi de kontrol edilecek); geçmiş planlanan sign-off'ta eksi gün yerine "X days over"; mobilde çizelge açıklamasında uzun gemi adı kırılıyor; başlıktaki bazı metinler değişecek; seyir haritasında yakın limanların adları üst üste biniyor (İstanbul/Ambarlı, Mersin/İskenderun → çakışan etiketi gizle); harita açıkken sayfa hâlâ kayıyor (gizli kartlar yer kaplıyor); mobilde "Sign out" iki satıra kırılıyor; `world-map.png` 6000×4303, telefonda bellek/performans kontrol edilecek; 180. meridyeni geçen rotalar (Pasifik) test edilmedi.
- Sıra: (1) uygulama kabuğu (iç içe route'lar, `AppLayout` + `Outlet`, üst bar, mobil sekme çubuğu), (2) başlık, (3) Gemide kartı (+ `planned_end_date`), (4) Sea Ledger, (5) Belgeler, (6) Seyir çizelgesi, (7) harita + seyir defteri (voyage endpoint'leri bittikten sonra).

### Seferler (Voyage) + Seyir haritası — KARARLAR (2026-11-04)
- Sıra: (1) Port modeli + seed migration, (2) Voyage modeli + şemalar + kurallar, (3) `services/routing.py` (searoute; **önce lisansı kontrol et**: kütüphane + deniz yolu ağı verisi), (4) endpoint'ler, (5) pytest, (6) frontend (tasarım: kullanıcı `design/` altına preview.html atacak, frontend'e gelince iste).
- **EOSP ayrı aksiyon:** `POST /voyages/{id}/eosp` (sadece aktif sefer, iki kez bitirilemez 409, eosp > cosp 422). Düzeltme: `PATCH /voyages/{id}` (2026-11-10; limanlar, COSP, bitmiş seferde EOSP; null 422, aktif seferde EOSP 422 → EOSP aksiyonu, birleşik değerlerle kontrat tarih kuralları).
- **Sefer kontrata zorunlu bağlı.** Gemideki kullanıcı önce aktif kontratını ekler (dashboard'da yönlendirme). `user_id` hep token'dan; kontrat kullanıcının değilse 404.
- **`contract_id` → `ondelete=RESTRICT`** (kontrat silinince seyir defteri gitmesin; seferli kontrat silinmek istenirse 409). `user_id` → CASCADE (hesap silme). Port FK'leri RESTRICT.
- Bir kontratın seferleri: `GET /voyages?contract_id=5` (ayrı endpoint yok).
- **Limanlar kendi tablomuzda.** **Güncelleme:** veri kaynağı searoute paketinin kendi `data/ports.geojson` dosyası (3962 liman: UN/LOCODE, ad, ülke, lon/lat). Migration sadece tabloyu kurar; veri `scripts/import_ports.py` ile yüklenir (locode'a göre upsert, tekrar çalıştırılabilir). Veride küçük hatalar var (ör. "Bandirmar") → tek tek düzeltilir.
- **Lisans kontrolü (2026-11-04):** searoute-py kodu **Apache-2.0** (ticari kullanım serbest, lisans metni korunmalı). Deniz yolu ağı Eurostat SeaRoute'tan (**EUPL-1.2**), o da ORNL "Global Shipping Lane Network" verisine dayanıyor. Liman verisinin kaynağı pakette belgelenmemiş. Geliştirme için sorun yok; **ticari yayından önce** veri lisansları (EUPL'nin ağ üzerinden sunma maddesi dahil) bir hukukçuyla netleştirilmeli. searoute "not for routing purposes": biz sadece görselleştirme için kullanıyoruz, uygun.
- Zamanlar UTC saklanır (`timezone=True`); formda gemi saati/UTC girişi frontend'de kararlaştırılacak.
- Mesafe ve rota saklanmaz, liman çiftinden hesaplanır. Güncel konum en yakın dereceye yuvarlanır, `approximate: true`.
- **DURUM (2026-11-04, burada kalındı):** (1) Port **bitti**: `models/port.py`, migration `bba69c86e998`, `app/scripts/import_ports.py` (`python -m app.scripts.import_ports`, 3923 liman yüklendi; bozuk "EG" kodu ve 38 tekrar atlanır). (2) Voyage modeli + migration `8f29c4da6071` **bitti ve uygulandı**; DB seviyesinde 3 kural: `ck_voyages_different_ports`, `ck_voyages_eosp_after_cosp`, kısmi benzersiz index `uq_voyages_one_active_per_user` (eosp_at IS NULL) — eşzamanlı iki istekte bile tek aktif sefer. Router yine aynı kuralları kontrol edip anlaşılır mesaj verecek (DB'den gelen IntegrityError'ı da 409/422'ye çevirmeyi unutma). **(2026-11-06) Backend sefer kısmı BİTTİ:** `schemas/port.py` (`PortOut`), `schemas/voyage.py` (`VoyageCreate`: eosp_at opsiyonel = geçmiş sefer tek istekte; `VoyageEosp`; `VoyageOut`: iç içe limanlar, `vessel_name` ve `is_active` modeldeki property'lerden, `distance_nm` router'da `voyage_out()` ile), zamanlar `AwareDatetime` (saat dilimsiz → 422). `services/routing.py`: `sea_route(origin, destination)` → `SeaRoute(coordinates: tuple, distance_nm)`, `@lru_cache(2048)`, `RouteError` (İstanbul–Mersin 766.3 nm, 39 nokta). `routers/ports.py`: `GET /ports?q=` (ad içinde veya LOCODE başında, ilike, min 2 harf, limit 15, giriş zorunlu). `routers/voyages.py`: `POST /voyages` (kurallar sırası: kontrat 404 → aynı liman 422 → bilinmeyen liman 422 → COSP < kontrat başı 422 → COSP > kontrat sonu 422 → EOSP ≤ COSP 422 → aktif sefer 409; commit'te `IntegrityError` → 409), `POST /voyages/{id}/eosp` (bitmiş 409, EOSP ≤ COSP 422, kontrat sonundan sonra 422), `GET /voyages?contract_id=` (yeniden eskiye), `DELETE /voyages/{id}` (204). `DELETE /contracts/{id}` seferi varsa 409. **Sıradaki: harita** → `GET /voyages/{id}/track` ve `GET /map` (frontend ihtiyacına göre), dünya haritası verisi (Natural Earth, public domain), dashboard arka planı + seyir defteri paneli, Sea Ledger'a nm kutusu.
- **Önerilen model (kullanıcı onayı bekliyor):** User'a `department` (deck/engine), `at_sea` (bool), `status_since` (date), `onboarded_at` (datetime) eklenir + migration. Tamamlanma işareti `full_name` yerine `onboarded_at` olur (ad 1. ekranda kaydedilse bile kullanıcı ana sayfaya fırlamasın). Cevaplar frontend state'inde toplanır, son zorunlu ekranda tek istekle `POST /auth/onboarding` gönderilir; backend `onboarded_at`'i kendisi koyar (istemci zaman damgası göndermez). Rütbe: departmana göre liste + "Other" (öneri).
4. Liman cüzdanı çıkarma: yöntem sonra kararlaştırılacak (MRZ yok).
5. OCR-B modeli ile isim doğruluğu.

### Yayına alma (2026-11-10, hazır ama denenmedi)
- `Dockerfile` (Python 3.14 + tesseract, root olmayan kullanıcı, `--proxy-headers`), frontend `Dockerfile` (node build → caddy), `deploy/`: `docker-compose.yml` (db, migrate, api, web, backup), `Caddyfile` (HTTPS, CSP/HSTS, `/api` → api), `backup.sh` (gece `pg_dump`, 14 gün), `.env.example`, `README.md` (adım adım VPS kurulumu). Production: `DOCS_ENABLED=false`, `COOKIE_SECURE=true`.
- Bu bilgisayarda Docker yok: image'lar hiç derlenmedi, compose hiç çalıştırılmadı. İlk kurulumda (VPS veya Docker Desktop) hatalar çıkabilir.

### Bilinen açıklar / yapılacaklar
- Kullanıcı silinince `uploads/<user_id>/` temizleniyor (`POST /account/delete`, 2026-11-10)
- Refresh token **eklendi (2026-11-10)**: `models/refresh_token.py` (migration `49279e6589a0`), `core/sessions.py`. Token'ın sadece SHA-256'sı saklanır; her `POST /auth/refresh` token'ı değiştirir (rotation), kullanılmış token geri gelirse kullanıcının bütün oturumları kapanır. Login'de `remember` (varsayılan true): 30 gün kalıcı cookie, false ise tarayıcı oturumu + 1 gün. Logout refresh token'ı iptal eder (access JWT 30 dk geçerli kalır). Frontend 401'de bir kez yenileyip isteği tekrarlar.
- Login deneme sınırı **eklendi (2026-11-10)**: `core/rate_limit.py`, bellekte (aynı email+adres 15 dk'da 5, aynı adres 20 hatalı → 429 + Retry-After). Çoklu worker'da Redis'e taşınmalı; proxy arkasında uvicorn `--proxy-headers` gerekir. Bilinmeyen email de sahte hash ile doğrulanır (süre farkı hesap varlığını ele vermesin).
- Pasaport onaylanınca `extracted_data` silinir (2026-11-10); önceden onaylanmış kayıtlar da tek seferlik temizlendi. Demo'daki "Medical Certificate" sertifikası Documents'a (`doc_type=medical`) taşındı.
- `PATCH /contracts/{id}` artık seferleri dışarıda bırakamaz (2026-11-10): sign-on ilk COSP'tan sonra olamaz, sign-off son EOSP'tan önce olamaz (422), yolda sefer varken sign-off 409. Sadece gerçekten değişen tarih kontrol edilir. Demo verideki çakışma kullanıcı onayıyla düzeltildi (2026-11-10): kontrat 8 sign-off 2026-09-03, sefer 20 25 Ağu–1 Eyl.
- Kontratlar birbiriyle çakışamaz (2026-11-10, `check_no_overlap`): POST ve tarihi değişen PATCH'te 409. Aynı gün sign-off/sign-on (gemi değiştirme) serbest.
- Dosyaların ve hassas alanların şifrelenmesi
- Otomatik testler: sadece `mrz.py` için başladı; endpoint'ler hâlâ Swagger'da elle test ediliyor
- `requirements.txt` güncellerken `>` kullanma (PowerShell 5.1 UTF-16 yazar): `pip freeze | Out-File -Encoding ascii requirements.txt`
- CORS (frontend başlayınca)

---

### Son eklenenler (2026-11-12 … 2026-11-16)
**Backend (kullanıcı yazdı, öğretmen modu; güvenlik düzeltmelerini Claude yazdı):**
- `GET /profile/stats` (`services/profile_stats.py`): deniz günü, terfi ilerlemesi (`settings.promotion_service_days`, TR kuralı 900 gün), 25 rozet (milestone) ve kazanıldıkları tarih, rekorlar.
- `GET /news` (`services/news.py`, "Karadan Özeti"): TRT Haber manşet RSS (`settings.news_feed_url`), ilk 5 başlık; 10 sn zaman sınırı, 2 MB sınır, sadece `https://www.trthaber.com/` linkleri, 15 dk bellek önbelleği, kaynak düşerse son liste.
- `GET /currency` (`services/currency.py`): TCMB `kurlar/today.xml`, USD/EUR/GBP döviz alış (`settings.currency_codes`), bülten tarihi; aynı önbellek kalıbı; hiç veri yoksa 503.
- Hizmet belgesi: `Contract.service_doc_path` + `has_service_doc` (migration `db3d6a3cd914`), `POST/GET/DELETE /contracts/{id}/service-doc`; sadece bitmiş kontrat (aktifte 409); kontrat silinince dosya da silinir. Orijinal dosya adı saklanmıyor.
- Kontrat tarihleri: sign-on ve sign-off bugün + 1 günden sonra olamaz (422, `check_not_in_future`; `planned_end_date` hariç).
- N+1 düzeltildi: `/contracts`, `/map`, `/voyages`, `/profile/stats` sorgularında `selectinload` (107 → 17 sorgu, veri arttıkça sabit).
- Sefer hızı / ETA (2026-11-16): `Vessel.service_speed_kn` (float, opsiyonel; şemada `gt=0, le=50`; migration `58ea3f47cc45`). `services/voyage_speed.py` → `estimated_speed_kn(voyage, voyages)`: servis hızı → aynı gemideki bitmiş seferlerin toplam nm ÷ toplam saat → `PLANNED_SPEED_KN` (12). `progress_fraction(..., speed_kn)`; `/map` (konum, progress, `eta`) ve `/profile/stats` (`sailed_route(voyage, voyages, ...)`) aynı hızı kullanır. Ticari gemi verisi API'leri (VesselFinder, Datalastic vb.) ücretli ve servis hızı vermiyor; Equasis'in API'si yok → bilgiler elle girilir. **Frontend (2026-11-16, Claude):** ContractSheet "Vessel details"te "Service speed (kn)" (0.1–50); dashboard "Complete your account"ta gemideyken "Add your vessel details" (tip, GT, kW, hız eksikse) → `/contracts?vessel=<id>` düzenleme formunu Vessel details açık getirir; VoyageCard "~N days left / ~N h left / due now · ETA 18 Nov" (`/map` `eta`, harita çekildiği andan sayılır). `UserOut.has_password` eklendi.
- **Oturumlar iOS'a hazır + iptal edilebilir (2026-11-16):** `RefreshToken.session_id` (her cihaz girişi = bir oturum, yenilemede aynı kalır) + `replaced_at` (normal yenileme; `revoked_at` artık sadece bilerek kapatma), migration `934fb939904d` (eski satırlar md5 ile dolduruldu). Access JWT: `sub`, `sid`, `iat`, `exp`, `typ="access"`; `decode_token` → `(user_id, sid)`, eksik alan/yanlış tür → 401. `get_current_user` her istekte `is_session_active(sid)` sorar (çıkış/şifre değişimi anında etkili) ve `request.state.session_id` bırakır. İki kapı: web `/auth/login` (204 + cookie), `/auth/refresh`, `/auth/logout`; native `/auth/token` (`TokenPair`: access, refresh, `expires_in`; Swagger'ın tokenUrl'si), `/auth/token/refresh`, `/auth/token/revoke` (bilinmeyen token da 204). Ortak `authenticate()` (deneme sınırı, sahte hash). `refresh_session`: satır `with_for_update()` ile kilitli; 30 sn içinde gelen eski token → sadece 401 (yarış), daha eskisi → bütün oturumlar kapanır (çalıntı). `end_session` oturumun bütün satırlarını kapatır. Şifre değişimi: bu cihaz hariç diğer oturumlar kapanır (`end_all_sessions(keep_session_id=...)`), yeni token gönderilmez. Login gövdesindeki Swagger token'ı kaldırıldı. Geçici hesapla 9 senaryo test edildi. iOS istemcisi: token'lar Keychain'de, yenileme tek seferde (single-flight).
- **Dosya şifreleme (2026-11-16, Claude yazdı):** yüklenen her dosya diskte AES-256-GCM ile şifreli (`core/crypto.py`: `encrypt_bytes`/`decrypt_bytes`, `core/storage.py`: `read_upload(path, user_id)`; biçim `SFE1` + 12 bayt nonce + şifreli veri; GCM bozulmayı da yakalar). Anahtar `.env`'de `DATA_ENCRYPTION_KEY` (eski adı FILE_ENCRYPTION_KEY) (32 bayt base64, başlangıçta doğrulanır; yerel `.env`'e rastgele bir tane eklendi), anahtar değişimi için `DATA_ENCRYPTION_OLD_KEYS`; her değer sahibinin id.sine mühürlü (AAD `user:<id>`). **Anahtar kaybolursa dosyalar da kaybolur, şifre yöneticisinde sakla.** İndirmeler `core/downloads.py` → `file_download()` (çözer, `attachment`, `Cache-Control: no-store`; `FileResponse` kalktı). OCR dosyayı bellekte çözüp okur (`extract_passport_data(content, suffix)`), şifresiz tarama diske yazılmaz; bozuk PDF/görsel → 422. Şifrelemeden önceki dosyalar okunmaya devam eder; `python -m app.scripts.encrypt_uploads [--apply]` onları (ve eski anahtarlıları) şifreler, varsayılanı sadece rapor. Yeni bağımlılık: `cryptography`.
- **Şifreli yedekler (2026-11-16, Docker'da denenmedi):** `deploy/backup.sh` her gece veritabanı + `uploads` volume'unu (`:ro`) `openssl enc -aes-256-cbc -pbkdf2 -iter 600000` ile `BACKUP_PASSPHRASE` parolasıyla şifreler (`*.dump.enc`, `uploads-*.tar.enc`), 14 gün tutar. Geri yükleme komutları `deploy/README.md` bölüm 6'da. `.env.example`'a `DATA_ENCRYPTION_KEY`, `BACKUP_PASSPHRASE` eklendi.
- **Güvenlik logu (2026-11-16):** `core/audit.py` → `security_event(event, request, user_id, email, **details)`, stdout'a tek satır JSON (`docker compose logs api`). Olaylar: login_succeeded/failed/blocked, register_succeeded/email_taken/blocked, refresh_token_reused, password_check_failed/blocked, password_changed, account_deleted, extract_limited. E-posta açık yazılmaz: `email_tag` = HMAC(secret_key) ilk 16 hane. Şifre, token, belge no loglanmaz. Compose'da api logu 5×10 MB ile sınırlı.
- **Alan şifreleme (2026-11-16, kullanıcı + Claude):** hash değil şifreleme (işverenle paylaşım için geri açılabilmeli). `core/crypto.py`: tek ana anahtar `DATA_ENCRYPTION_KEY` (eski adı FILE_ENCRYPTION_KEY), AES-256-GCM, her değer sahibinin id'sine mühürlü (AAD `user:<id>`; başka kullanıcının id'siyle açılmaz → `DecryptError`). Alanlar: `seal(value, user_id)` → `"v1."+base64`, `open_sealed`, `seal_json`/`open_json`; düz (eski) değerler okunmaya devam eder. Şifreli kolonlar `Text` (migration `f4b63cb774f5`; downgrade sadece şifrelemeden önce çalışır): kimlik belgesinde `document_number`, `issuing_country`, `extracted_data` (artık JSONB değil, şifreli metin); sertifikada `cert_number`, `issuing_inst`. Düz kalanlar: tarihler, belge türü, sertifika adı (sıralama/uyarı için; KVKK açısından riske uygun tedbir). Router'larda `SEALED_FIELDS` + `seal_fields()` (yazarken, doğrulamadan SONRA) ve `document_out()`/`certificate_out()` (önce aç, sonra şemaya dök); dışa aktarma da bunları kullanır. Mevcut 18 değer `python -m app.scripts.seal_fields --apply` ile şifrelendi (önce yedek: `deploy/backups/local-before-field-encryption-2026-11-16.dump`), API çıktısı öncesi/sonrası birebir aynı. **İş platformu için:** işveren paylaşımı = izin kaydı (kim, hangi belge, ne zamana kadar, geri alınabilir, her görüntüleme loglanır); sunucu sahibin id'siyle açıp gösterir, şifreleme düzeni değişmez. Hesap silinince veri en geç 14 gün içinde yedeklerden de düşer (gizlilik politikasına yazılacak); kullanıcı başına anahtarla "yedekten de silme" ancak anahtarlar DB dışında (KMS) dursaydı mümkün olurdu.
- **Google / Apple ile giriş, backend (2026-11-16, kullanıcı + Claude; frontend ve gerçek istemci kimlikleri bekliyor):** `settings.google_client_ids` / `apple_client_ids` (boş = kapalı → 404). `services/social_auth.py` → `verify_id_token(provider, id_token, nonce)`: PyJWT `PyJWKClient` ile sağlayıcının yayınladığı anahtarlar (1 saat önbellek), `RS256` sabit, `iss`/`aud`/`exp`/`iat`/`sub` zorunlu, nonce (Apple'da sha256) `compare_digest` ile; hatalar `SocialAuthError` / `ProviderDisabledError` / `ProviderUnavailableError` (→ 401/404/503). Model `UserIdentity` (`user_identities`: provider, subject, email; benzersiz provider+subject ve user_id+provider; migration `ce8ff0bdd315`), `User.hashed_password` artık boş olabilir. `routers/auth.py`: `social_sign_in()` (kullanıcı yazdı): bağlı `sub` → o kullanıcı; aynı e-postayla hesap varsa **otomatik birleştirme yok** → 409 (kayıtta e-posta doğrulanmadığı için ön hesap ele geçirmeye karşı); yoksa e-posta ve `email_verified` şartıyla şifresiz hesap + bağlantı tek commit. Endpoint'ler: web `POST /auth/google`, `/auth/apple` (204 + cookie), native `/auth/token/google`, `/auth/token/apple` (`TokenPair`); gövde `SocialLoginIn` (id_token, nonce min 16, remember); eşzamanlı ilk girişte `IntegrityError` → tekrar dener. Şifresiz hesapta şifreyle giriş hep 401 (sahte hash, aynı süre). `/account`: `GET /identities`, `POST /identities/{provider}` (girişliyken taze token ile bağlama = güvenli birleştirme yolu), `DELETE /identities/{provider}` (son giriş yolu silinemez → 409); şifresizde şifre değiştirme 400 (ilk şifre belirleme e-postalı akışla sonra), hesap silme taze Google/Apple doğrulamasıyla. Sahte anahtarla 13 senaryo test edildi. **Google web düğmesi (2026-11-16, Claude):** Client ID (web, public) backend `.env` `GOOGLE_CLIENT_IDS=["…"]` ve frontend `.env.local` `VITE_GOOGLE_CLIENT_ID`; `components/GoogleSignIn.jsx` (Google'ın kendi düğmesi, script sadece giriş sayfasında yüklenir, her denemede yeni nonce, `POST /auth/google` → `/auth/me`), AuthPage'de formun altında "or" ile. Yayında: Caddyfile CSP'sine `accounts.google.com/gsi` (script/style/connect/frame), frontend Dockerfile `ARG VITE_GOOGLE_CLIENT_ID`, compose `GOOGLE_WEB_CLIENT_ID` + `GOOGLE_CLIENT_IDS` (`.env.example`). Google Cloud'da yayın alan adı "Authorized JavaScript origins"e eklenmeli; telefonda LAN IP'siyle Google girişi çalışmaz (sadece localhost veya https alan adı). **Apple (2026-11-16, Claude; sadece ayarlar bekliyor):** web düğmesi `components/AppleSignIn.jsx` (Apple JS, popup, `state` kontrolü, Apple'a sha256(nonce) verilir, backend'e ham nonce + `authorization_code`; Apple kurallarına göre siyah/koyu temada beyaz düğme), Google ile birlikte `SocialSignIn.jsx` içinde (Apple önce, App Store 4.8), açık/kapalı `utils/socialConfig.js` (`VITE_APPLE_CLIENT_ID` + `VITE_APPLE_REDIRECT_URI`, https ve Apple'a kayıtlı olmalı, localhost çalışmaz). **Bağlantı iptali (App Store 5.1.1(v)):** `services/apple.py` (ES256 istemci sırrı 5 dk, `exchange_code`, `revoke`, urllib + zaman sınırı), `services/apple_links.py` (`store_refresh_token`: kodu Apple refresh token'ına çevirip `UserIdentity.provider_refresh_token`'a şifreli yazar; `revoke`). Girişte ve bağlamada kod saklanır; hesap silmede ve Apple'ı ayırmada iptal edilir. İkisi de "elden gelen": Apple'a ulaşılamazsa giriş/silme yine olur, `apple_*_failed` güvenlik loguna düşer. Yeni kolonlar `client_id`, `provider_refresh_token` (migration `b7f02a87be72`), `SocialIdentity.audience`. Ayarlar: `APPLE_CLIENT_IDS`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY` (.p8, gizli, satır sonları `\n`), web için `APPLE_WEB_CLIENT_ID`, `APPLE_REDIRECT_URI` (`.env.example`'da açıklamalı). Sahte Apple ile test edildi. Apple'ın sunucudan sunucuya bildirimleri (kullanıcı Apple tarafında bağlantıyı kaldırınca) henüz yok. **Ayarlar (2026-11-16, Claude):** "Sign-in methods" bölümü (şifre var/yok, Apple/Google bağla-ayır; son giriş yolu ayrılamaz), şifresiz hesapta Password bölümü gizli, hesap silme Google/Apple ile onaylanır. Google/Apple düğmeleri `onCredential` alır (giriş, bağlama, silme onayı aynı bileşen). Hesap silme `services/account_deletion.py` → `delete_user(db, user, by)` (uygulama ve admin aracı ortak). **Admin aracı (2026-11-17, kullanıcı yazdı):** `python -m app.scripts.admin users | show <email> | delete <email>` (argparse alt komutları; `show` sadece sayıları ve giriş yollarını gösterir, belge numarası yok; `delete` e-postayı tekrar yazdırır, `delete_user(by="admin")`). Sunucuda: `docker compose exec api python -m app.scripts.admin ...`. Web admin paneli bilinçli olarak yok (internete açık admin sayfası = saldırı yüzeyi).
- **Paylaşım kartları (2026-11-17, başladı):** tasarımlar `design/share-cards/` (1080×1920 Story, gece/kâğıt; 6 kart: signon, cosp, underway, eosp, endcontract=Homeward bound, achievement; `make.py`/`make2.py` üreticiler). Yaklaşım: harita katmanını backend SVG olarak üretir (`services/chart_render.py`, make.py'nin Python karşılığı: Mercator `Projection`, `land()` Natural Earth 10 m `app/data/land_10m.json.gz` (kamu malı, `app/scripts/build_land.py` ile üretildi, `NOTICE.txt`), `graticule`, `route`, `port_marker`, çakışmayan `port_label`, 180° için `unwrap`, `voyages_chart(legs)`); metinler `html.escape` ile. Kart verisi `services/share_cards.py` (kullanıcı yazdı: `sea_days_flag(start, end, voyages)` gün başına denizde mi, `homeward_card(contract, voyages)`), `schemas/share_card.py` `HomewardCardOut`, `GET /share-cards/contracts/{id}/homeward` (aktif kontrat 409, başkasının 404). Backend ham veri döndürür, metni frontend biçimlendirir (ileride TR). Frontend: `components/share/ShareCard.jsx` (+ `.css`, `.sc` altında, tasarımdaki ölçüler), `HomewardCard.jsx`, `ShareSheet.jsx` (önizleme, Night/Paper, `html-to-image` `toBlob` ile tarayıcıda PNG, Web Share API dosyayla → telefonun paylaş menüsü; paylaşamayan cihazda İndir), Contracts sayfasında bitmiş kontratın "⋯" menüsünde "Share card". Güvenlik kuralı: COSP kartında rota/varış yok, under way'de sadece yaklaşık bölge (kurallar backend'de uygulanacak). **EOSP kartı (2026-11-17):** `chart_render.voyage_chart(start, end, coords)` (kalkış boş halka, varış dolu; etiketlerde saat yok, saati telefon kendi saat diliminde yazar), `share_cards.eosp_card(voyage, contract_voyages)` (kullanıcı yazdı: süre, hız, `voyage_number`, `contract_day`, şerit `this`/`sea`/`port` = `sea_days_flag` iki kez + `zip`), `EospCardOut`, `GET /share-cards/voyages/{id}/eosp` (devam eden sefer 409). Frontend `EospCard.jsx`, Sea chart sefer ayrıntısında "Share card" düğmesi; varış 14 günden yeniyse paylaşım penceresinde "nerede olduğunu gösterir" notu. PNG hatası çözüldü: SVG özniteliklerindeki `var(--…)` html-to-image'da kayboluyordu → `utils/shareTheme.js` `paintSvg` renkleri yazar. Uygulamaya `ErrorBoundary` eklendi (siyah ekran yerine "Reload"). **COSP ve başarı kartları (2026-11-17, Claude):** COSP: `chart_render.departure_chart(port)` (sadece kalkış limanı + halkalar; rota ve varış asla yok), `share_cards.cosp_card` (limanın konumu derece/dakika, kontrat günü, sefer no, önceki deniz günleri), `CospCardOut`, `GET /share-cards/voyages/{id}/cosp` (devam eden seferde de çalışır). Frontend `CospCard.jsx`; Sea chart'ta devam eden seferin "Share card"ı COSP, bitmişinki EOSP; "Start voyage" kaydedilince (yeni ve devam eden sefer) COSP kartı kendiliğinden açılır (dashboard + Contracts). Başarı: backend yok, `/profile/stats`'tan çizilir: `AchievementCard.jsx` (pusula ızgarası, çevresinde "SEFERNÂME · <GRUP>" yazan halka, kadran, ortada sayı ya da başlık; alt şerit aynı merdivenin bir sonraki rozeti ya da toplam kazanılan), Profil'de rozete tıklayınca açılan kutuda "Share card". Ortak kart ayarları `components/share/targets.jsx` (`homewardTarget`, `eospTarget`, `cospTarget`, `achievementTarget`). PNG kuralı: SVG içinde CSS değişkeni ve CSS sınıfı stili PNG'ye geçmez; `paintSvg` hem `var(--…)`'yi hem `class="t|ts|deg"`'yi öznitelik olarak yazar, frontend'de çizilen SVG'ler renkleri doğrudan `CARD_THEMES`'ten alır. Dört kart iki temada headless Edge ile ekran/PNG piksel karşılaştırmasıyla doğrulandı. **Sign-on kartı (2026-11-17, model/migration/şema/create kullanıcı, kalanı Claude):** `Contract.sign_on_port_id` (opsiyonel, `ports.id` RESTRICT, migration `e39f80b5375b`, FK adı `contracts_sign_on_port_id_fkey`), `sign_on_port` ilişkisi; `ContractCreate/Update.sign_on_port_id` (null = sil), `ContractOut.sign_on_port: PortOut | None`; bilinmeyen liman 422; liste sorgusunda `selectinload`. `chart_render.signon_chart(port)` (yakın görünüm, halo + ad + "SIGN-ON"; halka yok), `share_cards.signon_card(contract, user_contracts)` (kaçıncı kontrat, aynı rütbede kaçıncı (büyük/küçük harf ve boşluk duyarsız), planlanan gün = planned ya da gerçek sign-off, gemi tipi; **gemi adı yok**: mevcut gemi gizli; limansız kontratta harita `None`), `SignOnCardOut`, `GET /share-cards/contracts/{id}/sign-on` (aktif ve bitmiş). Frontend: liman seçici ortak `components/PortField.jsx` (COSP sheet + kontrat formu "Sign-on port"), `SignOnCard.jsx` (alt yazıda "first contract at sea / first|second… contract in this rank", planlanan gün kadar boş kutu, ilki dolu), `signonTarget` (aktif ve 14 günden yeni ise "nerede olduğun belli olur" notu, liman yoksa "limanı ekle" notu). Contracts: aktif kontratta "Share card" = sign-on, bitmişte Homeward; "⋯" menüsünde her kontrat için "Sign-on card"; kartlar kendiliğinden açılır: Sign on (dashboard "Sign on" penceresi, ilk kontrat dahil; formda da "Sign-on port" var) ve Contracts'ta aktif kontrat ekleme → sign-on kartı; Sign off (dashboard ve Contracts) → Homeward bound kartı, pencere kapanınca (ref kalıbı, EOSP/COSP gibi). Kalan kart: under way (öğlen raporu ya da uyarlanmış şerit).
- **e-Devlet xlsx içe aktarma (2026-11-17; servis iskeleti, şema ve router'ın ilk kısmı kullanıcı, kalanı Claude):** kullanıcı kendi kaydını e-Devlet'ten xlsx olarak indirir; e-Devlet şifresi asla sorulmaz, e-Devlet'e bağlanılmaz. `services/sea_service_import.py`: `read_sheet(content, required, wrong_file)` (bellekte `BytesIO`, `read_only` + **`reset_dimensions()` şart**: e-Devlet dosyaya yanlış boyut yazıyor, yoksa sadece başlık okunur; başlıklar adla bulunur; en fazla 2000 satır), `to_date` (gerçek tarih hücresi ya da "26.07.2026" metni), `text` (strip, sayı → metin), `parse_sea_service` (durum "Doğrulandı"/"Yüklendi", "İptal Edildi" atlanır; bitiş boşsa hâlâ gemide). `services/certificate_import.py` → `parse_certificates` (sadece "Aktif"; "Zaman Aşımı"/"İptal Edildi" atlanır; e-Devlet sertifika tipleri `CERTIFICATE_NAMES` ile uygulamadaki İngilizce adlara (Türkçe harfler katlanarak eşleşir), bilinmeyen tip Türkçe adıyla gelir; veren kurum varsayılan "T.C. Ulaştırma ve Altyapı Bakanlığı"; geçerlilik boşsa süresiz). Hata → `ImportFormatError` → 422. `routers/imports.py`: `POST /imports/sea-service` (`SeaServiceRow` + `already_recorded` (kontrat çakışması, `check_no_overlap` kuralı) + `vessel_id` (aynı IMO ya da ad)), `POST /imports/certificates` (`CertificateRow` + `already_recorded`: şifreli numaralar açılıp karşılaştırılır ya da ad + veriliş tarihi). İkisi de **hiçbir şey kaydetmez**, dosya diske yazılmaz (`max_upload_size_mb`). Kaydetme frontend'den mevcut `POST /contracts` / `POST /certificates` ile, bütün kurallarıyla. Bağımlılık `openpyxl`. Frontend: `components/ImportSheet.jsx` (dosya seç → önizleme → tik → tek tek kaydet; zaten kayıtlılar tiksiz; hizmette şirket + rütbe bir kez girilir (e-Devlet vermiyor), yeni gemi bir kez oluşturulup sonraki satırlarda kullanılır; başarısız satırlar sebebiyle kalır; sertifika no maskeli; bilinmeyen sertifika tipi listeden eşleştirilir), Contracts şeridinin ilk sütununda "Add contract" altında "Import from e-Devlet", Certificates başlığında "Import from e-Devlet". Uygulamadaki sertifika listesine "Security-Related Familiarization" (VI/6) eklendi. Gerçek dosyalarla (10 hizmet, 15 aktif sertifika) geçici hesapta denendi.
- **Bilinçli bırakılanlar:** kayıt ekranındaki "Email already in use" (e-posta doğrulaması gelene kadar; deneme sınırı + `register_email_taken` logu var); minimum şifre 7 (kullanıcı kararı).
- Güvenlik (2026-11-16): kayıt için ayrı deneme sınırı (`register_throttle`, adres başına 15 dk'da 10, 429); login gövdesindeki token sadece `docs_enabled` iken (`Token.access_token` opsiyonel); `secret_key` en az 32 karakter (`Field(min_length=32)`).

**Frontend (Claude):**
- Giriş/kayıt tek kart (`AuthPage.jsx`, sekmeler, şifre gücü). Onboarding 4 adım (yukarıda).
- Dashboard: tek "On board" kartı (kalan gün, bugün işaretli çubuk, sefer satırı: In port → Start voyage / Under way → EOSP; Sign off kartta sadece son 14 günde, diğer zaman "⋯" menüsünde). "From ashore" kartı: TRT başlıkları + altında TCMB kurları. Yükleme iskeleti, bağlantı hatasında Retry. Onaylanmamış taramalar "Check details" der, yenilenmiş belgenin eskisi uyarı vermez.
- Profil: başlık (halka + "… sea service", "N days to go · TR rules"), tek istatistik şeridi, kazanılan rozetler madalyon (her serinin sadece en yükseği; "See all" penceresinde 25'i), "Next up" (en yakın 3), gemi tipleri, rekorlar. "Days in rank" kaldırıldı.
- Contracts: rota haritalı kontrat kartları, kaydırma (dokunma, tekerlek, sürükleme). Açık kontrat kartı iki sütun, "‹ 3 / 8 ›", "⋯" (Edit / Delete + onay), hizmet belgesi satırı. Ortak sefer listesi `components/VoyageList.jsx` (Contracts ve Sea chart; yıl çizgileri, sadece devam eden seferde "UNDER WAY", hover'da haritada vurgu).
- Sea chart kendi adresinde: `/chart?voyage=<id>` (yenileme ve geri tuşu çalışır); filtreler (gemi, yıl), etiket çakışma önleme (öncelik + hover'da ad), seçili seferin adı sağ altta.
- Tasarım kuralları için `.claude/skills/sefername-design`; gözden geçirici için uygulama özeti `docs/app-brief.md`.

**Açık kalanlar:** öğlen raporu (Noon) backend'i yok (ertelendi); hizmet belgesinin orijinal adı saklanmıyor; haber kaynağı arayüz diline göre seçilmiyor; şifremi unuttum yok (e-posta sistemi yok); deneme sınırları bellekte (çoklu worker'da Redis; 2026-11-16'dan beri üç katman: e-posta+IP 5, e-posta 20 (sıfırlanmaz, dağıtık saldırı), IP 100 (gemi/CGNAT tek IP), kayıt IP başına 30); (2026-11-16 çözüldü: kullanıcı başına 200 MB kota `settings.user_storage_limit_mb`, `storage.used_bytes` diskten sayar, `StorageQuotaError` → 413 üç yükleme endpoint'inde; `/extract` kullanıcı başına saatte 10 `settings.extract_per_hour`, `extract_throttle`, sadece OCR'a ulaşan istekler sayılır; `mrz_ocr` 50 MP sınırı (`Image.open` başlıktan ölçer, Pillow'un `DecompressionBombError`'ı `MRZNotFoundError`'a çevrilir), PDF zoom'u toplam piksele göre de sınırlı); (dosyalar, yedekler ve `uploads/` yedeği 2026-11-16'da çözüldü; belge/sertifika numaraları da şifreli); Docker hiç çalıştırılmadı; testler `mrz.py` dışında yok (MVP sonrası).

---

## 6. Ürün vizyonu

### Aşamalar
1. **Şimdi:** sadece kullanıcının kendisi için kişisel web app — profil, belgeler, kontratlar, sertifikalar.
2. **Sonra:** sefer olaylarını kaydetme ve paylaşılabilir premium kartlar.
3. **Uzun vade:** sosyal denizci platformu; şirketlere, crewing'e ve işe alımcılara ücretli B2B hizmetler; Docker ile paketlenip **App Store**'da iOS uygulaması.

### İmza konsept: The Chart
Her denizcinin tüm kariyeri, aynı zamanda doğrulanmış bir mesleki kayıt olan **canlı bir deniz haritası** olarak çizilir:
- Her kontrat harita tarzı bir tuvalde bir seyir: yıllar için dönem şeritleri, gemi silüetleri, rota değişikliği olarak rütbe değişiklikleri, kazınmış işaretler olarak geçişler, yakınlaştırılabilen notlar olarak ufuklar ve iş kartları.
- Gemi arkadaşları kesişen rotalar olarak görünür ve her seyri onaylayabilir.
- Tek dokunuşla aynı veri temiz bir **deniz hizmeti belgesi** olarak dışa aktarılır (yeterlik başvurusu / işe alımcı için), sadece seçilen bilgiler paylaşılır.

### Konseptler
- **Voyage:** sefer başlangıcı/olayları ("Commence of sea passage to America, ETA ...") Instagram'da paylaşılabilen, kendimize has tasarım dilinde kartlar. Kartı gören tasarım dilinden bizim olduğumuzu anlamalı.
- **Homebound:** sign-off kartı.
- **The Count:** kontrat geri sayımı.
- **Sea Ledger:** kariyer boyu toplamlar ("Hayatımın 4 yıl 7 ayı denizde · 11 gemi · 3 gemi tipi · 26 ülke · 180k deniz mili").
- **Sea Year:** yıllık özet kartları (Wrapped tarzı); ikinci yılın özelliği.
- **My Fleet:** çalışılan her gemi tip silüetli bir kart; hepsi bir filo duvarı. Gemi veritabanına bağımlı olma; kullanıcı tip ve boyutu girer, IMO opsiyonel. Mevcut gemi sign-off'a kadar gizli.
- **Shipmates:** aynı gemi + çakışan tarih → eşleşme. Opt-in; sadece iki tarafın da açtığı bilgi görünür. İleride doğrulama katmanı ("3 gemi arkadaşı bu kontratı onaylıyor").
- **Port Passport:** liman/ülke damgaları + "karaya çıktın mı?" anahtarı. UN/LOCODE, hızlı otomatik tamamlama. Şu anki liman gecikmeli gösterilir.
- **Job Card:** makine dairesi işleri için önce/sonra kartları. EXIF sil, gemi adı/logo bulanıklaştırma, "gemi tanımlayıcısı yok" anahtarı.
- **Crossing the Line:** Shellback, Golden Dragon, Bluenose, Horn Burnu, Panama, Süveyş sertifikaları. Hassas geçişler sadece sonradan paylaşılır.
- **While I Was Away:** sign-off'ta kaçırılan hayat olayları; Homebound'a opsiyonel katman. Ton kritik, kendine acıma gibi okunmamalı.
- **180 Horizons:** günlük ufuk fotoğrafı → kontrat sonunda mozaik/time-lapse. Offline-first, EXIF/GPS silinir.
- **Next Ticket:** bir sonraki CoC'ye ilerleme + sertifika bitiş takibi. Bayrak kurallarını kodlamak yerine kullanıcının koyduğu hedefle başla ("365 gün lazım"). Varsayılan gizli.

Bu konseptlerin hepsi şu anki veri modelinin (kontrat, gemi, sertifika, belge) üzerine kurulacak. Yeni bir özellik tasarlanırken mevcut modellerin bunu destekleyip desteklemediği kontrol edilmeli.

---

## 7. Tasarım sistemi

**Hedef:** Premium, rafine, ölçülü. Apple veya Instagram'ın elinden çıkmış gibi profesyonel hissettirmeli: her hover, basış ve geçiş düşünülmüş. **AI yapımı gibi görünmemeli.**

**Canlı referans:** `C:\Users\canug\Desktop\seafarer-panel\design\preview.html` (tüm tokenlar, butonlar, animasyonlar; tarayıcıda aç). Frontend'de tokenlar buradan kopyalanır.

### İlham (ne alınır, ne alınmaz)
- **Strava:** büyük tabular istatistikler, rota haritası bir kez çizilerek gelir, aktivite kartı düzeni. → Sea Ledger, Voyage, The Chart.
- **Apple Store:** bol boşluk, hap şeklinde butonlar, kesin tipografi, ölçülü hover. Yarı saydam bulanık üst bar (sadece orada).
- **Apple Music:** sade listeler, satır hover'ı, iOS anahtar ve segmentli seçici.
- **Instagram:** paylaşılabilir kart formatları (gönderi 4:5, story 9:16), dokunmaya anında "pop" geri bildirimi (gemi arkadaşı onayı).
- Arayüzleri **kopyalanmaz**; his ve detay özeni alınır.

### Palet (paletin dışına asla çıkılmaz)
Tek vurgu rengi ilkesi: vurgu sadece butonlar, linkler, rotalar, limanlar ve "Aktif" rozetinde. Olumlu durumlar ("Geçerli") için ayrı yeşil yok, `--text-muted` kullanılır. Yeni renk gerekirse önce palete eklenmesi tartışılır. Tüm metin renkleri iki temada da kontrast ≥ 4.5 (ölçüldü, en düşük 5.0).

| Token | Açık | Koyu | Kullanım |
|---|---|---|---|
| `--bg` | `#F6F6F4` | `#121519` | zemin, ikincil paneller |
| `--surface` | `#FFFFFF` | `#1A1E23` | kartlar, form alanları |
| `--text` | `#121519` | `#F6F6F4` | ana metin, ikonlar |
| `--text-muted` | `#5B6168` | `#9AA0A6` | açıklamalar, etiketler |
| `--line` | `#D6D8D8` | `#2A2F35` | kenarlıklar, ayraçlar |
| `--accent` | `#1E6B66` | `#4FA39C` | tek vurgu |
| `--accent-hover` | `#164F4B` | `#6DBAB3` | vurgunun hover/basılı hâli |
| `--on-accent` | `#FFFFFF` | `#121519` | vurgu zeminindeki metin |
| `--accent-soft` | vurgu %10 | vurgu %14 | ikincil buton, satır hover'ı, "Aktif" rozeti zemini |
| `--warning` | `#9A5B0E` | `#E3B15A` | süresi yaklaşan, şüpheli OCR alanı |
| `--danger` | `#A93226` | `#E57A6E` | süresi dolmuş, hata |

**Rütbe apoletleri (`components/Epaulette.jsx`, 2026-11-04):** lacivert apolet + altın şerit; şerit sayısı kıdem (4→1, cadet ince yarım şerit), güverte zabitine elmas, makineye mor ara dolgu, ETO'ya yeşil, ratinglere sadece amblem (güverte elmas, makine pervane). Bu renkler (`--gold`, `--board`, `--board-edge`, `--engine-purple`, `--eto-green`) **sadece apolet içindir**, genel arayüzde kullanılmaz.

**Paylaşım kartları (Voyage, Homebound, Sea Ledger...) henüz tasarlanmadı.** En sona bırakıldı; kullanıcı o aşamada farklı istekler getirecek. `preview.html`'deki 4:5 kart sadece yer tutucu, kural değil.

### Tipografi
- Font **Manrope**; ağırlıklar sadece **400** (metin), **500** (etiket, sayı), **600** (başlık, buton), **700** (sadece marka adı).
- Aşırı büyük başlık, aşırı kalın metin, dekoratif tipografi yok.
- Tüm sayılarda (gün, tarih, mesafe, DWT, kW, deniz mili) **`font-variant-numeric: tabular-nums`**.

| Ad | Boyut / satır yüksekliği | Kullanım |
|---|---|---|
| Display | 28 / 34 | sadece istatistik sayıları |
| Title | 22 / 28 | sayfa başlığı |
| Subhead | 18 / 26 | bölüm başlığı |
| Body | 16 / 24 | ana metin |
| Small | 14 / 20 | liste, form, buton |
| Caption | 12 / 16 | etiket, yardım metni; büyük harf etiketlerde `letter-spacing: .08em` |

### Şekil ve boşluk
- Köşe: `--r-sm` 8 (form alanı), `--r-md` 14 (kart, liste), `--r-lg` 22 (paylaşım kartı, sheet), `--r-full` (buton, rozet, anahtar, seçici).
- Boşluk 4 px ızgarası: 4, 8, 12, 16, 24, 32, 48.
- Kartlar gölgesiz, 1 px `--line` kenarlıkla ayrılır. **Gölge (`--shadow-float`) sadece yüzen katmanlarda:** toast, sheet, menü.
- Yarı saydam bulanık arka plan (`backdrop-filter`) **sadece üst barda**.
- Dokunma hedefi en az **44 px** (Apple kuralı).

### Hareket
| Token | Değer | Kullanım |
|---|---|---|
| `--dur-1` | 120 ms | basma, renk değişimi |
| `--dur-2` | 200 ms | hover, anahtar, seçici |
| `--dur-3` | 320 ms | giriş/çıkış (toast, sheet), tema geçişi |
| `--dur-draw` | 1400 ms | rota çizimi, sayaç; **sadece bir kez** |
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | varsayılan |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | iki durum arası geçiş |
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | sadece "pop" geri bildirimi (onay, anahtar topu) |
| `--press-scale` | 0.97 | basılı buton |

Kurallar:
- Her hareketin bir amacı olur (geri bildirim, yön, durum değişimi). Süs animasyonu, sürekli dönen/titreyen şey yok.
- Sadece `transform` ve `opacity` canlandırılır (akıcı 60 fps); genişlik/yükseklik/konum canlandırılmaz.
- `prefers-reduced-motion: reduce` açıksa animasyonlar kapanır.

### Etkileşim durumları
- **Hover** (sadece `@media (hover: hover)`, telefonda yok): renk `--accent-hover`'a koyulaşır; liste satırına `--accent-soft` zemini, ok işareti 3 px sağa. Yukarı kalkma, gölge, büyüme yok.
- **Basma:** buton `scale(0.97)`, 120 ms.
- **Odak:** sadece klavyeyle (`:focus-visible`): 2 px zemin + 2 px vurgu halkası.
- **Devre dışı:** opaklık 0.4, hover/basma yok.
- **Yükleniyor:** dönen çark yerine gelecek alanların iskeleti (shimmer); butonda küçük çark + "Okunuyor". Veri gelince alanlar 60 ms arayla belirir.
- **Başarı:** alttan çıkan toast (320 ms), 2.4 sn sonra kaybolur.
- Buton türleri: birincil (dolu vurgu), ikincil (`--accent-soft` zemin), düz (sadece metin).

### "AI yapımı gibi görünmesin" — kaçınılacaklar
- Mor-mavi gradyanlar, her yerde glassmorphism, neon parlamalar
- Her kartta gölge; her şeyin ortalandığı sayfalar
- Emoji ikonlar, jenerik ikon setlerinin rastgele kullanımı, stok illüstrasyonlar
- Jenerik "hero" bölümleri ve pazarlama dili, lorem ipsum
- Gereksiz veya tekrar eden animasyon

### Yön
- Kendine has görsel dil: deniz haritası referansları (ince kazınmış ızgara çizgileri, koordinat/ölçek detayları, rota çizgisi) ölçülü şekilde.
- Gerçek verilerle tasarla.
- Paylaşılabilir kartlar en son tasarlanacak; kullanıcıyla sıfırdan konuşulacak. Kendi kendine kart stili belirleme.

---

## 8. DevOps yol haritası
1. Otomatik testler (pytest)
2. Docker + docker-compose (uygulama + Postgres; Tesseract Dockerfile'da)
3. CI (GitHub Actions): her push'ta testler
4. Deploy: Neon + sunucu, ortam ayarları, loglama, health check; dosyalar için nesne deposu (S3/R2)
5. iOS / App Store (gizlilik politikası, veri silme, KVKK/GDPR uyumu)

Her adımda kullanıcıya DevOps açısından "neden"ini anlat; bu kısım kullanıcının uzmanlaşmak istediği alan.

---

## 9. Sık kullanılan komutlar
Uygulamayı tek komutla açmak (proje kökünde, git dışında): `.\start.ps1` (backend ve frontend için iki PowerShell penceresi açar, sonra tarayıcıyı). Çift tıklama Notepad'de açar; sağ tık → Run with PowerShell.

```
venv\Scripts\activate
uvicorn app.main:app --reload          # Swagger: http://127.0.0.1:8000/docs
alembic revision --autogenerate -m "..."
alembic upgrade head
alembic current | alembic heads | alembic check
git status | git add . | git commit -m "..."
pip freeze | Out-File -Encoding ascii requirements.txt   # ">" PowerShell 5.1'de UTF-16 yazar
```

### Frontend (`seafarer-panel-frontend/`, React 19 + Vite 8, düz JavaScript)
```
npm run dev        # sadece bu bilgisayar: http://localhost:5173
npm run dev:lan    # telefondan da: http://<bilgisayarın Wi-Fi IP'si>:5173 — SADECE ev Wi-Fi'ında
npm install <paket>
```
- Backend adresi **tek yerde**: `src/api/client.js` (`apiRequest`). Geliştirmede `/api` → Vite proxy → `http://127.0.0.1:8000` (`vite.config.js`; `/api` öneki silinir). Bu yüzden geliştirmede CORS devreye girmez ve telefon da backend'e Vite üzerinden ulaşır; backend ağa açılmaz.
- Backend başka portta çalışıyorsa: `$env:BACKEND_URL="http://127.0.0.1:8001"; npm run dev`
- Yayında: `VITE_API_URL` ile gerçek API adresi verilir; backend'de `cors_origins` (`.env`) o adrese ayarlanır. `["*"]` asla.
- Font: `@fontsource/manrope` (400/500/600/700, `main.jsx`'te import). Google Fonts linki kullanılmaz (kullanıcı IP'si Google'a gider, GDPR).
- Tokenlar: `src/index.css` (bölüm 7 ile aynı). Koyu tema şimdilik işletim sistemi ayarını izler.
