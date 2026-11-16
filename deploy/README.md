# Sefernâme'yi yayına alma

Tek bir sunucuda dört container çalışır. Gemideki gibi düşün: tek bir **kapı** (Caddy) var, makine dairesine (API) ve ambara (PostgreSQL) dışarıdan yol yok.

```
internet ──443──▶ web (Caddy) ──▶ api (FastAPI) ──▶ db (PostgreSQL)
                  │ HTTPS sertifikası, React dosyaları, /api yönlendirmesi
                  migrate: açılışta şemayı günceller, çıkar
                  backup:  her gece veritabanı dökümü
```

| Dosya | Ne işe yarar |
|---|---|
| `../Dockerfile` | API image'ı: Python 3.14 + Tesseract, root olmayan kullanıcı |
| `../../seafarer-panel-frontend/Dockerfile` | React'i derler, Caddy image'ına koyar |
| `docker-compose.yml` | Container'lar, ağ, volume'lar |
| `Caddyfile` | HTTPS, güvenlik başlıkları (CSP, HSTS), `/api` → API |
| `backup.sh` | Gece dökümü, son 14 gün |
| `.env.example` | Sunucuda doldurulacak gizli değerler |

## 1. Sunucu ve alan adı

1. **VPS:** Hetzner CX22 (Ubuntu 24.04, ~5 €/ay) yeter. Kurarken **SSH anahtarını** ekle, şifreyle giriş açma.
2. **Alan adı:** bir domain (veya alt alan adı) al, DNS'te **A kaydı** → sunucunun IP'si. Yayılması birkaç dakika–saat.
3. Sunucuya bağlan: `ssh root@<ip>`

## 2. Sunucuyu hazırla

```bash
# Güncelle, güvenlik duvarı: sadece SSH ve web
apt update && apt upgrade -y
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable

# Docker (resmi betik)
curl -fsSL https://get.docker.com | sh

# Root yerine kendi kullanıcın
adduser sefer && usermod -aG docker,sudo sefer
rsync --archive --chown=sefer:sefer ~/.ssh /home/sefer
```
Sonra `ssh sefer@<ip>` ile gir ve `/etc/ssh/sshd_config` içinde `PermitRootLogin no` + `PasswordAuthentication no` yap (`sudo systemctl restart ssh`).

## 3. Kodu getir

İki repo **yan yana** olmalı (compose ikisini de buradan bulur):
```bash
mkdir ~/sefername && cd ~/sefername
git clone <backend-repo-adresi> seafarer-panel-backend
git clone <frontend-repo-adresi> seafarer-panel-frontend
```

## 4. Gizli değerler

```bash
cd ~/sefername/seafarer-panel-backend/deploy
cp .env.example .env
openssl rand -hex 32                     # üç kez çalıştır: POSTGRES_PASSWORD, SECRET_KEY, BACKUP_PASSPHRASE
openssl rand -base64 32 | tr '+/' '-_'   # DATA_ENCRYPTION_KEY
nano .env              # DOMAIN, ACME_EMAIL ve dört değeri yaz
chmod 600 .env
```
`.env` git'e **girmez** (`.gitignore`). Laptop'taki anahtarları burada kullanma; sunucunun kendi anahtarları olsun.

**`DATA_ENCRYPTION_KEY` ve `BACKUP_PASSPHRASE`'i şimdi bir şifre yöneticisine kaydet.** Yüklenen dosyalar ve belge numaraları bu anahtarla şifreli duruyor: anahtar kaybolursa pasaport taramaları ve numaraları da kaybolur, kimse (sen dahil) açamaz. Yedeklerin şifresi de `BACKUP_PASSPHRASE`; bu ikisini yedeklerin yanına koyma.

Anahtar değiştirmek gerekirse (sızdığından şüphe varsa): eskisini `DATA_ENCRYPTION_OLD_KEYS='["eski-anahtar"]'` olarak ekle, yenisini `DATA_ENCRYPTION_KEY`'e yaz, yeniden başlat, sonra `docker compose run --rm api python -m app.scripts.encrypt_uploads --apply` ve `docker compose run --rm api python -m app.scripts.seal_fields --apply` ile dosyaları ve alanları yeni anahtara taşı; bitince eski anahtarı sil.

## 5. Başlat

