# Profil sayfası ve `/profile/stats` — tasarım

Tarih: 2026-11-11 · Durum: onaylandı (kullanıcı, 2026-11-11)

## Neden

Uygulamada kişinin kendi deniz hayatını tek bakışta gördüğü bir yer yok. Kariyer toplamları (Sea ledger) eski kontrat sayfasıyla birlikte kayboldu. Kontrat sayfasının başlığında yalnızca birkaç rakam duruyor.

Profil sayfası bir **vitrin**. Kullanıcı onu kendisi için açar, başkasına göstermek için değil. Açtığında "bunu büyütmek istiyorum" demeli. Bu his elle veri doldurmaktan gelmiyor; denizde geçen zamandan ve geçilen eşiklerden geliyor. Sayfadaki her şey mevcut kontrat ve sefer kayıtlarından hesaplanır, kullanıcı yeni bir şey girmez.

## Hedefler

- Kariyer toplamlarını tek yerde göstermek: deniz günleri, sefer, mil, liman, ülke, gemi, şirket.
- Eğlenceli ama gerçek verilerden çıkan bilgiler göstermek: gemi tipine göre tecrübe, rütbedeki günler, en uzun kontrat ve sefer, en çok uğranan liman, kaç kez dünya turu atıldığı.
- **Rütbe ilerlemesi:** TR yönetmeliğine göre bir sonraki rütbenin sınavı için 900 gün deniz hizmeti gerekiyor. Sayfa bunun ne kadarının dolduğunu gösterecek.
- **Milestone rozetleri:** eşikler geçildikçe kazanılır. Kazanılmayanlar soluk durur ve hedef olur.
- Hesaplar backend'de yapılacak. İleride native iOS uygulaması da aynı uç noktayı kullanacak.

## Hedef dışı

- Başkalarıyla paylaşma ve herkese açık profil. Paylaşım kartları ayrı bir iş, hafızada duruyor.
- Profil fotoğrafı, uyruk, doğum tarihi gibi yeni kişisel alanlar. Yeni veri toplanmayacak.
- Sertifika tarihinden sayım. Sertifikanın ne zaman alındığını bilmiyoruz (aşağıya bakın).
- Hesapları önbelleğe almak veya bir tabloda saklamak. Gerekirse sonra yapılır.

## Kaçınılacaklar

Teknik olarak çalışsa bile şunlar olursa iş başarısız sayılır:

- **"Yapay zekâ yapmış" görüntüsü.** Emoji, gösterişli gradyan, süs amaçlı uydurma rakam, kalabalık konfeti efekti olmayacak. Görünüm profesyonel ve sade olmalı:
  - mevcut renkler ve fontlar kullanılır,
  - ikonlar uygulamanın çizgi ikonlarından seçilir,
  - hiyerarşiyi rakamlar ve tipografi taşır.
- **Yanlış kural göstermek.** 900 gün kuralı "TR yönetmeliği" olarak etiketlenir. Kesinmiş gibi yanlış bir yasal iddia yazılmaz.
- **Kişisel veriyi sızdırmak.** Uç nokta yalnızca giriş yapan kullanıcının verisini döner. `user_id` her zaman token'dan alınır.

## Tasarım yönü (kullanıcı seçti: "B · Progress hero")

Taslak: `.superpowers/brainstorm/.../content/profile-layout.html`, seçenek B.

1. **Üst kart (hero):**
   - Solda bir halka: mevcut basamaktaki hizmet / 900 gün.
   - Sağda rütbe, isim ve tek bir cümle, örneğin "360 days to the sea service for the Chief Engineer exam (TR)".
   - Altında kazanılmış en yeni 3 rozet.
2. **Sea ledger kutucukları:**
   - deniz günleri, "x yıl"
   - mil, "x kez dünya turu"
   - en uzun kontrat
3. **Gemi tipine göre deniz zamanı:** tek yatay şerit, yüzdelerle. Altında tip, gün ve yüzde listesi.
4. **İkinci sıra kutucuklar:**
   - en çok uğranan liman
   - evde / denizde oranı
   - sıradaki milestone ve ne kadar kaldığı
5. **Milestones bölümü:** bütün rozetler kategoriye göre gruplanır. Kazanılanların yanında kazanılma tarihi, kazanılmayanların yanında ilerleme ("640 / 1,000 days") yazar.
6. **Rütbeye göre günler:** küçük bir liste.

