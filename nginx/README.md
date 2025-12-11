# Nginx Configuration Structure

Modular nginx configuration for BRAiN v2.0 with support for multiple environments.

## 📁 Structure

```
nginx/
├── nginx.conf              # Main configuration (includes all below)
├── conf.d/                 # Server blocks
│   ├── upstream.conf      # Upstream definitions for all environments
│   ├── dev.brain.conf     # dev.brain.falklabs.de (Port 8001, 3001, 3002)
│   ├── stage.brain.conf   # stage.brain.falklabs.de (Port 8002, 3003, 3004)
│   ├── prod.brain.conf    # brain.falklabs.de (Port 8000, 3000)
│   └── chat.conf          # chat.falklabs.de (Open WebUI)
└── snippets/               # Reusable configuration snippets
    ├── ssl-params.conf        # SSL/TLS settings
    ├── proxy-params.conf      # Proxy headers and timeouts
    ├── security-headers.conf  # Security headers (HSTS, X-Frame-Options, etc.)
    └── rate-limits.conf       # Rate limiting zones
```

## 🌐 Environments

| Environment | Domain | Backend Port | Frontend Port | Purpose |
|-------------|--------|--------------|---------------|---------|
| **Development** | dev.brain.falklabs.de | 8001 | 3001 | Active development, debugging |
| **Staging** | stage.brain.falklabs.de | 8002 | 3003 | Pre-production testing |
| **Production** | brain.falklabs.de | 8000 | 3000 | Live production system |
| **Chat** | chat.falklabs.de | 8080 | - | Open WebUI |

## 🚀 Deployment

### 1. Copy to Server

```bash
# From repository
scp -r nginx/ root@brain.falklabs.de:/etc/nginx-brain/

# Or via Git
ssh root@brain.falklabs.de
cd /srv/dev
git pull origin v2
```

### 2. Link Configuration

```bash
# Backup current config
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

# Create symlinks
ln -sf /srv/dev/nginx/nginx.conf /etc/nginx/nginx.conf
ln -sf /srv/dev/nginx/snippets /etc/nginx/snippets
ln -sf /srv/dev/nginx/conf.d /etc/nginx/conf.d

# Or copy files
cp /srv/dev/nginx/nginx.conf /etc/nginx/
cp -r /srv/dev/nginx/snippets /etc/nginx/
cp -r /srv/dev/nginx/conf.d /etc/nginx/
```

### 3. SSL Certificates

```bash
# Install certbot if not already installed
apt install certbot python3-certbot-nginx

# Get certificates for subdomains
certbot --nginx -d dev.brain.falklabs.de
certbot --nginx -d stage.brain.falklabs.de

# Existing certificates for production
# - brain.falklabs.de (already configured)
# - chat.falklabs.de (already configured)
```

### 4. Test & Reload

```bash
# Test configuration
nginx -t

# Reload nginx
systemctl reload nginx

# Check status
systemctl status nginx

# View logs
tail -f /var/log/nginx/dev-brain-access.log
tail -f /var/log/nginx/dev-brain-error.log
```

## 🔧 Configuration Details

### Upstream Definitions

Each environment has dedicated upstreams:
- **Dev**: localhost:8001 (backend), localhost:3001 (frontend)
- **Stage**: localhost:8002 (backend), localhost:3003 (frontend)
- **Prod**: Docker service names (brain-api, brain-control-deck)

### Rate Limiting

Different rate limits per environment:
- **API**: 10 req/s (burst 20)
- **Chat**: 30 req/s (burst 50)
- **Dev**: 50 req/s (burst 100) - generous for development

### SSL/TLS

- **Protocols**: TLS 1.2, TLS 1.3
- **Ciphers**: Modern, secure ciphers only
- **HSTS**: Enabled with 1-year max-age
- **OCSP Stapling**: Enabled

### Security Headers

- `Strict-Transport-Security`: Force HTTPS
- `X-Frame-Options`: Prevent clickjacking
- `X-Content-Type-Options`: Prevent MIME sniffing
- `X-XSS-Protection`: XSS filter
- `Referrer-Policy`: Control referrer information

## 🔄 Updating Configuration

### Add New Environment

1. Create new upstream in `conf.d/upstream.conf`
2. Create new server block in `conf.d/newenv.brain.conf`
3. Add domain to HTTP→HTTPS redirect in `nginx.conf`
4. Get SSL certificate with certbot
5. Test and reload

### Modify Existing Environment

1. Edit appropriate file in `conf.d/`
2. Test: `nginx -t`
3. Reload: `systemctl reload nginx`

### Disable Environment

```bash
# Rename file to disable (nginx ignores non-.conf files)
mv /etc/nginx/conf.d/stage.brain.conf /etc/nginx/conf.d/stage.brain.conf.disabled

# Reload
nginx -t && systemctl reload nginx
```

## 📊 Monitoring

### Check Access Logs

```bash
# Development
tail -f /var/log/nginx/dev-brain-access.log

# Staging
tail -f /var/log/nginx/stage-brain-access.log

# Production
tail -f /var/log/nginx/brain-access.log

# Chat
tail -f /var/log/nginx/chat-access.log
```

### Check Error Logs

```bash
tail -f /var/log/nginx/dev-brain-error.log
tail -f /var/log/nginx/stage-brain-error.log
tail -f /var/log/nginx/brain-error.log
tail -f /var/log/nginx/chat-error.log
```

### Test Endpoints

```bash
# Development
curl https://dev.brain.falklabs.de/api/health
curl https://dev.brain.falklabs.de/docs

# Staging
curl https://stage.brain.falklabs.de/api/health

# Production
curl https://brain.falklabs.de/api/health

# Chat
curl https://chat.falklabs.de
```

## 🐛 Troubleshooting

### Configuration Test Fails

```bash
nginx -t
# Read error message, usually points to line number
# Common issues:
# - Missing semicolon
# - Wrong path in include directive
# - SSL certificate not found
```

### SSL Certificate Issues

```bash
# Renew certificates
certbot renew

# Check certificate expiry
certbot certificates

# Test SSL
openssl s_client -connect dev.brain.falklabs.de:443
```

### Upstream Not Reachable

```bash
# Check if backend is running
docker ps | grep brain
netstat -tulpn | grep 8001

# Check upstream definition
cat /etc/nginx/conf.d/upstream.conf

# Check logs
tail -f /var/log/nginx/error.log
```

## 📚 Additional Resources

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Security Headers Reference](https://securityheaders.com/)
