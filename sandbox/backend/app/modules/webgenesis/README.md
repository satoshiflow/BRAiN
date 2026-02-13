# WebGenesis Module

**Version:** 1.0.0 (Sprint I MVP)
**Purpose:** AI-powered website generation and deployment system

---

## Overview

WebGenesis enables BRAiN to generate complete websites from specifications and deploy them safely via Docker Compose.

### Sprint I MVP Features

✅ **Static Website Generation**
- HTML + Tailwind CSS template
- Multi-page support
- Customizable theme (colors, typography)
- SEO optimization

✅ **Build System**
- Artifact hashing (SHA-256)
- Build validation
- Error tracking

✅ **Docker Compose Deployment**
- Nginx-based static file serving
- Auto port allocation (808x range)
- Health checks
- Container lifecycle management

✅ **Security & Governance**
- Trust tier enforcement (DMZ/LOCAL only for deploy)
- Path traversal protection
- Audit trail integration
- Fail-closed policy

---

## Storage Structure

All WebGenesis data is stored in `storage/webgenesis/`:

```
storage/webgenesis/
├── {site_id}/                    # Per-site directory
│   ├── spec.json                 # Original website spec
│   ├── manifest.json             # Site manifest (metadata, hashes, status)
│   ├── source/                   # Generated source code
│   │   ├── index.html
│   │   ├── about.html
│   │   ├── assets/
│   │   │   ├── styles.css
│   │   │   └── images/
│   │   └── ...
│   ├── build/                    # Build artifacts (for static: copy of source)
│   │   ├── index.html
│   │   ├── about.html
│   │   └── assets/
│   └── docker-compose.yml        # Deployment configuration
│
└── audit.jsonl                   # WebGenesis audit trail (hash-chained)
```

---

## Workflow

### 1. Submit Spec

```bash
POST /api/webgenesis/spec
{
  "spec": {
    "name": "my-site",
    "template": "static_html",
    "pages": [...],
    "seo": {...},
    "deploy": {...}
  }
}
```

**Response:**
```json
{
  "success": true,
  "site_id": "site_abc123",
  "spec_hash": "a1b2c3...",
  "message": "Spec received and stored"
}
```

**Audit Event:** `spec_received`

---

### 2. Generate Source

```bash
POST /api/webgenesis/{site_id}/generate
```

**What happens:**
- Creates `storage/webgenesis/{site_id}/source/`
- Generates HTML files from spec
- Creates CSS with theme colors
- Sets up page structure

**Response:**
```json
{
  "success": true,
  "site_id": "site_abc123",
  "source_path": "storage/webgenesis/site_abc123/source",
  "files_created": 5,
  "message": "Source generated successfully"
}
```

**Audit Events:** `generate_started`, `generate_finished`

---

### 3. Build Artifacts

```bash
POST /api/webgenesis/{site_id}/build
```

**What happens:**
- Copies source to `build/` directory
- Computes SHA-256 hash of all artifacts
- Updates manifest with artifact hash

**Response:**
```json
{
  "result": {
    "success": true,
    "site_id": "site_abc123",
    "artifact_path": "storage/webgenesis/site_abc123/build",
    "artifact_hash": "f6e5d4c3...",
    "timestamp": "2025-01-01T12:00:00Z"
  },
  "message": "Build completed successfully"
}
```

**Audit Events:** `build_started`, `build_finished`

---

### 4. Deploy

```bash
POST /api/webgenesis/{site_id}/deploy
```

**⚠️ Requires:** `TrustTier.DMZ` or `TrustTier.LOCAL` (EXTERNAL blocked)

**What happens:**
- Generates `docker-compose.yml` in site directory
- Creates Nginx container with static file volume mount
- Starts container with `docker-compose up -d`
- Performs health check
- Updates manifest with deployment info

**Response:**
```json
{
  "result": {
    "success": true,
    "site_id": "site_abc123",
    "url": "http://localhost:8080",
    "container_name": "webgenesis-site_abc123",
    "ports": [8080],
    "timestamp": "2025-01-01T12:05:00Z"
  },
  "message": "Deployment completed successfully"
}
```

**Audit Events:** `deploy_started`, `deploy_finished` (or `deploy_failed`)

---

### 5. Check Status

