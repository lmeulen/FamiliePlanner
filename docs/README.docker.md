# Docker Deployment Guide

FamiliePlanner kan eenvoudig gedeployed worden met Docker en Docker Compose.

## 🚀 Quick Start

### 1. Vereisten

- **Docker** (20.10+)
- **Docker Compose** (2.0+)

Installatie:
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (Windows/Mac)
- Linux: `sudo apt-get install docker.io docker-compose`

### 2. Environment Variabelen

Kopieer de voorbeeld environment file:

```bash
cp .env.example .env
```

Pas `.env` aan met je eigen waarden:

```bash
# Genereer een SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"

# Bewerk .env:
SECRET_KEY=<gegenereerde-key>
APP_USERNAME=admin
APP_PASSWORD=jouwwachtwoord
AUTH_REQUIRED=true
OPENWEATHER_API_KEY=<optioneel>
```

### 3. Start de Applicatie

```bash
docker-compose up -d
```

De applicatie is nu beschikbaar op: **http://localhost:8002**

---

## 📋 Docker Compose Commando's

### Start containers (achtergrond)
```bash
docker-compose up -d
```

### Stop containers
```bash
docker-compose down
```

### Herstart containers
```bash
docker-compose restart
```

### Bekijk logs
```bash
# Alle services
docker-compose logs -f

# Alleen app
docker-compose logs -f app

# Laatste 100 regels
docker-compose logs --tail=100 app
```

### Bekijk status
```bash
docker-compose ps
```

### Update naar nieuwste versie
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

---

## 🗂️ Data Persistentie

Data wordt opgeslagen in volumes en lokale directories:

```
├── data/                     # Database (SQLite)
│   └── familieplanner.db
└── app/static/uploads/       # Foto's
    ├── <uuid>.jpg/png
    └── thumbnails/
        └── <uuid>.jpg
```

**Backup maken:**
```bash
# Database + uploads
tar -czf backup-$(date +%Y%m%d).tar.gz data/ app/static/uploads/

# Alleen database
cp data/familieplanner.db backup-familieplanner-$(date +%Y%m%d).db
```

**Restore:**
```bash
# Stop de app eerst
docker-compose down

# Restore database
cp backup-familieplanner-20260307.db data/familieplanner.db

# Start de app
docker-compose up -d
```

---

## 📊 Monitoring (Optioneel)

FamiliePlanner heeft ingebouwde Prometheus metrics. Enable monitoring door de volgende regels in `docker-compose.yml` te uncommenten:

```yaml
services:
  # ... (app service)

  prometheus:
    # Uncomment hele prometheus service

  grafana:
    # Uncomment hele grafana service
```

Start met monitoring:
```bash
docker-compose up -d
```

**Toegang:**
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Metrics endpoint**: http://localhost:8002/metrics

**Grafana Dashboard importeren:**
1. Login op http://localhost:3000
2. Ga naar Dashboards → Import
3. Upload `docs/grafana-dashboard.json`
4. Selecteer Prometheus als data source

---

## 🔧 Advanced Configuration

### Custom Port

Wijzig de port in `docker-compose.yml`:

```yaml
services:
  app:
    ports:
      - "8080:8000"  # Host:Container
```

### Resource Limits

Voeg resource limits toe aan `docker-compose.yml`:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Productie Deployment

Voor productie gebruik:

1. **Gebruik een reverse proxy** (Nginx/Traefik)
2. **Enable HTTPS** met Let's Encrypt
3. **Set sterke wachtwoorden** in `.env`
4. **Backup automatiseren** met cron jobs
5. **Monitor logs** met logging aggregator

**Voorbeeld Nginx reverse proxy:**

```nginx
server {
    listen 80;
    server_name familieplanner.example.com;

    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🐛 Troubleshooting

### Container start niet

**Check logs:**
```bash
docker-compose logs app
```

**Veel voorkomende problemen:**
- Port 8002 al in gebruik: wijzig port in docker-compose.yml
- Permission errors: `chmod 777 data/ app/static/uploads/`
- Missing .env file: `cp .env.example .env`

### Database migratie errors

```bash
# Enter container
docker-compose exec app bash

# Run migrations manually
alembic upgrade head
```

### Reset database

```bash
docker-compose down
rm -rf data/familieplanner.db*
docker-compose up -d
```

### Container rebuild (clean)

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Check health status

```bash
docker-compose ps
# STATUS kolom toont (healthy) of (unhealthy)

# Manual health check
curl http://localhost:8002/health
```

---

## 🔒 Security Best Practices

### 1. Change Default Credentials

```bash
# .env
APP_USERNAME=your_username
APP_PASSWORD=strong_password_here
SECRET_KEY=<64-character-random-string>
```

### 2. Disable Auth for Internal Networks Only

Als je AUTH_REQUIRED=false gebruikt, zorg dat de app NIET publiek toegankelijk is:

```yaml
services:
  app:
    ports:
      - "127.0.0.1:8002:8000"  # Alleen localhost
```

### 3. Regular Updates

```bash
# Update base images
docker-compose pull
docker-compose up -d
```

### 4. Backup Automation

```bash
# Cron job (dagelijks om 3:00)
0 3 * * * cd /path/to/FamiliePlanner && tar -czf backup-$(date +\%Y\%m\%d).tar.gz data/ app/static/uploads/ && find . -name "backup-*.tar.gz" -mtime +30 -delete
```

---

## 📚 Zie Ook

- [Main README](../README.md) - Algemene documentatie
- [MONITORING.md](MONITORING.md) - Prometheus/Grafana setup
- [CACHING.md](CACHING.md) - Performance optimalisatie
- [ERROR_HANDLING.md](ERROR_HANDLING.md) - Error messages

---

## 🆘 Support

**Issues:** https://github.com/lmeulen/FamiliePlanner/issues

**Docker versie checken:**
```bash
docker --version
docker-compose --version
```

**Logs verzamelen voor debugging:**
```bash
docker-compose logs --tail=200 > debug.log
```
