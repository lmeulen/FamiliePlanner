# HTTPS Setup Guide

This guide explains how to deploy FamiliePlanner with HTTPS using Nginx reverse proxy and Let's Encrypt SSL certificates.

## Prerequisites

- A domain name pointing to your server (e.g., `familieplanner.yourdomain.com`)
- Docker and Docker Compose installed
- Ports 80 and 443 open on your firewall

## Quick Start

### 1. Configure Environment Variables

Create or update your `.env` file with the following variables:

```bash
# Domain for SSL certificate
DOMAIN=familieplanner.yourdomain.com

# Email for Let's Encrypt notifications
EMAIL=your-email@example.com

# Application credentials (required in production)
APP_USERNAME=your_username
APP_PASSWORD=your_secure_password

# Secret key for sessions (generate a random string)
SECRET_KEY=your-secret-key-here

# Optional: OpenWeather API key
OPENWEATHER_API_KEY=your-api-key
```

**Generate a secure secret key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Initial SSL Certificate

Before starting the services, obtain your SSL certificate:

```bash
# Start only the nginx service temporarily (without SSL)
docker-compose -f docker-compose.production.yml up -d nginx

# Obtain the certificate
docker-compose -f docker-compose.production.yml run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email ${EMAIL} \
  --agree-tos \
  --no-eff-email \
  -d ${DOMAIN}

# Stop nginx
docker-compose -f docker-compose.production.yml down
```

### 3. Start All Services

```bash
# Start all services with HTTPS enabled
docker-compose -f docker-compose.production.yml up -d

# Check logs
docker-compose -f docker-compose.production.yml logs -f
```

### 4. Verify HTTPS

Open your browser and navigate to:
- `https://familieplanner.yourdomain.com` - Should show FamiliePlanner with valid SSL
- `http://familieplanner.yourdomain.com` - Should redirect to HTTPS

### 5. Verify Digital Asset Links (for TWA)

```bash
# Check assetlinks.json is accessible
curl https://familieplanner.yourdomain.com/.well-known/assetlinks.json

# Should return JSON with Android app verification
```

## Certificate Renewal

Certbot automatically renews certificates every 12 hours via the `certbot` service. No manual intervention required.

### Manual Renewal (if needed)

```bash
docker-compose -f docker-compose.production.yml exec certbot certbot renew
docker-compose -f docker-compose.production.yml restart nginx
```

## Troubleshooting

### Port 80/443 Already in Use

Check what's using the ports:
```bash
sudo lsof -i :80
sudo lsof -i :443
```

Stop conflicting services (e.g., Apache, Nginx) or change the port mapping in `docker-compose.production.yml`.

### Certificate Not Found Error

Make sure you ran the initial certificate generation (step 2) before starting all services.

### DNS Not Propagated

Wait 5-10 minutes for DNS changes to propagate. Check DNS:
```bash
nslookup familieplanner.yourdomain.com
```

### Testing Without Domain (Local Development)

For local testing without a real domain, use `localhost` or your server IP:

1. Update `.env`:
   ```bash
   DOMAIN=localhost
   ```

2. Use self-signed certificate (not recommended for production):
   ```bash
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout certbot/conf/live/localhost/privkey.pem \
     -out certbot/conf/live/localhost/fullchain.pem \
     -subj "/CN=localhost"
   ```

3. Your browser will show a security warning (expected for self-signed certs)

## Development vs Production

### Development (HTTP only)
```bash
docker-compose up -d
# Access at: http://localhost:8002
```

### Production (HTTPS)
```bash
docker-compose -f docker-compose.production.yml up -d
# Access at: https://familieplanner.yourdomain.com
```

## Security Best Practices

1. **Enable HSTS** (after testing):
   - Uncomment the HSTS header in `nginx.conf`
   - This forces HTTPS for future visits

2. **Firewall Rules**:
   ```bash
   # Allow only HTTP/HTTPS
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **Regular Updates**:
   ```bash
   # Update Docker images
   docker-compose -f docker-compose.production.yml pull
   docker-compose -f docker-compose.production.yml up -d
   ```

4. **Monitor Logs**:
   ```bash
   # Watch for security issues
   docker-compose -f docker-compose.production.yml logs -f nginx
   ```

## Next Steps

Once HTTPS is working:

1. **Generate Android Keystore** (for TWA APK):
   ```bash
   ./scripts/generate-keystore.sh
   ```

2. **Update Digital Asset Links**:
   - Copy SHA-256 fingerprint from keystore generation
   - Update `app/static/.well-known/assetlinks.json`
   - Restart services

3. **Build TWA Android APK** - See `docs/APK_BUILD_GUIDE.md` (coming soon)

## Support

For issues or questions:
- Check logs: `docker-compose -f docker-compose.production.yml logs`
- Verify nginx config: `docker-compose -f docker-compose.production.yml exec nginx nginx -t`
- Restart services: `docker-compose -f docker-compose.production.yml restart`
