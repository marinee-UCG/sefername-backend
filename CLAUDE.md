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

**Frontend (henüz başlamadı):** React (Vite).

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
- Auth: `POST /auth/register` (sadece email + şifre, min 7), `POST /auth/login` (OAuth2 form, JWT 30 dk, httpOnly cookie), `POST /auth/logout`, `GET /auth/me`, `PATCH /auth/me` (`UserUpdate`: full_name, rank; full_name bir kez girilince null yapılamaz → 422)
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
- **Açık sorun:** Tesseract `eng` modeli pasaport fontunu (OCR-B) tanımıyor. Kullanıcının gerçek pasaportunda `<`→`K` (isim `UGUR CAN` yerine `UGUR KCANK K`) ve `9`→`I` (doğum yılı; kontrol hanesi yakaladı) hataları var; süre ~17 sn. Çözüm: OCR-B / MRZ `.traineddata` modeli (projede bir klasöre, `--tessdata-dir` ile). Henüz kurulmadı.

### Sıradaki işler (sırayla)
1. ~~MRZ endpoint'i~~ **bitti:** `POST /identity-documents/{id}/extract` (sırayla: pasaport değil 422, dosya yok 422, dosya diskte yok 404, onaylı 409, `MRZError` 422). `personal_number` (TC kimlik no) **saklanmaz** (veri minimizasyonu). `verified=False` kalır.
2. **pytest — yarıda bırakıldı, frontend'den sonra dönülecek:** kurulu (`pytest.ini`: `pythonpath = .`, `testpaths = tests`). `tests/test_mrz.py`'de 5 test var (3 kontrol hanesi, `pytest.raises` ile küçük harf, ICAO `parse_td3` sözlük+döngü). Kaldığı yer: 6. adım, OCR hatası testi (`L898`→`LB98`; `checks.document_number` False, `birth_date` True). Sonra endpoint testleri (httpx2 + TestClient).
3. **Frontend:** palet, tipografi ve hareket kuralları **belirlendi** (bölüm 7, `design/preview.html`). Kurulum bitti (Vite + React, tokenlar, Manrope, CORS, `/api` proxy, `dev:lan`). Sıradaki: **login sayfası.** **KARAR (2026-11-03): token httpOnly cookie'de** (localStorage değil; XSS ile çalınamasın). Plan, sırayla: (1) backend `POST /auth/login` token'ı cookie olarak gönderir: `HttpOnly`, `SameSite=Lax`, `Secure` sadece yayında (ayar), `max_age` = token süresi; (2) `get_current_user` önce cookie'yi, yoksa `Authorization` başlığını okur (Swagger ve ileride iOS için); (3) `POST /auth/logout` cookie'yi siler; (4) frontend token'ı hiç görmez, giriş durumu `GET /auth/me` ile anlaşılır (200/401); (5) login sayfası. Backend adımları (1)–(3) **bitti**: login cookie bırakır (gövdede token Swagger için durur), `get_current_user` önce cookie sonra başlık (`auto_error=False`), `POST /auth/logout` 204. Logout token'ı iptal etmez (JWT 30 dk geçerli kalır; çözüm refresh token). Şifre kuralı: min 7 (kullanıcı kararı; 8 önerildi), max 128. Frontend (4)–(5) **bitti**: `LoginPage` (state, `onSubmit`, hata + bekleme durumu, tasarım), `App` kullanıcıyı tutar (`onLogin` prop), açılışta `useEffect` ile `/auth/me` kontrolü (`checking` iken `null` çizer), çıkış butonu. Login arka planı: `components/ChartBackground.jsx` (OSM İstanbul Boğazı kıyı çizgisi, 5′ ızgara, Mercator; veri `scripts/make_chart.py` ile üretilir; `© OpenStreetMap contributors` yazısı lisans gereği kalmalı). Router (react-router 8) kuruldu; `RegisterPage` (email, şifre + şifre tekrarı, frontend'de eşleşme kontrolü). **Kullanıcı kararı: sıradaki iş ONBOARDING, sonra uygulama iskeleti.**

### Onboarding — hazır olan iskelet (2026-11-04)
- Kural: `full_name` boşsa kullanıcı onboarding'i bitirmemiş sayılır. `App.jsx`'te `needsOnboarding`; `/` → `/onboarding`'e, onboarding bitmişse `/onboarding` → `/`'e yönlendirir. Bilinmeyen adresler → `/`.
- `src/pages/OnboardingPage.jsx` şimdilik **yer tutucu** (karşılama + çıkış). Hazır prop'lar: `user`, `onComplete(updatedUser)` (PATCH sonrası çağrılınca App ana sayfayı açar), `onLogout`.
- Backend: `PATCH /auth/me` ile ad ve rütbe kaydedilir.
- **Kesin:** ilk soru ad soyad (kayıt formundan kaldırıldı).
- **KARARLAR (kullanıcı, 2026-11-04):** her soru ayrı ekran, üstte ilerleme çubuğu. Ekran sırası: (1) ad soyad, (2) departman (güverte/makine), (3) rütbe, (4) şu an gemide mi evde mi, (5) gemideyse "gemiye ne zaman çıktın", evdeyse "gemiden ne zaman indin" (tarih), (6) **profil kartı / özet** — kullanıcı tüm cevapları görür, her satırdan ilgili ekrana dönüp düzeltebilir; "Confirm" ile `POST /auth/onboarding` gider (kullanıcı kararı 2026-11-04), Confirm → `onComplete(user)` → doğrudan dashboard. **Belge yükleme onboarding'den çıkarıldı (2026-11-04), dashboard'dan yapılacak.** Onboarding BİTTİ.

### Seferler (Voyage) + Seyir haritası — KARARLAR (2026-11-04)
- Sıra: (1) Port modeli + seed migration, (2) Voyage modeli + şemalar + kurallar, (3) `services/routing.py` (searoute; **önce lisansı kontrol et**: kütüphane + deniz yolu ağı verisi), (4) endpoint'ler, (5) pytest, (6) frontend (tasarım: kullanıcı `design/` altına preview.html atacak, frontend'e gelince iste).
- **EOSP ayrı aksiyon:** `POST /voyages/{id}/eosp` (sadece aktif sefer, iki kez bitirilemez 409, eosp > cosp 422). Düzeltme için PATCH sonra.
- **Sefer kontrata zorunlu bağlı.** Gemideki kullanıcı önce aktif kontratını ekler (dashboard'da yönlendirme). `user_id` hep token'dan; kontrat kullanıcının değilse 404.
- **`contract_id` → `ondelete=RESTRICT`** (kontrat silinince seyir defteri gitmesin; seferli kontrat silinmek istenirse 409). `user_id` → CASCADE (hesap silme). Port FK'leri RESTRICT.
- Bir kontratın seferleri: `GET /voyages?contract_id=5` (ayrı endpoint yok).
- **Limanlar kendi tablomuzda.** **Güncelleme:** veri kaynağı searoute paketinin kendi `data/ports.geojson` dosyası (3962 liman: UN/LOCODE, ad, ülke, lon/lat). Migration sadece tabloyu kurar; veri `scripts/import_ports.py` ile yüklenir (locode'a göre upsert, tekrar çalıştırılabilir). Veride küçük hatalar var (ör. "Bandirmar") → tek tek düzeltilir.
- **Lisans kontrolü (2026-11-04):** searoute-py kodu **Apache-2.0** (ticari kullanım serbest, lisans metni korunmalı). Deniz yolu ağı Eurostat SeaRoute'tan (**EUPL-1.2**), o da ORNL "Global Shipping Lane Network" verisine dayanıyor. Liman verisinin kaynağı pakette belgelenmemiş. Geliştirme için sorun yok; **ticari yayından önce** veri lisansları (EUPL'nin ağ üzerinden sunma maddesi dahil) bir hukukçuyla netleştirilmeli. searoute "not for routing purposes": biz sadece görselleştirme için kullanıyoruz, uygun.
- Zamanlar UTC saklanır (`timezone=True`); formda gemi saati/UTC girişi frontend'de kararlaştırılacak.
- Mesafe ve rota saklanmaz, liman çiftinden hesaplanır. Güncel konum en yakın dereceye yuvarlanır, `approximate: true`.
- **Önerilen model (kullanıcı onayı bekliyor):** User'a `department` (deck/engine), `at_sea` (bool), `status_since` (date), `onboarded_at` (datetime) eklenir + migration. Tamamlanma işareti `full_name` yerine `onboarded_at` olur (ad 1. ekranda kaydedilse bile kullanıcı ana sayfaya fırlamasın). Cevaplar frontend state'inde toplanır, son zorunlu ekranda tek istekle `POST /auth/onboarding` gönderilir; backend `onboarded_at`'i kendisi koyar (istemci zaman damgası göndermez). Rütbe: departmana göre liste + "Other" (öneri).
4. Liman cüzdanı çıkarma: yöntem sonra kararlaştırılacak (MRZ yok).
5. OCR-B modeli ile isim doğruluğu.

### Bilinen açıklar / yapılacaklar
- Kullanıcı silinince `uploads/<user_id>/` temizlenmeli (kullanıcı silme endpoint'i eklendiğinde)
- Refresh token, login rate limiting
- Dosyaların ve hassas alanların şifrelenmesi
- Otomatik testler: sadece `mrz.py` için başladı; endpoint'ler hâlâ Swagger'da elle test ediliyor
- `requirements.txt` güncellerken `>` kullanma (PowerShell 5.1 UTF-16 yazar): `pip freeze | Out-File -Encoding ascii requirements.txt`
- CORS (frontend başlayınca)

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
