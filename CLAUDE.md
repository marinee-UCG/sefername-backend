# CLAUDE.md — Seafarer Panel (çalışma adı, uygulama ismi henüz belli değil)

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
    └── services/       (iş mantığı; mrz.py yazılacak)
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
- Auth: `POST /auth/register`, `POST /auth/login` (OAuth2 form, JWT, 30 dk), `GET /auth/me`
- **Contracts** (`/contracts`): tam CRUD. Kurallar: tek aktif kontrat (409), bitiş > başlangıç (422), POST'ta `vessel_id` **veya** yeni `vessel` (tam olarak biri), yeni gemi + kontrat tek transaction, PATCH'te yeniden açma kontrolü. Cevapta iç içe `vessel`.
- **Vessels** (`/vessels`): `GET` (alfabetik), `PATCH /{id}`. Gemi kontrat üzerinden eklenir.
- **Certificates** (`/certificates`): tam CRUD; liste bitiş tarihine göre, süresizler sonda (`nulls_last`).
- **Identity documents** (`/identity-documents`): pasaport + liman cüzdanı tek tablo (`doc_type`). Elle giriş CRUD (`verified=True`), `POST /upload` (multipart, `verified=False`), `GET /{id}/file` (korumalı indirme), DELETE dosyayı da siler.

### Modeller (özet)
- **User:** email (unique), hashed_password, full_name, rank?, created_at
- **Vessel:** user_id, name, imo?, vessel_type?, flag?, dwt?, gt?, main_engine?, kw?
- **Contract:** user_id, vessel_id (RESTRICT), company, rank, start_date, end_date? (boş = aktif), `vessel` relationship
- **Certificate:** user_id, cert_name (150), cert_number, issue_date, expiry_date?, issuing_inst
- **IdentityDocument:** user_id, doc_type, document_number?, issuing_country?, issue_date?, expiry_date?, file_path?, extracted_data (JSONB)?, verified, created_at

### Sıradaki iş: pasaport MRZ okuyucu (AI'sız, lokal OCR)
Dosya: `app/services/mrz.py`
1. `compute_check_digit(data: str) -> int` — **kullanıcı yazacak.** ICAO 9303: rakam=değeri, A–Z=10–35, `<`=0; ağırlıklar 7,3,1 tekrar; toplam % 10.
   Test (ICAO örneği): `"740812"`→2, `"L898902C3"`→6, `"120415"`→9
   ```
   P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
   L898902C36UTO7408122F1204159ZE184226B<<<<<10
   ```
2. TD3 ayrıştırma (2 × 44 karakter) + tüm kontrol haneleri + genel kontrol hanesi; tarihlerde yüzyıl çözümü.
3. Görüntü boru hattı: PDF → resim (pymupdf) → alt kısmı kes → gri ton → Tesseract (whitelist `A-Z0-9<`) → 44 karakterlik iki satırı bul.
4. Endpoint: yüklenen belgeden çıkar → `extracted_data` + alanları doldur, `verified=False`; kullanıcı PATCH ile onaylar.
5. Liman cüzdanı çıkarma: yöntem sonra kararlaştırılacak (MRZ yok).

### Bilinen açıklar / yapılacaklar
- Kullanıcı silinince `uploads/<user_id>/` temizlenmeli (kullanıcı silme endpoint'i eklendiğinde)
- Refresh token, login rate limiting
- Dosyaların ve hassas alanların şifrelenmesi
- Otomatik testler (pytest) — şu an Swagger'da elle test ediliyor
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

**Hedef:** Rafine, ölçülü, premium. Apple'ın detaya gösterdiği özenden ilham, arayüzünü kopyalamadan. **AI yapımı gibi görünmemeli.**

### Palet
- **Henüz belirlenmedi.** Herhangi bir arayüz yazılmadan önce kullanıcıyla birlikte tek bir palet belirlenecek ve design token olarak tanımlanacak (CSS değişkenleri; açık + koyu tema).
- Sonrasında **paletin dışına asla çıkılmaz**; tek seferlik renk eklenmez. Yeni bir renk ihtiyacı doğarsa önce palete eklenmesi tartışılır.

### Tipografi
- Font: **Manrope**
- Tutarlı bir tip ölçeği ve hiyerarşi kur.
- Ağırlıklar sadece **400, 500, 600, 700**.
- Aşırı büyük başlıklar, aşırı kalın metin ve dekoratif tipografi yok.
- İstatistiklerde, tarihlerde, sürelerde ve ölçümlerde (gün sayıları, DWT, kW, deniz mili) **tabular rakamlar** (`font-variant-numeric: tabular-nums`).
- Mükemmel okunabilirlik ve tutarlı satır yükseklikleri.

### "AI yapımı gibi görünmesin" — kaçınılacaklar
- Mor-mavi gradyanlar, her yerde glassmorphism, neon parlamalar
- Her şeyin yuvarlak köşeli kart + gölge olduğu düzenler; her şeyin ortalandığı sayfalar
- Emoji ikonlar, jenerik ikon setlerinin rastgele kullanımı, stok illüstrasyonlar
- Jenerik "hero" bölümleri ve pazarlama dili, lorem ipsum
- Gereksiz animasyon

### Yön
- Kendine has bir görsel dil: deniz haritası referansları (ince kazınmış çizgiler, harita tipografisi hissi, koordinat/ölçek detayları) ölçülü şekilde.
- Gerçek verilerle tasarla.
- Paylaşılabilir kartlar (Voyage, Homebound, Sea Ledger...) aynı tasarım dilini taşımalı ve tanınabilir olmalı.

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
pip freeze > requirements.txt
```