Sayfa yeri: `/profile` rotası. Sağ üstteki kullanıcı menüsüne "Profile" eklenir. Settings ayrı kalır.

Telefonda her şey tek sütun olur. Halka küçülür ama korunur.

CLAUDE.md bölüm 7'ye uyulur:
- Kartlar gölgesiz, 1 px `--line` kenarlıklı.
- Bulanık arka plan yok.
- Hover'da yukarı kalkma ve büyüme yok.
- Vurgu rengi tek: `--accent`. Gemi tipi şeridindeki tonlar bu rengin açık tonlarından üretilir.
- Bütün sayılar `tabular-nums`.
- Halka sayfa açılınca **bir kez** dolarak gelir (`--dur-draw`). "Hareketi azalt" açıksa animasyon olmaz.

## Kurallar ve hesaplar

### Deniz günü

Bir kontratın günü, sign-on'dan sign-off'a kadar geçen süredir. Aktif kontratta bitiş tarihi bugün kabul edilir. Bu, kontrat sayfasındaki `daysBetween` ile aynı hesap; iki sayfa aynı sonucu vermeli.

### Diğer toplamlar (benim kararım)

- **`sea_years`:** `sea_days / 365.25`, tek ondalık. "3.2 years of your life" cümlesinde kullanılır.
- **`home_days`:** kontratlar arasındaki boşlukların toplamı. Şu an evdeyse son sign-off'tan bugüne geçen süre de eklenir.
- **Evde / denizde oranı:** `sea_days / (bugün − ilk sign-on)`.
- **Mesafe (kullanıcı kararı):** bitmiş seferlerin tam rota mesafesi, artı yolda olan seferde **şimdiye kadar katedilen mil**. Katedilen mil, `/map`'teki yaklaşık konumla aynı hesaptan gelir: 12 kn plan hızıyla geçen süre, en fazla rotanın tamamı. Bu yüzden profildeki toplam, `/map` toplamından küçük olabilir. `/map` yolda olan seferin tamamını sayıyor, bu beklenen fark.
- **Limanlar ve ülkeler:** seferlerin kalkış ve varış limanlarından sayılır.
- **900 sabiti:** kodda dağınık durmaz, `core/config.py` içinde `settings.promotion_service_days` olarak tutulur.

### Rütbe basamakları (benim kararım, okurken kontrol et)

TR'deki sınav basamaklarına göre gruplandı. Aynı basamaktaki rütbelerin günleri toplanır:

| Basamak | Rütbeler (kontrattaki metin) | Sonraki sınav |
|---|---|---|
| Makine – vardiya | Fourth Engineer, Third Engineer | Second Engineer |
| Makine – ikinci | Second Engineer | Chief Engineer |
| Makine – baş | Chief Engineer | — (zirve) |
| Güverte – vardiya | Third Officer, Second Officer | Chief Officer |
| Güverte – birinci | Chief Officer | Master |
| Güverte – kaptan | Master | — (zirve) |

- **Hangi basamak:** kullanıcının mevcut rütbesi (`users.rank`).
- **Halka:** mevcut basamağa ait bütün kontratların günlerinin toplamı / 900.
- **900'e ulaşınca** halka dolar ve "Sea service complete for the … exam" yazar. "Sınavı geçtin" demez.
- **Listede olmayan rütbelerde** (Cadet, Bosun, ETO, elle yazılmış "2/E" gibi; kullanıcı kararı) rütbe ilerlemesiyle ilgili **hiçbir şey gösterilmez**: halka da, "x days as" kartı da çıkmaz. Hero kartı halkasız olur: rütbe, isim ve rozetler.
- **Zirve rütbede** (Chief Engineer, Master) halka gösterilmez, yerine "x days as Chief Engineer" yazar (benim kararım).
- Rütbe karşılaştırması büyük/küçük harfe duyarsızdır.

### Rotalardan çıkan geçişler