```bash
GET /api/webgenesis/{site_id}/status
```

**Response:**
```json
{
  "site_id": "site_abc123",
  "manifest": {
    "status": "deployed",
    "deployed_url": "http://localhost:8080",
    "deployed_ports": [8080],
    "created_at": "2025-01-01T12:00:00Z",
    "deployed_at": "2025-01-01T12:05:00Z"
  },
  "is_running": true,
  "health_status": "healthy"
}
```

---

## Example Website Spec

### JSON Format

```json
{
  "spec_version": "1.0.0",
  "name": "landing-page",
  "domain": "example.com",
  "locale_default": "en",
  "locales": ["en"],
  "template": "static_html",
  "pages": [
    {
      "slug": "home",
      "title": "Home - Example Site",
      "description": "Welcome to our amazing platform",
      "sections": [
        {
          "section_id": "hero",
          "type": "hero",
          "title": "Build Amazing Things",
          "content": "Our platform helps you create faster",
          "data": {
            "cta_text": "Get Started",
            "cta_link": "/signup"
          },
          "order": 0
        },
        {
          "section_id": "features",
          "type": "features",
          "title": "Features",
          "content": "",
          "data": {
            "items": [
              {"title": "Fast", "description": "Lightning quick"},
              {"title": "Secure", "description": "Bank-grade security"}
            ]
          },
          "order": 1
        }
      ],
      "layout": "default"
    },
    {
      "slug": "about",
      "title": "About Us",
      "description": "Learn more about our company",
      "sections": [
        {
          "section_id": "about_content",
          "type": "content",
          "title": "Our Story",
          "content": "We started in 2020...",
          "order": 0
        }
      ],
      "layout": "default"
    }
  ],
  "theme": {
    "colors": {
      "primary": "#3B82F6",
      "secondary": "#8B5CF6",
      "accent": "#10B981",
      "background": "#FFFFFF",
      "text": "#1F2937"
    },
    "typography": {
      "font_family": "Inter, system-ui, sans-serif",
      "heading_font": "Montserrat, sans-serif",
      "base_size": "16px"
    }
  },
  "seo": {
    "title": "Example Site - Build Amazing Things",
    "description": "Our platform helps you create faster and more efficiently",
    "keywords": ["platform", "tools", "innovation"],
    "og_image": "/assets/og-image.jpg",
    "twitter_card": "summary_large_image"
  },
  "deploy": {
    "target": "compose",
    "base_path": null,
    "ports": [8080],
    "healthcheck_path": "/",
    "domain": null,
    "ssl_enabled": false
  }
}
```

### YAML Format

```yaml
spec_version: "1.0.0"
name: landing-page
domain: example.com
locale_default: en
locales:
  - en
template: static_html

pages:
  - slug: home
    title: "Home - Example Site"
    description: "Welcome to our amazing platform"
    sections:
      - section_id: hero
        type: hero
        title: "Build Amazing Things"
        content: "Our platform helps you create faster"
        data:
          cta_text: "Get Started"
          cta_link: "/signup"
        order: 0

      - section_id: features
        type: features
        title: "Features"
        data:
          items:
            - title: "Fast"
              description: "Lightning quick"
            - title: "Secure"
              description: "Bank-grade security"
        order: 1

  - slug: about
    title: "About Us"
    description: "Learn more about our company"
    sections:
      - section_id: about_content
        type: content
        title: "Our Story"
        content: "We started in 2020..."
        order: 0

theme:
  colors:
    primary: "#3B82F6"
    secondary: "#8B5CF6"
    accent: "#10B981"
    background: "#FFFFFF"
    text: "#1F2937"
  typography:
    font_family: "Inter, system-ui, sans-serif"
    heading_font: "Montserrat, sans-serif"
    base_size: "16px"

seo:
  title: "Example Site - Build Amazing Things"
  description: "Our platform helps you create faster and more efficiently"
  keywords:
    - platform
    - tools
    - innovation
  og_image: "/assets/og-image.jpg"
  twitter_card: summary_large_image

deploy:
  target: compose
  ports:
    - 8080
  healthcheck_path: "/"
  ssl_enabled: false
```

---

## Security Model

### Trust Tier Enforcement