```bash
docker compose up -d --build        # ilk derleme birkaç dakika sürer
docker compose ps                   # migrate "exited (0)", diğerleri "running" olmalı
docker compose logs -f web          # Caddy sertifikayı alınca "certificate obtained" yazar
```
Limanları bir kez yükle (searoute verisinden ~3900 liman):
```bash
docker compose run --rm api python -m app.scripts.import_ports
```
Tarayıcıda `https://<domain>` → kayıt ol → kullan.

## 6. Yedek ve geri dönüş

`backup` container'ı her gece iki dosya yazar, son 14 günü tutar; ikisi de `BACKUP_PASSPHRASE` ile şifreli:
- `deploy/backups/sefername-YYYY-MM-DD.dump.enc`: veritabanı
- `deploy/backups/uploads-YYYY-MM-DD.tar.enc`: yüklenen dosyalar (dosyalar zaten tek tek `DATA_ENCRYPTION_KEY` ile şifreli; arşiv ikinci kilit)

**Bu yalnız yanlışlıklara karşı korur; sunucu giderse yedek de gider.** Klasörü sunucu dışına da kopyala (ör. `rclone` ile Backblaze B2 / Cloudflare R2, ayda birkaç kuruş). Şifreli oldukları için başka bir yerde durmaları güvenli; parolayı yanlarına koyma.

Geri yükleme (bunu **bir kez dene**, denenmemiş yedek yedek değildir). Önce dosyanın **boyutuna ve tarihine** bak: veritabanı boşken alınmış bir döküm her şeyi boşaltır.
```bash
ls -lh backups/                                  # hangi döküm, ne zaman, ne büyüklükte?
docker compose stop api                          # geri yüklerken kimse yazmasın
# Veritabanı: önce şifreyi çöz, sonra geri yükle
docker compose exec backup sh -c 'openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:BACKUP_PASSPHRASE -in /backups/sefername-2026-11-10.dump.enc | pg_restore --clean --if-exists -d sefername'
# Dosyalar (gerekirse): uploads volume'una geri aç
docker compose run --rm --no-deps -v sefername_uploads:/restore --entrypoint sh backup -c 'command -v openssl >/dev/null || apk add --no-cache openssl >/dev/null; openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:BACKUP_PASSPHRASE -in /backups/uploads-2026-11-10.tar.enc | tar -xf - -C /restore'
docker compose start api
```
Komutlar `backup` container'ının içinde çalışır (parola ve bağlantı bilgileri orada tanımlı), PowerShell'den de aynen yazılabilir. Elle şifreli döküm almak için: `docker compose exec backup sh -c 'pg_dump --format=custom | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:BACKUP_PASSPHRASE -out /backups/elle.dump.enc'`.

> Bu yedek düzeni Docker'da henüz hiç çalıştırılmadı (bu bilgisayarda Docker yok). İlk kurulumda bir gece bekleyip iki `.enc` dosyasının oluştuğunu ve yukarıdaki geri yüklemenin çalıştığını mutlaka dene.

## 7. Güncelleme

```bash
cd ~/sefername/seafarer-panel-frontend && git pull
cd ~/sefername/seafarer-panel-backend && git pull
cd deploy && docker compose up -d --build   # migrate yeni şemayı kendisi uygular
```
Büyük bir migration'dan önce elle bir döküm al (komut 6. bölümde, "Elle şifreli döküm").

## Güvenlik notları

- Dışarı açık tek port Caddy'nin (80/443). API ve veritabanının portu yok.
- Production'da Swagger kapalı (`DOCS_ENABLED=false`), cookie'ler `Secure` (`COOKIE_SECURE=true`).
- Login deneme sınırı gerçek istemci adresini Caddy'nin `X-Forwarded-For` başlığından okur (`--proxy-headers`).
- `index.html`'deki tema betiği değişirse `Caddyfile`'daki CSP hash'i de değişmeli, yoksa betik engellenir. Yeni hash:
  ```bash
  node -e "const h=require('fs').readFileSync('index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];console.log('sha256-'+require('crypto').createHash('sha256').update(h).digest('base64'))"
  ```
- Login sayacı bellekte: tek API container'ı için doğru. İkinci bir API container'ı eklenirse Redis'e taşınmalı.