Bunlar seferin **hesaplanmış deniz rotası** üzerinden bulunur (`/map`'teki `sea_route` ile aynı). Gerçek GPS izi değildir. Rozet açıklamasında "on your recorded routes" yazar.

- **Ekvator:** rota üzerinde enlem işareti değişirse.
- **Tarih değiştirme hattı:** boylam bir noktadan sonrakine ±180 sıçrarsa.
- **Süveyş, Panama, Cebelitarık, İstanbul Boğazı, Ümit Burnu:** rota ilgili kutunun içinden geçerse. Kutuların koordinatları builder'a bırakıldı, kodda sabit olarak durur.
- **Kazanılma tarihi:** o geçişi içeren ilk seferin EOSP tarihi.
- **Yolda olan sefer (kullanıcı kararı):** rotanın sadece şimdiye kadar katedilen kısmı kontrol edilir. Bu kısım, mesafedeki aynı orandan gelir. Gemi ekvatoru şimdiden geçtiyse rozet hemen kazanılır, kazanılma tarihi bugündür.

### Milestone listesi (benim önerim, okurken çıkar ya da ekle)

- **Deniz zamanı:** 100 · 365 · 1,000 · 2,000 · 3,650 gün
- **Mesafe:**
  - 10,000 nm
  - 21,600 nm ("once around the world"; ekvator çevresi yaklaşık 21,600 nm)
  - 50,000 nm
  - 100,000 nm
- **Limanlar:** 10 · 25 · 50 farklı liman. **Ülkeler:** 10 · 25 farklı ülke.
- **Geçişler:** Equator, Date line, Suez, Panama, Gibraltar, Bosphorus, Cape of Good Hope
- **Kariyer** (kullanıcı: liste şimdilik bu, ileride milestone eklenecek; kod yeni milestone eklemeyi kolaylaştıracak şekilde, tek bir tanım listesiyle yazılır):
  - ilk kontrat
  - ilk terfi (aynı departmanda bir üst basamağa geçiş)
  - 5 farklı gemi
  - 3 farklı gemi tipi

Sayısal milestone'ların kazanılma tarihi, eşiğin geçildiği gündür. Bu tarih kontrat ve sefer tarihlerinden hesaplanır. Builder hesaplayamıyorsa tarihi boş bırakabilir.

### Bugün ve saat dilimi

Hesaplarda "bugün" UTC tarihidir. Frontend'deki cihaz tarihinden en fazla bir gün sapabilir, bu kabul edildi.

## API

`GET /profile/stats` (giriş gerekli) → `ProfileStats`

Alanlar (isimler builder'da netleşebilir):

- **Kimlik:**
  - `rank`, `full_name`
  - `first_sign_on` (tarih ya da null)
  - `years_at_sea` (ilk sign-on'dan bugüne geçen süre)
- **`totals`:** `sea_days`, `home_days`, `contracts`, `vessels`, `companies`, `voyages`, `distance_nm`, `ports`, `countries`
- **`by_vessel_type`:** `[{type, days}]`, çoktan aza. Tipi girilmemiş gemiler `type: null` olarak gelir, ekranda "Not set" yazar.
- **`by_rank`:** `[{rank, days}]`
- **`records`:**
  - `longest_contract`: `{vessel, days}`
  - `longest_voyage`: `{from, to, days, distance_nm}`
  - `most_visited_port`: `{name, country_code, calls}`; bir limana her varış bir "call" sayılır
- **`promotion`:** `{step, days, required: 900, next_rank}`. Basamak yoksa `null`.
- **`milestones`:** `[{key, category, title, earned, earned_on, progress, target}]`. Metinler İngilizce gelir, arayüz dili İngilizce.

Uç nokta kullanıcıya ait bütün kontratları ve seferleri okur, `user_id` token'dan alınır. Rota hatası (`RouteError`) olan sefer mesafe ve geçiş hesabına katılmaz, sayılara katılır.

## İş bölümü

- **Backend (kullanıcı yazar, ben adım adım yol gösteririm):**
  - schema: `app/schemas/profile.py`
  - hesap servisi: `app/services/profile_stats.py`, saf fonksiyonlar, test edilebilir
  - router: `app/routers/profile.py`
  - `main.py`'ye eklenir
- **Frontend (ben):**
  - `ProfilePage.jsx/.css`
  - kullanıcı menüsünde bağlantı
  - `/profile` rotası

## Builder'a bırakılanlar

- Geçiş kutularının tam koordinatları, şeridin renk tonları (mevcut yeşilin açık tonları), rozet ikonlarının seçimi (MUI outlined setinden).
- Milestone tarih hesabının ayrıntısı.
- Boş durum: hiç kontrat yoksa halka yerine "Add your first contract" kartı ve soluk rozet listesi gösterilir.
