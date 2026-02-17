# BRAiN Auth.js Integration

This document describes the Auth.js (NextAuth.js v5) integration for BRAiN Control Deck.

## Overview

The authentication system uses:
- **Auth.js v5** (NextAuth.js) for authentication
- **Authentik** as the OIDC/OAuth2 provider
- **JWT session strategy** for stateless authentication
- **Middleware** for route protection

## File Structure

```
├── auth.ts                          # Main Auth.js configuration
├── middleware.ts                    # Route protection middleware
├── app/
│   ├── api/auth/[...nextauth]/      # Auth API routes
│   │   └── route.ts
│   ├── auth/
│   │   ├── signin/page.tsx          # Sign-in page
│   │   └── error/page.tsx           # Error page
│   ├── layout.tsx                   # Root layout with AuthProvider
│   └── providers.tsx                # Auth provider wrapper
├── components/auth/
│   ├── index.ts                     # Component exports
│   ├── auth-status.tsx              # Auth status component
│   ├── login-button.tsx             # Login button
│   ├── logout-button.tsx            # Logout button
│   └── user-info.tsx                # User info dropdown
├── hooks/
│   └── use-auth.ts                  # useAuth hook
├── types/
│   └── next-auth.d.ts               # TypeScript types
└── .env.local.example               # Environment variables template
```

## Environment Variables

Copy `.env.local.example` to `.env.local` and fill in the values:

```bash
# Generate a secure random secret
cp .env.local.example .env.local
# Edit .env.local with your values
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AUTH_SECRET` | Random secret for token encryption | `openssl rand -base64 32` |
| `AUTH_AUTHENTIK_ID` | Authentik OAuth2 Client ID | From Authentik application |
| `AUTH_AUTHENTIK_SECRET` | Authentik OAuth2 Client Secret | From Authentik application |
| `AUTH_AUTHENTIK_ISSUER` | Authentik OIDC Issuer URL | `https://authentik.example.com/application/o/brain/` |

## Authentik Configuration

1. Create a new **Provider** in Authentik:
   - Type: OAuth2/OpenID Provider
   - Name: BRAiN Control Deck
   - Client Type: Confidential
   - Redirect URIs: `http://localhost:3000/api/auth/callback/authentik` (dev)

2. Create an **Application**:
   - Name: brain-control-deck
   - Slug: brain-control-deck
   - Provider: Select the provider created above

3. Copy the Client ID and Client Secret to `.env.local`

## Usage

### Protecting Routes

Routes are automatically protected by `middleware.ts`. Unauthenticated users are redirected to `/auth/signin`.

Public routes (no authentication required):
- `/auth/signin`
- `/auth/error`
- `/api/auth/*`

### Using Auth Components

```tsx
import { LoginButton, LogoutButton, UserInfo, AuthStatus } from "@/components/auth";

// Login button
<LoginButton />

// Logout button
<LogoutButton />

// User info dropdown
<UserInfo />

// Combined auth status (shows user info or login button)
<AuthStatus />
```

### Using the useAuth Hook

```tsx
import { useAuth } from "@/hooks/use-auth";

function MyComponent() {
  const { session, user, isAuthenticated, isLoading } = useAuth({
    required: true,      // Redirect to login if not authenticated
    redirectTo: "/auth/signin"
  });

  if (isLoading) return <div>Loading...</div>;

  return <div>Hello {user?.name}</div>;
}
```

### Accessing Session in Server Components

```tsx
import { auth } from "@/auth";

export default async function ServerComponent() {
  const session = await auth();

  if (!session) {
    return <div>Not authenticated</div>;
  }

  return <div>Hello {session.user.name}</div>;
}
```

### Accessing Session in Client Components

```tsx
"use client";

import { useSession } from "next-auth/react";

export default function ClientComponent() {
  const { data: session, status } = useSession();

  if (status === "loading") return <div>Loading...</div>;
  if (status === "unauthenticated") return <div>Not authenticated</div>;

  return <div>Hello {session.user.name}</div>;
}
```

## Session Data

The session contains:

```typescript
{
  user: {
    id: string;          // User ID from Authentik
    name?: string;       // User's full name
    email?: string;      // User's email
    image?: string;      // User's avatar URL
    groups?: string[];   // User's groups from Authentik
  },
  accessToken?: string;  // OAuth2 access token
  idToken?: string;      // OIDC ID token
  provider?: string;     // Authentication provider
  expires: string;       // Session expiration date
}
```

## Security

- **httpOnly cookies**: Session tokens are not accessible via JavaScript
- **Secure cookies**: Cookies are only sent over HTTPS in production
- **SameSite lax**: CSRF protection
- **JWT strategy**: Stateless sessions, no database required
- **30-day session expiry**: Sessions expire after 30 days of inactivity

## Troubleshooting

### "Invalid issuer" error

Verify the `AUTH_AUTHENTIK_ISSUER` URL ends with a trailing slash and matches the Authentik provider configuration.

### "Invalid client" error

Check that the Client ID and Client Secret match the values in Authentik.

### Session not persisting

Ensure `AUTH_SECRET` is set and consistent across server restarts.

### CORS errors

Add your application URL to the allowed redirect URIs in Authentik:
- Development: `http://localhost:3000/api/auth/callback/authentik`
- Production: `https://your-domain.com/api/auth/callback/authentik`