| Operation | LOCAL | DMZ | EXTERNAL |
|-----------|-------|-----|----------|
| Submit Spec | ✅ | ✅ | ✅ |
| Generate | ✅ | ✅ | ✅ |
| Build | ✅ | ✅ | ✅ |
| **Deploy** | ✅ | ✅ | ❌ **BLOCKED** |
| Status | ✅ | ✅ | ✅ |

**Rationale:** Deploy operations execute system commands (docker-compose) and must be restricted to authenticated sources.

### Path Traversal Protection

- All site IDs validated against `^[a-zA-Z0-9_-]+$`
- Base path allowlist: `storage/webgenesis/` only
- No `..` sequences allowed in any paths
- All paths canonicalized before use

### Subprocess Safety

- All `docker-compose` commands use `subprocess.run()` with arg arrays
- **NEVER** `shell=True`
- All user inputs sanitized
- Command injection vectors blocked

### Audit Trail

All critical operations logged to `storage/webgenesis/audit.jsonl`:
- `spec_received` - Spec submitted
- `generate_started` / `generate_finished` - Source generation
- `build_started` / `build_finished` - Build process
- `deploy_started` / `deploy_finished` - Deployment
- `deploy_failed` - Deployment errors
- `site_stopped` / `site_deleted` - Lifecycle changes

Audit events include:
- Site ID
- Status (success/failure)
- Trust tier
- User ID (if available)
- Timestamp
- Detailed metadata

---

## Manifest Schema

The `manifest.json` file tracks complete site lifecycle:

```json
{
  "site_id": "site_abc123",
  "name": "landing-page",
  "spec_version": "1.0.0",
  "spec_hash": "a1b2c3d4e5f6...",
  "artifact_hash": "f6e5d4c3b2a1...",
  "status": "deployed",
  "template": "static_html",

  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:05:00Z",
  "generated_at": "2025-01-01T12:01:00Z",
  "built_at": "2025-01-01T12:03:00Z",
  "deployed_at": "2025-01-01T12:05:00Z",

  "deployed_url": "http://localhost:8080",
  "deployed_ports": [8080],
  "docker_container_id": "abc123def456",
  "docker_image_tag": "nginx:alpine",

  "source_path": "storage/webgenesis/site_abc123/source",
  "build_path": "storage/webgenesis/site_abc123/build",
  "deploy_path": "storage/webgenesis/site_abc123",

  "last_error": null,
  "error_count": 0,
  "metadata": {}
}
```

---

## Cleanup & Rollback

### Stop Deployment

```bash
cd storage/webgenesis/{site_id}
docker-compose down
```

### Remove Site

```bash
# Stop containers
cd storage/webgenesis/{site_id}
docker-compose down -v

# Remove directory
rm -rf storage/webgenesis/{site_id}
```

### Rollback After Failed Deploy

1. Check `manifest.json` for `last_error`
2. Review audit trail for `deploy_failed` events
3. Fix spec or build issues
4. Retry deploy with `force=true`

---

## Future Enhancements

### Sprint II+
- Next.js template support
- Astro static template
- Multi-language generation
- Asset optimization
- CDN integration

### Deployment Targets
- Coolify integration
- Kubernetes deployment
- Cloud providers (Vercel, Netlify)

### Advanced Features
- A/B testing variants
- Analytics integration
- Form handlers
- API proxy configuration

---

## Module Info

| Property | Value |
|----------|-------|
| Module Name | `brain.webgenesis` |
| Version | 1.0.0 |
| Status | Production (Sprint I MVP) |
| Dependencies | Docker, Docker Compose |
| Storage | `storage/webgenesis/` |

---

## API Endpoints

| Method | Path | Description | Trust Required |
|--------|------|-------------|----------------|
| POST | `/api/webgenesis/spec` | Submit website spec | Any |
| POST | `/api/webgenesis/{site_id}/generate` | Generate source | Any |
| POST | `/api/webgenesis/{site_id}/build` | Build artifacts | Any |
| POST | `/api/webgenesis/{site_id}/deploy` | Deploy site | DMZ/LOCAL |
| GET | `/api/webgenesis/{site_id}/status` | Get site status | Any |

---

**Security Notice:** This module executes system commands for deployment. All operations are audited and trust tier enforcement is mandatory. Never disable security features.
