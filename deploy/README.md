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
openssl rand -hex 32   # iki kez çalıştır: biri POSTGRES_PASSWORD, biri SECRET_KEY
nano .env              # DOMAIN, ACME_EMAIL ve iki değeri yaz
chmod 600 .env
```
`.env` git'e **girmez** (`.gitignore`). Laptop'taki `SECRET_KEY`'i burada kullanma; sunucunun kendi anahtarı olsun.

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

`backup` container'ı her gece `deploy/backups/sefername-YYYY-MM-DD.dump` yazar, son 14'ü tutar. **Bu yalnız yanlışlıklara karşı korur; sunucu giderse yedek de gider.** Klasörü sunucu dışına da kopyala (ör. `rclone` ile Backblaze B2 / Cloudflare R2, ayda birkaç kuruş).

Geri yükleme (bunu **bir kez dene**, denenmemiş yedek yedek değildir):
```bash
docker compose exec -T db pg_restore --clean --if-exists -U sefername -d sefername < backups/sefername-2026-11-10.dump
```
Yüklenen dosyalar (`uploads` volume) dökümde yok; onları da yedekle:
```bash
docker run --rm -v sefername_uploads:/u -v "$PWD/backups":/b alpine tar czf /b/uploads-$(date +%F).tgz -C /u .
```

## 7. Güncelleme

```bash
cd ~/sefername/seafarer-panel-frontend && git pull
cd ~/sefername/seafarer-panel-backend && git pull
cd deploy && docker compose up -d --build   # migrate yeni şemayı kendisi uygular
```
Büyük bir migration'dan önce elle bir döküm al: `docker compose exec backup pg_dump -Fc -f /backups/elle-$(date +%F).dump`.

## Güvenlik notları

- Dışarı açık tek port Caddy'nin (80/443). API ve veritabanının portu yok.
- Production'da Swagger kapalı (`DOCS_ENABLED=false`), cookie'ler `Secure` (`COOKIE_SECURE=true`).
- Login deneme sınırı gerçek istemci adresini Caddy'nin `X-Forwarded-For` başlığından okur (`--proxy-headers`).
- `index.html`'deki tema betiği değişirse `Caddyfile`'daki CSP hash'i de değişmeli, yoksa betik engellenir. Yeni hash:
  ```bash
  node -e "const h=require('fs').readFileSync('index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];console.log('sha256-'+require('crypto').createHash('sha256').update(h).digest('base64'))"
  ```
- Login sayacı bellekte: tek API container'ı için doğru. İkinci bir API container'ı eklenirse Redis'e taşınmalı.
