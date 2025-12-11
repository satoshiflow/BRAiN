# BRAiN v2 Nginx Configuration

This directory contains nginx configurations for both Docker and host deployments.

## Files

- **nginx.docker.conf** - Nginx config for Docker Compose (internal routing)
- **nginx.conf** - Main nginx config for host system
- **snippets/** - Reusable configuration snippets
  - `proxy-params.conf` - Standard proxy headers and timeouts
  - `rate-limits.conf` - Rate limiting zones
- **conf.d/** - Server-specific configurations
  - `upstream.conf` - Upstream definitions for all environments
  - `dev.brain.conf` - Development environment (dev.brain.falklabs.de)
  - `stage.brain.conf` - Staging environment (stage.brain.falklabs.de)
  - `brain.conf` - Production environment (brain.falklabs.de)

## Deployment

The `brain-v2-setup.sh` script copies these files to the appropriate locations:

```bash
# Host system nginx config
cp /srv/dev/nginx/nginx.conf /etc/nginx/nginx.conf

# Snippets and server configs
cp -r /srv/dev/nginx/snippets /etc/nginx/
cp -r /srv/dev/nginx/conf.d /etc/nginx/
```

## Port Mapping

| Environment | Backend Port | Frontend Port | Domain |
|-------------|--------------|---------------|---------|
| Development | 8001 | 3001 | dev.brain.falklabs.de |
| Staging | 8002 | 3003 | stage.brain.falklabs.de |
| Production | 8000 | 3000 | brain.falklabs.de |

## SSL Certificates

SSL certificates are managed by Let's Encrypt via certbot:

```bash
# Development
certbot --nginx -d dev.brain.falklabs.de

# Staging
certbot --nginx -d stage.brain.falklabs.de

# Production
certbot --nginx -d brain.falklabs.de
```
