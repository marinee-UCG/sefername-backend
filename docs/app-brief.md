# Sefernâme: gözden geçirici için uygulama özeti

Bu dosyayı, uygulamayı ilk kez görecek bir gözden geçiriciye (insan veya AI) ver. Amaç: önerilerin bu uygulamaya ve bu aşamaya uyması.

## Ne, kimin için

Sefernâme, gemi adamlarının (zabit ve tayfa, güverte ve makine) kariyer defteri. Kontratlarını, seferlerini, sertifikalarını ve kimlik belgelerini (pasaport, gemici cüzdanı, sağlık belgesi) tek yerde tutar; deniz sürelerini, rotalarını ve kariyer istatistiklerini bunlardan hesaplar.

Kullanıcı uygulamayı şu anlarda açar:
- **Gemiye katılınca / ayrılınca:** kontrat başlatır, sign-off yapar.
- **Limandan çıkınca / varınca:** seferi başlatır (COSP), bitirir (EOSP).
- **Bir belge dolmak üzereyken:** sertifika ve belge bitiş tarihlerini kontrol eder.
- **Terfi veya yeterlik başvurusu öncesi:** deniz süresini ve rütbedeki günlerini görmek ister.
- **Evdeyken, merak edince:** haritada kariyerine, profil istatistiklerine bakar.

Gemide internet yavaş, pahalı veya kesintili olabilir; telefon gemi saatini tutar (bu yüzden ev saati ayrıca saklanır).

## Aşama

- **MVP**, şimdilik sadece kişisel kullanım. Sosyal özellikler, paylaşılabilir kartlar ve ücretli hizmetler sonraki aşamalar.
- Bir **öğrenme projesi**: geliştirici backend ve DevOps öğreniyor. Backend kodunu çoğunlukla kendisi yazıyor; açıklanabilir, sade çözümler, zekice ama karmaşık olanlardan iyidir.
- Hedef: Docker ile yayına alma (Hetzner), ileride **native iOS uygulaması**. API bu yüzden istemciden bağımsız tasarlanmalı (web'e özel varsayım yok).
- Otomatik testler bilinçli olarak MVP sonrasına bırakıldı; "test yaz" önerisi şimdilik öncelik değil.

## Ekranlar

| Sayfa | Ne yapar |
|---|---|
| Giriş / kayıt | Tek kart, iki sekme |
| Onboarding | İsim, departman, rütbe. Denizde mi evde mi kontratlardan hesaplanır, sorulmaz |
| Overview | Bugünkü durum: gemide kaçıncı gün veya evde kaçıncı gün, aktif sefer, yaklaşan belge bitişleri |
| Contracts | Dünya haritası sayfanın kendisi; altta kontrat kartları; açılan kontratta sefer günlüğü, COSP/EOSP formları |
| Documents | Pasaport, gemici cüzdanı, sağlık belgesi; pasaportun MRZ satırları yerel OCR ile okunur |
| Certificates | STCW ve diğer sertifikalar, bitiş takibi |
| Profile | Deniz süresi, terfiye ilerleme, gemi tipleri, rozetler (milestones), rekorlar |
| Settings | Şifre, ev saat dilimi, veriyi dışa aktarma, hesabı silme |

**Teknik:** FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic, JWT (httpOnly cookie + refresh token), Tesseract OCR. Frontend React 19 + Vite, düz JavaScript, kendi CSS token'larımız (Tailwind yok).

## Değişmeyecek kararlar (bunlara ters öneri getirme)

**Güvenlik ve gizlilik:**
- `user_id` her zaman token'dan gelir; başkasının kaydı istenirse 404 döner (403 değil).
- Token sadece httpOnly cookie'de; localStorage'da sadece tema tercihi.
- OCR ile okunan veri kullanıcı onaylayana kadar doğru sayılmaz (`verified=False`); pasaport verisi loglanmaz.
- Sırlar `.env`'de; CORS asla `*` değil.
- Fontlar kendi sunucumuzda (Google Fonts yok); OpenStreetMap atfı kalır.

**Tasarım:**
- Premium ve ölçülü; "AI yapımı gibi" görünmemeli (mor gradyan, her yerde cam efekti, emoji ikon, pazarlama dili yok).
- Tek vurgu rengi (teal), açık ve koyu tema.
- Kartlarda gölge yok; gölge sadece yüzen katmanlarda (açılır menü, sheet). Bulanık arka plan sadece üst barda.
- Hover'da kart yükselmesi yok. Animasyonlar sadece transform ve opacity ile; "hareketi azalt" ayarına uyulur.
- Sayılar tabular rakamlarla. Yükleme ekranında spinner değil iskelet.
- Arayüz metinleri İngilizce.

## Senden beklenen

Sana bir sayfanın ekran görüntüleri (masaüstü ve telefon, açık ve koyu tema) ve o sayfanın kodu (frontend ve ilgili backend) verilecek.

- **Sadece somut bulgular.** "Erişilebilirliği iyileştir" değil; "telefonda X butonu 32 px, dokunma alanı 44 px olmalı".
- Her bulgu için: **önem** (yüksek / orta / düşük), **yer** (dosya:satır veya ekrandaki yer), **sorun**, **neden önemli**, **öneri**, **tahmini iş** (küçük / orta / büyük).
- Önce kullanıcıyı gerçekten etkileyenler: yanlış veri, kaybolan veri, güvenlik açığı, telefonda kullanılamayan bir şey. Zevk meselesi en sonda.
- Emin olmadığın şeyi "emin değilim" diye işaretle.
- Yukarıdaki kararlara ters düşen öneri getirme; bir kararın yanlış olduğunu düşünüyorsan ayrı bir not olarak gerekçesiyle yaz.
