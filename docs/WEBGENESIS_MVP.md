# WebGenesis MVP Documentation

**Version:** 1.0.0 (Sprint I)
**Module:** `backend.app.modules.webgenesis`
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [API Reference](#api-reference)
5. [Security Model](#security-model)
6. [Workflow Guide](#workflow-guide)
7. [Templates & Customization](#templates--customization)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)
10. [Examples](#examples)

---

## Overview

**WebGenesis** is BRAiN's website generation and deployment system. It transforms YAML/JSON specifications into fully functional static websites deployed via Docker Compose.

### Key Features

✅ **Spec-Based Generation** - Declarative YAML/JSON website specifications
✅ **Static HTML + Tailwind** - Modern, responsive templates
✅ **Artifact Hashing** - SHA-256 verification for build integrity
✅ **Docker Compose Deployment** - Isolated Nginx containers per site
✅ **Trust Tier Enforcement** - DMZ/LOCAL only deployment (fail-closed)
✅ **Audit Trail** - Hash-chained JSONL logging
✅ **Path Safety** - Regex validation + path traversal protection
✅ **Subprocess Safety** - No shell injection vulnerabilities

### Sprint I Scope

**Template Support:**
- Static HTML with Tailwind CSS CDN
- Responsive layouts (mobile-first)
- SEO optimizations (meta tags, Open Graph, Twitter Card)

**Deployment Targets:**
- Docker Compose with Nginx Alpine
- Auto port allocation (8080-8180)
- Health check verification

**Security:**
- Trust tier enforcement (EXTERNAL blocked for deploy)
- Path traversal prevention
- Command injection prevention
- Fail-closed policy

---

## Quick Start

### 1. Submit Website Specification

```bash
curl -X POST http://localhost:8000/api/webgenesis/spec \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {
      "spec_version": "1.0.0",
      "name": "my-awesome-site",
      "domain": "example.com",
      "locale_default": "en",
      "locales": ["en"],
      "template": "static_html",
      "pages": [{
        "slug": "home",
        "title": "Welcome",
        "description": "My awesome website",
        "sections": [{
          "section_id": "hero",
          "type": "hero",
          "title": "Hello World",
          "content": "Welcome to my site",
          "data": {},
          "order": 0
        }],
        "layout": "default"
      }],
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
          "base_size": "16px"
        }
      },
      "seo": {
        "title": "My Awesome Site",
        "description": "A great website built with WebGenesis",
        "keywords": ["awesome", "website"],
        "twitter_card": "summary"
      },
      "deploy": {
        "target": "compose",
        "healthcheck_path": "/",
        "ssl_enabled": false
      }
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "site_id": "my-awesome-site_1703001234",
  "spec_hash": "a3f5c8e9...",
  "message": "Website specification stored successfully"
}
```

### 2. Generate Source Code

```bash
curl -X POST http://localhost:8000/api/webgenesis/my-awesome-site_1703001234/generate
```

**Response:**
```json
{
  "success": true,
  "site_id": "my-awesome-site_1703001234",
  "source_path": "/storage/webgenesis/my-awesome-site_1703001234/source",
  "files_created": 3,
  "errors": []
}
```

### 3. Build Artifacts

```bash
curl -X POST http://localhost:8000/api/webgenesis/my-awesome-site_1703001234/build
```

**Response:**
```json
{
  "result": {
    "success": true,
    "site_id": "my-awesome-site_1703001234",
    "artifact_hash": "b8d4f7a2...",
    "errors": []
  }
}
```

### 4. Deploy Website

```bash
curl -X POST http://localhost:8000/api/webgenesis/my-awesome-site_1703001234/deploy
```

**Response:**
```json
{
  "result": {
    "success": true,
    "site_id": "my-awesome-site_1703001234",
    "deployment_url": "http://localhost:8080",
    "container_id": "abc123...",
    "errors": []
  }
}
```

### 5. Check Status

```bash
curl http://localhost:8000/api/webgenesis/my-awesome-site_1703001234/status
```

**Response:**
```json
{
  "site_id": "my-awesome-site_1703001234",
  "manifest": {
    "site_id": "my-awesome-site_1703001234",
    "name": "my-awesome-site",
    "spec_hash": "a3f5c8e9...",
    "status": "deployed",
    "created_at": 1703001234.56,
    "updated_at": 1703001300.78,
    "source_path": "/storage/webgenesis/my-awesome-site_1703001234/source",
    "build_path": "/storage/webgenesis/my-awesome-site_1703001234/build",
    "artifact_hash": "b8d4f7a2...",
    "deployment_url": "http://localhost:8080",
    "container_id": "abc123..."
  }
}
```

---

## Architecture

### Directory Structure

```
storage/webgenesis/
└── {site_id}/
    ├── spec.json                 # Original specification
    ├── manifest.json             # Site metadata & status
    ├── source/                   # Generated source code
    │   ├── index.html
    │   ├── about.html
    │   └── ...
    ├── build/                    # Build artifacts (copy of source)
    │   ├── index.html
    │   ├── about.html
    │   └── artifact_hash.txt
    └── docker-compose.yml        # Deployment configuration
```

### Site ID Format

```
{name}_{timestamp}
```

**Example:** `my-site_1703001234`

**Validation:** `^[a-zA-Z0-9_-]+$` (alphanumeric, hyphens, underscores only)

### Status Lifecycle

```
pending → generated → built → deployed
                             → failed
```

**Status Transitions:**
- `pending` - Spec submitted, no source generated yet
- `generated` - Source code created, ready to build
- `built` - Artifacts built, ready to deploy
- `deployed` - Running in Docker container
- `failed` - Error occurred (check manifest for details)

### Module Components

```
backend/app/modules/webgenesis/
├── __init__.py           # Module exports
├── schemas.py            # Pydantic models
├── service.py            # Business logic
├── router.py             # API endpoints
├── templates/
│   ├── base.html         # Main HTML template
│   └── sections.html     # Section templates
└── README.md             # Module documentation
```

---

## API Reference

### Base URL

```
http://localhost:8000/api/webgenesis
```

### Endpoints

#### 1. Submit Specification

**POST** `/spec`

Submit a new website specification.

**Trust Tier:** Any (LOCAL, DMZ, EXTERNAL)

**Request Body:**
```json
{
  "spec": {
    "spec_version": "1.0.0",
    "name": "site-name",
    "domain": "example.com",
    "locale_default": "en",
    "locales": ["en", "de"],
    "template": "static_html",
    "pages": [...],
    "theme": {...},
    "seo": {...},
    "deploy": {...}
  }
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "site_id": "site-name_1703001234",
  "spec_hash": "sha256_hash",
  "message": "Website specification stored successfully"
}
```

**Errors:**
- `400 Bad Request` - Invalid specification
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Storage failure

---

#### 2. Generate Source

**POST** `/{site_id}/generate`

Generate source code from specification.

**Trust Tier:** Any

**Query Parameters:**
- `force` (optional, default: `false`) - Regenerate even if source exists

**Request Body (optional):**
```json
{
  "force": true
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "site_id": "site-name_1703001234",
  "source_path": "/storage/webgenesis/site-name_1703001234/source",
  "files_created": 5,
  "errors": []
}
```

**Errors:**
- `400 Bad Request` - Source already exists (without force flag)
- `404 Not Found` - Site ID not found
- `500 Internal Server Error` - Generation failure

---

#### 3. Build Artifacts

**POST** `/{site_id}/build`

Build deployment artifacts from source.

**Trust Tier:** Any

**Query Parameters:**
- `force` (optional, default: `false`) - Rebuild even if artifacts exist

**Request Body (optional):**
```json
{
  "force": true
}
```

**Response:** `200 OK`
```json
{
  "result": {
    "success": true,
    "site_id": "site-name_1703001234",
    "artifact_hash": "sha256_hash",
    "errors": []
  }
}
```

**Errors:**
- `400 Bad Request` - Source not generated or build already exists
- `404 Not Found` - Site ID not found
- `500 Internal Server Error` - Build failure

---

#### 4. Deploy Website

**POST** `/{site_id}/deploy`

Deploy website via Docker Compose.

**Trust Tier:** DMZ or LOCAL only (EXTERNAL blocked with HTTP 403)

**Query Parameters:**
- `force` (optional, default: `false`) - Redeploy even if already deployed

**Request Body (optional):**
```json
{
  "force": true
}
```

**Response:** `200 OK`
```json
{
  "result": {
    "success": true,
    "site_id": "site-name_1703001234",
    "deployment_url": "http://localhost:8080",
    "container_id": "abc123...",
    "errors": []
  }
}
```

**Errors:**
- `400 Bad Request` - Build not ready or already deployed
- `403 Forbidden` - EXTERNAL trust tier attempted deployment
- `404 Not Found` - Site ID not found
- `500 Internal Server Error` - Deployment failure

---

#### 5. Get Status

**GET** `/{site_id}/status`

Retrieve site status and manifest.

**Trust Tier:** Any

**Response:** `200 OK`
```json
{
  "site_id": "site-name_1703001234",
  "manifest": {
    "site_id": "site-name_1703001234",
    "name": "site-name",
    "spec_hash": "sha256_hash",
    "status": "deployed",
    "created_at": 1703001234.56,
    "updated_at": 1703001300.78,
    "source_path": "/storage/webgenesis/site-name_1703001234/source",
    "build_path": "/storage/webgenesis/site-name_1703001234/build",
    "artifact_hash": "sha256_hash",
    "deployment_url": "http://localhost:8080",
    "container_id": "abc123..."
  }
}
```

**Errors:**
- `404 Not Found` - Site ID not found

---

## Security Model

### Trust Tier Enforcement

WebGenesis implements **fail-closed security** for deployment operations.

**Trust Tiers:**
- **LOCAL** - Requests from localhost (127.0.0.1, ::1) - ✅ ALLOWED
- **DMZ** - Authenticated gateway requests (x-dmz-gateway-id header) - ✅ ALLOWED
- **EXTERNAL** - All other requests - ❌ BLOCKED (HTTP 403)

**Enforcement:**
```python
async def validate_trust_tier_for_deploy(request: Request) -> AXERequestContext:
    validator = get_axe_trust_validator()
    context = await validator.validate_request(...)

    if context.trust_tier == TrustTier.EXTERNAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "deployment_forbidden",
                "message": "Deployment operations are restricted to DMZ and LOCAL trust tiers",
                "trust_tier": "external"
            }
        )

    return context
```

**Endpoint Protection:**

| Endpoint | LOCAL | DMZ | EXTERNAL |
|----------|-------|-----|----------|
| POST /spec | ✅ | ✅ | ✅ |
| POST /{site_id}/generate | ✅ | ✅ | ✅ |
| POST /{site_id}/build | ✅ | ✅ | ✅ |
| **POST /{site_id}/deploy** | ✅ | ✅ | ❌ |
| GET /{site_id}/status | ✅ | ✅ | ✅ |

### Path Traversal Prevention

**Site ID Validation:**
```python
SITE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

def validate_site_id(site_id: str) -> bool:
    return bool(SITE_ID_PATTERN.match(site_id))
```

**Safe Path Joining:**
```python
def safe_path_join(base: Path, *parts: str) -> Path:
    result = (base / Path(*parts)).resolve()
    try:
        result.relative_to(base.resolve())
    except ValueError:
        raise ValueError(f"Path traversal detected: {result} is outside {base}")
    return result
```

**Examples:**
```python
# ✅ ALLOWED
safe_path_join(base, "my-site_1703001234", "source")
# → /storage/webgenesis/my-site_1703001234/source

# ❌ BLOCKED
safe_path_join(base, "../../../etc/passwd")
# → ValueError: Path traversal detected
```

### Command Injection Prevention

All subprocess calls use **argument arrays** (never `shell=True`):

```python
# ✅ SAFE
subprocess.run(
    ["docker-compose", "up", "-d"],
    cwd=str(site_dir),
    capture_output=True,
    timeout=60,
    check=True
)

# ❌ UNSAFE (never used in WebGenesis)
subprocess.run(
    f"docker-compose up -d",  # Shell injection risk!
    shell=True  # NEVER DO THIS
)
```

### Artifact Integrity

**SHA-256 Hashing:**
- Spec hash: `hashlib.sha256(spec_json.encode()).hexdigest()`
- Artifact hash: Recursive directory hashing with sorted file list

**Verification:**
```python
def compute_directory_hash(directory: Path) -> str:
    sha256 = hashlib.sha256()

    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            sha256.update(file_path.read_bytes())

    return sha256.hexdigest()
```

### Audit Trail

All operations are logged to the BRAiN audit system:

```python
await audit_manager.log(
    event_type="webgenesis.spec.submit",
    data={
        "site_id": site_id,
        "spec_hash": spec_hash,
        "name": spec.name
    }
)
```

Audit events are stored in hash-chained JSONL format for tamper detection.

---

## Workflow Guide

### Complete Workflow Example

**1. Prepare Specification**

Create `website-spec.json`:
```json
{
  "spec": {
    "spec_version": "1.0.0",
    "name": "portfolio-site",
    "domain": "portfolio.example.com",
    "locale_default": "en",
    "locales": ["en"],
    "template": "static_html",
    "pages": [
      {
        "slug": "home",
        "title": "Portfolio - John Doe",
        "description": "Welcome to my portfolio",
        "sections": [
          {
            "section_id": "hero",
            "type": "hero",
            "title": "Hi, I'm John Doe",
            "content": "Full-stack developer specializing in AI systems",
            "data": {},
            "order": 0
          },
          {
            "section_id": "projects",
            "type": "features",
            "title": "My Projects",
            "content": "",
            "data": {
              "items": [
                {
                  "title": "Project Alpha",
                  "description": "AI-powered chatbot",
                  "icon": "💬"
                },
                {
                  "title": "Project Beta",
                  "description": "Real-time analytics dashboard",
                  "icon": "📊"
                }
              ]
            },
            "order": 1
          }
        ],
        "layout": "default"
      },
      {
        "slug": "contact",
        "title": "Contact Me",
        "description": "Get in touch",
        "sections": [
          {
            "section_id": "contact_form",
            "type": "contact",
            "title": "Let's Connect",
            "content": "Email: john@example.com",
            "data": {},
            "order": 0
          }
        ],
        "layout": "default"
      }
    ],
    "theme": {
      "colors": {
        "primary": "#2563EB",
        "secondary": "#7C3AED",
        "accent": "#059669",
        "background": "#FFFFFF",
        "text": "#111827"
      },
      "typography": {
        "font_family": "Inter, system-ui, sans-serif",
        "base_size": "16px",
        "heading_font": "Poppins, sans-serif"
      }
    },
    "seo": {
      "title": "John Doe - Full-Stack Developer",
      "description": "Portfolio showcasing AI and web development projects",
      "keywords": ["portfolio", "developer", "AI", "web development"],
      "og_image": "https://example.com/og-image.jpg",
      "twitter_card": "summary_large_image",
      "twitter_handle": "@johndoe"
    },
    "deploy": {
      "target": "compose",
      "healthcheck_path": "/",
      "ssl_enabled": false,
      "custom_nginx_config": null
    }
  }
}
```

**2. Submit Specification**
```bash
SITE_ID=$(curl -X POST http://localhost:8000/api/webgenesis/spec \
  -H "Content-Type: application/json" \
  -d @website-spec.json | jq -r '.site_id')

echo "Site ID: $SITE_ID"
# Output: Site ID: portfolio-site_1703001234
```

**3. Generate Source**
```bash
curl -X POST http://localhost:8000/api/webgenesis/$SITE_ID/generate
```

**4. Build Artifacts**
```bash
curl -X POST http://localhost:8000/api/webgenesis/$SITE_ID/build
```

**5. Deploy**
```bash
DEPLOY_RESULT=$(curl -X POST http://localhost:8000/api/webgenesis/$SITE_ID/deploy)
DEPLOY_URL=$(echo $DEPLOY_RESULT | jq -r '.result.deployment_url')

echo "Website deployed at: $DEPLOY_URL"
# Output: Website deployed at: http://localhost:8080
```

**6. Verify Deployment**
```bash
curl $DEPLOY_URL
# Should return the generated HTML
```

**7. Check Status**
```bash
curl http://localhost:8000/api/webgenesis/$SITE_ID/status | jq
```

### Regeneration Workflow

**Force Regenerate Source:**
```bash
curl -X POST "http://localhost:8000/api/webgenesis/$SITE_ID/generate?force=true"
```

**Force Rebuild:**
```bash
curl -X POST "http://localhost:8000/api/webgenesis/$SITE_ID/build?force=true"
```

**Force Redeploy:**
```bash
curl -X POST "http://localhost:8000/api/webgenesis/$SITE_ID/deploy?force=true"
```

### Manual Deployment Cleanup

**Stop Container:**
```bash
cd storage/webgenesis/$SITE_ID
docker-compose down
```

**Remove Volumes:**
```bash
docker-compose down -v
```

---

## Templates & Customization

### Available Section Types

**1. Hero Section**
```json
{
  "section_id": "hero",
  "type": "hero",
  "title": "Main Headline",
  "content": "Subheadline text",
  "data": {},
  "order": 0
}
```

**2. Features Section**
```json
{
  "section_id": "features",
  "type": "features",
  "title": "Our Features",
  "content": "",
  "data": {
    "items": [
      {
        "title": "Feature 1",
        "description": "Description of feature 1",
        "icon": "🚀"
      },
      {
        "title": "Feature 2",
        "description": "Description of feature 2",
        "icon": "⚡"
      }
    ]
  },
  "order": 1
}
```

**3. Content Section**
```json
{
  "section_id": "about",
  "type": "content",
  "title": "About Us",
  "content": "<p>Rich text content here</p>",
  "data": {},
  "order": 2
}
```

**4. CTA (Call to Action) Section**
```json
{
  "section_id": "cta",
  "type": "cta",
  "title": "Ready to Get Started?",
  "content": "Join thousands of satisfied customers",
  "data": {
    "buttons": [
      {
        "text": "Sign Up Free",
        "url": "/signup",
        "primary": true
      },
      {
        "text": "Learn More",
        "url": "/about",
        "primary": false
      }
    ]
  },
  "order": 3
}
```

**5. Contact Section**
```json
{
  "section_id": "contact",
  "type": "contact",
  "title": "Get in Touch",
  "content": "Email: contact@example.com<br>Phone: +1 234 567 890",
  "data": {},
  "order": 4
}
```

### Theme Customization

**Colors:**
```json
{
  "theme": {
    "colors": {
      "primary": "#3B82F6",      // Main brand color
      "secondary": "#8B5CF6",    // Secondary accent
      "accent": "#10B981",       // Highlights
      "background": "#FFFFFF",   // Page background
      "text": "#1F2937"          // Body text
    }
  }
}
```

**Typography:**
```json
{
  "theme": {
    "typography": {
      "font_family": "Inter, system-ui, sans-serif",
      "base_size": "16px",
      "heading_font": "Poppins, sans-serif"
    }
  }
}
```

### SEO Configuration

**Full SEO Example:**
```json
{
  "seo": {
    "title": "My Awesome Website",
    "description": "The best website ever created",
    "keywords": ["awesome", "website", "amazing"],
    "og_image": "https://example.com/og-image.jpg",
    "twitter_card": "summary_large_image",
    "twitter_handle": "@mywebsite"
  }
}
```

**Twitter Card Types:**
- `summary` - Small card with image
- `summary_large_image` - Large card with prominent image
- `app` - Mobile app card
- `player` - Video/audio player card

---

## Deployment

### Docker Compose Configuration

**Generated `docker-compose.yml`:**
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: webgenesis-{site_id}
    ports:
      - "{port}:80"
    volumes:
      - ./build:/usr/share/nginx/html:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
```

### Port Allocation

WebGenesis auto-discovers available ports in the range **8080-8180**.

**Port Discovery Algorithm:**
```python
def find_available_port(start: int = 8080, end: int = 8180) -> Optional[int]:
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue
    return None
```

### Health Checks

**Default Health Check:**
- Endpoint: `/` (configurable via `deploy.healthcheck_path`)
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3
- Start period: 5 seconds

**Custom Health Check Path:**
```json
{
  "deploy": {
    "healthcheck_path": "/health"
  }
}
```

### SSL/TLS (Future)

Sprint I does not include SSL/TLS support. Future sprints will add:
- Let's Encrypt integration
- Custom certificate uploads
- Automatic HTTPS redirects

---

## Troubleshooting

### Common Issues

#### Issue 1: "Site ID not found"

**Symptoms:**
```json
{
  "detail": "Site not found: my-site_1703001234"
}
```

**Causes:**
- Site ID doesn't exist
- Typo in site ID

**Solutions:**
1. Verify site ID from submit response
2. Check `/api/webgenesis/{site_id}/status`
3. List sites in `storage/webgenesis/` directory

---

#### Issue 2: "Source already exists"

**Symptoms:**
```json
{
  "detail": "Source already exists for site my-site_1703001234. Use force=true to regenerate."
}
```

**Causes:**
- Attempting to generate source twice without force flag

**Solutions:**
1. Use force flag: `POST /generate?force=true`
2. Or manually delete source directory:
   ```bash
   rm -rf storage/webgenesis/{site_id}/source
   ```

---

#### Issue 3: "Build not ready for deployment"

**Symptoms:**
```json
{
  "detail": "Build not ready for deployment. Ensure source has been generated and built."
}
```

**Causes:**
- Skipped generate or build steps
- Build failed silently

**Solutions:**
1. Check status: `GET /status`
2. Ensure workflow order: submit → generate → build → deploy
3. Check manifest for errors:
   ```bash
   cat storage/webgenesis/{site_id}/manifest.json | jq
   ```

---

#### Issue 4: "Port already allocated"

**Symptoms:**
```json
{
  "detail": "No available ports in range 8080-8180"
}
```

**Causes:**
- All ports in range are in use
- Previous deployments not cleaned up

**Solutions:**
1. Stop old containers:
   ```bash
   docker ps | grep webgenesis
   docker stop webgenesis-{site_id}
   ```

2. Free up ports:
   ```bash
   netstat -tuln | grep -E ":(8080|8100|8120)"
   ```

3. Increase port range (requires code change)

---

#### Issue 5: "Deployment forbidden (HTTP 403)"

**Symptoms:**
```json
{
  "error": "deployment_forbidden",
  "message": "Deployment operations are restricted to DMZ and LOCAL trust tiers",
  "trust_tier": "external"
}
```

**Causes:**
- Request from EXTERNAL trust tier (not localhost or DMZ gateway)

**Solutions:**
1. **From localhost:**
   ```bash
   curl -X POST http://localhost:8000/api/webgenesis/{site_id}/deploy
   ```

2. **From DMZ gateway:**
   ```bash
   curl -X POST http://localhost:8000/api/webgenesis/{site_id}/deploy \
     -H "x-dmz-gateway-id: telegram_gateway" \
     -H "x-dmz-gateway-token: YOUR_TOKEN"
   ```

3. **Security note:** EXTERNAL blocking is intentional for security.

---

#### Issue 6: "Container health check failed"

**Symptoms:**
- Container starts but immediately stops
- Health check endpoint returns 502/503

**Causes:**
- Invalid HTML in build artifacts
- Incorrect healthcheck path
- Nginx configuration error

**Solutions:**
1. Check container logs:
   ```bash
   docker logs webgenesis-{site_id}
   ```

2. Verify build artifacts:
   ```bash
   ls -la storage/webgenesis/{site_id}/build/
   cat storage/webgenesis/{site_id}/build/index.html
   ```

3. Test health check manually:
   ```bash
   docker exec webgenesis-{site_id} wget -O- http://localhost/
   ```

---

### Debug Checklist

**Before Deployment:**
- [ ] Spec submitted successfully (HTTP 201)
- [ ] Site ID recorded
- [ ] Source generated (check `source/` directory)
- [ ] Build completed (check `build/` directory + artifact_hash.txt)
- [ ] Status shows `status: "built"`

**After Deployment:**
- [ ] Container running (`docker ps | grep webgenesis`)
- [ ] Port accessible (`curl http://localhost:{port}`)
- [ ] Health check passing (check `docker ps` HEALTH column)
- [ ] Status shows `status: "deployed"`

**If Issues Persist:**
1. Check backend logs: `docker compose logs -f backend`
2. Check manifest: `cat storage/webgenesis/{site_id}/manifest.json`
3. Check audit trail: `cat storage/audit/trail.jsonl | grep webgenesis`

---

## Examples

### Example 1: Simple Landing Page

```json
{
  "spec": {
    "spec_version": "1.0.0",
    "name": "simple-landing",
    "domain": "landing.example.com",
    "locale_default": "en",
    "locales": ["en"],
    "template": "static_html",
    "pages": [
      {
        "slug": "home",
        "title": "Welcome to Our Product",
        "description": "The best product you'll ever use",
        "sections": [
          {
            "section_id": "hero",
            "type": "hero",
            "title": "Transform Your Business",
            "content": "Our product helps you achieve 10x productivity",
            "data": {},
            "order": 0
          },
          {
            "section_id": "cta",
            "type": "cta",
            "title": "Ready to Start?",
            "content": "Join 10,000+ satisfied customers",
            "data": {
              "buttons": [
                {"text": "Start Free Trial", "url": "/signup", "primary": true}
              ]
            },
            "order": 1
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
        "base_size": "16px"
      }
    },
    "seo": {
      "title": "Best Product Ever",
      "description": "Transform your business with our amazing product",
      "keywords": ["product", "business", "productivity"],
      "twitter_card": "summary"
    },
    "deploy": {
      "target": "compose",
      "healthcheck_path": "/",
      "ssl_enabled": false
    }
  }
}
```

### Example 2: Multi-Page Portfolio

```json
{
  "spec": {
    "spec_version": "1.0.0",
    "name": "dev-portfolio",
    "domain": "johndoe.dev",
    "locale_default": "en",
    "locales": ["en"],
    "template": "static_html",
    "pages": [
      {
        "slug": "home",
        "title": "John Doe - Developer",
        "description": "Full-stack developer portfolio",
        "sections": [
          {
            "section_id": "hero",
            "type": "hero",
            "title": "Hi, I'm John Doe",
            "content": "Full-stack developer & AI enthusiast",
            "data": {},
            "order": 0
          },
          {
            "section_id": "skills",
            "type": "features",
            "title": "Skills",
            "content": "",
            "data": {
              "items": [
                {"title": "Python", "description": "Expert", "icon": "🐍"},
                {"title": "React", "description": "Advanced", "icon": "⚛️"},
                {"title": "Docker", "description": "Intermediate", "icon": "🐳"}
              ]
            },
            "order": 1
          }
        ],
        "layout": "default"
      },
      {
        "slug": "projects",
        "title": "My Projects",
        "description": "Showcase of my work",
        "sections": [
          {
            "section_id": "projects_list",
            "type": "features",
            "title": "Featured Projects",
            "content": "",
            "data": {
              "items": [
                {
                  "title": "AI Chatbot",
                  "description": "GPT-powered customer support bot",
                  "icon": "💬"
                },
                {
                  "title": "Dashboard",
                  "description": "Real-time analytics platform",
                  "icon": "📊"
                }
              ]
            },
            "order": 0
          }
        ],
        "layout": "default"
      },
      {
        "slug": "contact",
        "title": "Contact Me",
        "description": "Get in touch",
        "sections": [
          {
            "section_id": "contact_info",
            "type": "contact",
            "title": "Let's Connect",
            "content": "Email: john@example.com<br>GitHub: @johndoe",
            "data": {},
            "order": 0
          }
        ],
        "layout": "default"
      }
    ],
    "theme": {
      "colors": {
        "primary": "#2563EB",
        "secondary": "#7C3AED",
        "accent": "#059669",
        "background": "#FFFFFF",
        "text": "#111827"
      },
      "typography": {
        "font_family": "Inter, system-ui, sans-serif",
        "base_size": "16px",
        "heading_font": "Poppins, sans-serif"
      }
    },
    "seo": {
      "title": "John Doe - Full-Stack Developer",
      "description": "Portfolio of John Doe, full-stack developer specializing in AI and web technologies",
      "keywords": ["developer", "portfolio", "AI", "full-stack"],
      "og_image": "https://johndoe.dev/og-image.jpg",
      "twitter_card": "summary_large_image",
      "twitter_handle": "@johndoe"
    },
    "deploy": {
      "target": "compose",
      "healthcheck_path": "/",
      "ssl_enabled": false
    }
  }
}
```

### Example 3: Business Website

```json
{
  "spec": {
    "spec_version": "1.0.0",
    "name": "acme-corp",
    "domain": "acme.com",
    "locale_default": "en",
    "locales": ["en", "de"],
    "template": "static_html",
    "pages": [
      {
        "slug": "home",
        "title": "ACME Corporation",
        "description": "Leading provider of innovative solutions",
        "sections": [
          {
            "section_id": "hero",
            "type": "hero",
            "title": "Innovating Tomorrow, Today",
            "content": "ACME delivers cutting-edge solutions for modern businesses",
            "data": {},
            "order": 0
          },
          {
            "section_id": "services",
            "type": "features",
            "title": "Our Services",
            "content": "",
            "data": {
              "items": [
                {"title": "Consulting", "description": "Expert business advice", "icon": "💼"},
                {"title": "Development", "description": "Custom software solutions", "icon": "⚙️"},
                {"title": "Support", "description": "24/7 customer support", "icon": "🛟"}
              ]
            },
            "order": 1
          },
          {
            "section_id": "testimonials",
            "type": "testimonials",
            "title": "What Our Clients Say",
            "content": "",
            "data": {
              "items": [
                {
                  "quote": "ACME transformed our business operations",
                  "author": "Jane Smith",
                  "company": "TechCorp"
                },
                {
                  "quote": "Outstanding service and results",
                  "author": "Bob Johnson",
                  "company": "StartupXYZ"
                }
              ]
            },
            "order": 2
          },
          {
            "section_id": "cta",
            "type": "cta",
            "title": "Ready to Get Started?",
            "content": "Schedule a free consultation today",
            "data": {
              "buttons": [
                {"text": "Contact Us", "url": "/contact", "primary": true},
                {"text": "Learn More", "url": "/about", "primary": false}
              ]
            },
            "order": 3
          }
        ],
        "layout": "default"
      },
      {
        "slug": "about",
        "title": "About ACME",
        "description": "Learn about our company and mission",
        "sections": [
          {
            "section_id": "story",
            "type": "content",
            "title": "Our Story",
            "content": "<p>Founded in 2020, ACME has grown to become a leader in innovative business solutions...</p>",
            "data": {},
            "order": 0
          }
        ],
        "layout": "default"
      },
      {
        "slug": "contact",
        "title": "Contact ACME",
        "description": "Get in touch with our team",
        "sections": [
          {
            "section_id": "contact_form",
            "type": "contact",
            "title": "Contact Us",
            "content": "Email: contact@acme.com<br>Phone: +1 800 123 4567<br>Address: 123 Business Ave, Suite 100, City, ST 12345",
            "data": {},
            "order": 0
          }
        ],
        "layout": "default"
      }
    ],
    "theme": {
      "colors": {
        "primary": "#1E40AF",
        "secondary": "#059669",
        "accent": "#F59E0B",
        "background": "#F9FAFB",
        "text": "#111827"
      },
      "typography": {
        "font_family": "Roboto, system-ui, sans-serif",
        "base_size": "16px",
        "heading_font": "Montserrat, sans-serif"
      }
    },
    "seo": {
      "title": "ACME Corporation - Innovative Business Solutions",
      "description": "Leading provider of consulting, development, and support services for modern businesses",
      "keywords": ["business", "consulting", "development", "enterprise"],
      "og_image": "https://acme.com/og-image.jpg",
      "twitter_card": "summary_large_image",
      "twitter_handle": "@acmecorp"
    },
    "deploy": {
      "target": "compose",
      "healthcheck_path": "/",
      "ssl_enabled": false
    }
  }
}
```

---

## Future Enhancements

**Sprint II Roadmap:**
- SSL/TLS certificate automation (Let's Encrypt)
- Custom domain configuration
- Nginx reverse proxy integration
- Multi-language support (i18n)
- Template variants (blog, e-commerce, SaaS)
- Asset optimization (minification, compression)
- CDN integration
- Analytics integration (Google Analytics, Plausible)
- Form handling (contact forms, newsletters)
- A/B testing support

**Sprint III Roadmap:**
- CMS integration (headless CMS)
- Dynamic content (API-driven)
- User authentication
- Database integration
- Payment gateway integration
- Advanced SEO (schema.org, sitemap generation)
- Performance monitoring
- Automated testing (Lighthouse CI)

---

## Support & Contributing

**Issue Reporting:**
- GitHub Issues: https://github.com/satoshiflow/BRAiN/issues
- Label: `webgenesis`

**Documentation:**
- Module README: `backend/app/modules/webgenesis/README.md`
- Test Suite: `backend/tests/test_webgenesis_mvp.py`
- This file: `docs/WEBGENESIS_MVP.md`

**Related Modules:**
- AXE Governance: `backend/app/modules/axe_governance/`
- Audit System: `backend/modules/audit_trail.py`

---

**WebGenesis MVP v1.0.0 - Powered by BRAiN Framework**
