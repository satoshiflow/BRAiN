# Better Auth Integration Skill

**Repository:** https://github.com/better-auth/better-auth  
**Skills Reference:** https://github.com/better-auth/skills  
**Date:** 2026-02-21  
**Context:** BRAiN Authentication Service

---

## Overview

Better Auth is a comprehensive authentication framework for TypeScript applications. It provides:
- Email/Password authentication
- OAuth providers (Google, GitHub, etc.)
- Session management
- Two-factor authentication
- Organization/Team support
- Admin dashboard

---

## Architecture Decision

### Deployment Model: Separate Service

**Why separate service?**
- ✅ Clear separation of concerns
- ✅ Can be reused by multiple apps
- ✅ Independent scaling
- ✅ Easier maintenance
- ✅ Better security isolation

### Infrastructure

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   BRAiN API     │────▶│   Better Auth    │────▶│   PostgreSQL    │
│   (FastAPI)     │     │   (Node.js)      │     │   (Shared DB)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  ControlDeck    │     │   Redis          │
│  (Next.js)      │     │   (Sessions)     │
└─────────────────┘     └──────────────────┘
```

---

## Coolify Service Configuration

### 1. Domain Setup

**Subdomain:** `auth.falklabs.de`

**DNS Record:**
```
Type: A
Name: auth
Value: 46.224.37.114
TTL: 3600
```

### 2. Environment Variables

```bash
# Database (shared with BRAiN)
DATABASE_URL=postgresql://user:password@postgres:5432/better_auth

# Redis (for sessions)
REDIS_URL=redis://redis:6379/1

# App
BETTER_AUTH_SECRET=your-secret-key-here
BETTER_AUTH_URL=https://auth.falklabs.de

# OAuth Providers (optional)
GITHUB_CLIENT_ID=your-github-id
GITHUB_CLIENT_SECRET=your-github-secret
GOOGLE_CLIENT_ID=your-google-id
GOOGLE_CLIENT_SECRET=your-google-secret

# Email (for verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@falklabs.de
```

### 3. Docker Configuration

**Dockerfile:**
```dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy app
COPY . .

# Build
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  better-auth:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - BETTER_AUTH_SECRET=${BETTER_AUTH_SECRET}
      - BETTER_AUTH_URL=${BETTER_AUTH_URL}
    networks:
      - brain-network
    depends_on:
      - postgres
      - redis

networks:
  brain-network:
    external: true
```

---

## Integration with BRAiN

### 1. Backend API (FastAPI)

**Auth Middleware:**
```python
from fastapi import Depends, HTTPException, Request
import httpx

AUTH_SERVICE_URL = "https://auth.falklabs.de"

async def verify_token(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/api/auth/session",
            headers={"Authorization": token}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return response.json()

@app.get("/protected")
async def protected_route(user=Depends(verify_token)):
    return {"message": f"Hello {user['email']}"}
```

### 2. ControlDeck Frontend (Next.js)

**Auth Client Setup:**
```typescript
// lib/auth.ts
import { createAuthClient } from "better-auth/client"

export const authClient = createAuthClient({
  baseURL: "https://auth.falklabs.de"
})

// hooks/use-auth.ts
export function useAuth() {
  const { data: session, isPending } = authClient.useSession()
  
  return {
    user: session?.user,
    isLoading: isPending,
    signIn: authClient.signIn,
    signOut: authClient.signOut
  }
}
```

**Protected Route:**
```typescript
// app/dashboard/page.tsx
import { authClient } from "@/lib/auth"
import { redirect } from "next/navigation"

export default async function DashboardPage() {
  const session = await authClient.getSession()
  
  if (!session) {
    redirect("/login")
  }
  
  return <Dashboard user={session.user} />
}
```

---

## Database Schema

Better Auth creates its own tables:
```sql
-- User table
CREATE TABLE "user" (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  email_verified BOOLEAN DEFAULT FALSE,
  name TEXT,
  image TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Session table
CREATE TABLE "session" (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES "user"(id),
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Account table (for OAuth)
CREATE TABLE "account" (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES "user"(id),
  provider TEXT NOT NULL,
  provider_account_id TEXT NOT NULL,
  access_token TEXT,
  refresh_token TEXT,
  expires_at TIMESTAMP,
  UNIQUE(provider, provider_account_id)
);

-- Verification token
CREATE TABLE "verification" (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  value TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL
);
```

---

## Security Best Practices

### 1. Secrets Management

**Never commit secrets!**
```bash
# Use Coolify Secrets
# Or .env.local (gitignored)
# Or Docker Secrets
```

### 2. CORS Configuration

```typescript
// better-auth.config.ts
export default {
  trustedOrigins: [
    "https://control.brain.falklabs.de",
    "https://api.brain.falklabs.de"
  ]
}
```

### 3. Session Security

```typescript
// Cookie settings
export default {
  advanced: {
    cookiePrefix: "brain_auth",
    useSecureCookies: true,
    sameSite: "lax"
  }
}
```

---

## Migration Strategy

### Phase 1: Setup (Week 1)
- [ ] Deploy Better Auth service to Coolify
- [ ] Configure domain and SSL
- [ ] Set up database tables
- [ ] Test OAuth providers

### Phase 2: Integration (Week 2)
- [ ] Add auth middleware to BRAiN API
- [ ] Create login page in ControlDeck
- [ ] Update protected routes
- [ ] Test end-to-end flow

### Phase 3: Migration (Week 3)
- [ ] Migrate existing users (if any)
- [ ] Update documentation
- [ ] Train team
- [ ] Monitor and optimize

---

## Troubleshooting

### Common Issues

**1. CORS Errors**
```
Solution: Add trusted origins in Better Auth config
```

**2. Database Connection**
```
Solution: Verify DATABASE_URL and network connectivity
```

**3. Session Not Persisting**
```
Solution: Check Redis connection and cookie settings
```

**4. OAuth Redirect Fails**
```
Solution: Verify redirect URLs in OAuth provider settings
```

---

## Resources

- **Documentation:** https://www.better-auth.com/
- **GitHub:** https://github.com/better-auth/better-auth
- **Discord:** https://discord.gg/better-auth
- **Examples:** https://github.com/better-auth/examples

---

## Commands Reference

```bash
# Deploy to Coolify
coolify deploy better-auth

# Check logs
coolify logs better-auth

# Restart service
coolify restart better-auth

# Database migration
npx better-auth migrate
```

---

**Next Steps:**
1. Set up Coolify service for Better Auth
2. Configure environment variables
3. Deploy and test
4. Integrate with BRAiN API
5. Update ControlDeck frontend

