# WebGenesis Sprint III: Control Center UI

**Version:** 1.0
**Sprint:** III - Control Plane UI
**Date:** 2025-12-25
**Status:** ✅ Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Pages](#pages)
4. [Components](#components)
5. [Trust Tier Awareness](#trust-tier-awareness)
6. [Safety Features](#safety-features)
7. [User Workflows](#user-workflows)
8. [Development Notes](#development-notes)
9. [API Integration](#api-integration)
10. [Future Enhancements](#future-enhancements)

---

## Overview

**WebGenesis Control Center UI** is a comprehensive frontend interface for managing website generation, deployment, and lifecycle operations within the BRAiN Control Center. Built with Next.js 14 (App Router), React 18, TypeScript, and Tailwind CSS.

### Key Features

- **Site List View** - Browse and manage all WebGenesis sites
- **Site Detail View** - Detailed site information with 4 tabs (Overview, Releases, DNS, Audit)
- **WebsiteSpec Builder** - Guided 5-step wizard for creating new sites
- **Lifecycle Management** - Start, stop, restart, rollback, and remove sites
- **DNS Management** - Configure DNS records with trust tier enforcement (LOCAL only)
- **Release Management** - View release history and rollback to previous versions
- **Trust Tier Awareness** - Client-side hints with warnings for restricted operations
- **Safety Features** - Confirmation modals, disabled states, error boundaries

### Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.2.33 | React framework (App Router) |
| React | 18 | UI library |
| TypeScript | 5.4+ | Type safety |
| Tailwind CSS | 3.4+ | Utility-first styling |
| Lucide React | Latest | Icon library |

### Project Location

```
frontend/control_deck/
├── app/
│   └── webgenesis/
│       ├── page.tsx                    # Site list page
│       ├── new/
│       │   └── page.tsx                # New site creation page
│       └── [site_id]/
│           └── page.tsx                # Site detail page
├── components/
│   └── webgenesis/
│       ├── SiteTable.tsx               # Site list table
│       ├── SiteStatusBadge.tsx         # Status indicator
│       ├── LifecycleBadge.tsx          # Lifecycle status
│       ├── HealthBadge.tsx             # Health status
│       ├── SiteActions.tsx             # Action dropdown
│       ├── SiteOverview.tsx            # Overview tab
│       ├── ReleaseList.tsx             # Releases tab
│       ├── DNSPanel.tsx                # DNS tab
│       ├── AuditTimeline.tsx           # Audit tab
│       ├── SpecBuilder.tsx             # Spec builder wizard
│       ├── TrustTierBanner.tsx         # Trust tier warnings
│       ├── ConfirmModal.tsx            # Confirmation dialogs
│       └── ErrorBoundary.tsx           # Error handling
├── lib/
│   ├── webgenesisApi.ts                # WebGenesis API client
│   └── dnsApi.ts                       # DNS API client + trust tier detection
└── types/
    └── webgenesis.ts                   # TypeScript DTOs
```

---

## Architecture

### Component Hierarchy

```
WebGenesis Pages
├── /webgenesis (Site List)
│   └── SiteTable
│       ├── SiteStatusBadge
│       ├── LifecycleBadge
│       ├── HealthBadge
│       └── SiteActions
│
├── /webgenesis/new (New Site)
│   └── SpecBuilder (5-step wizard)
│       ├── Step1: Basic Info
│       ├── Step2: Theme
│       ├── Step3: SEO
│       ├── Step4: Deployment
│       └── Step5: Review & Deploy
│
└── /webgenesis/[site_id] (Site Detail)
    ├── Tab: Overview
    │   └── SiteOverview
    ├── Tab: Releases
    │   └── ReleaseList
    ├── Tab: DNS
    │   └── DNSPanel
    │       └── TrustTierBanner
    └── Tab: Audit
        └── AuditTimeline
```

### Data Flow

```
User Action → Component → API Client → Backend API
                ↓
           LoadState Pattern
                ↓
         UI Update (React)
```

**LoadState Pattern:**
```typescript
type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};
```

Used for all async operations to manage loading/error/success states consistently.

---

## Pages

### 1. Site List Page (`/webgenesis`)

**File:** `app/webgenesis/page.tsx`

**Purpose:** Main landing page showing all WebGenesis sites with stats and quick actions.

**Features:**
- **Stats Cards:**
  - Total Sites
  - Running (green)
  - Stopped (yellow)
  - Failed (red)
- **Site Table:**
  - Site ID (clickable → detail page)
  - Domain
  - Status, Lifecycle, Health
  - Current Release
  - DNS Enabled (✓/✗)
  - Deployed URL (external link)
  - Updated timestamp
  - Actions dropdown
- **Quick Actions:**
  - Create New Site
  - Documentation
  - System Settings
- **Backend Endpoint Notice:**
  - Shows warning if GET /api/webgenesis/sites not implemented
  - Yellow banner with AlertCircle icon
- **Empty State:**
  - Globe icon
  - Helpful message
  - Create button
- **Error Handling:**
  - Red error banner for API failures

**Navigation:**
- Accessible from sidebar: WebGenesis → Sites
- Header button: "Create New Site" → `/webgenesis/new`
- Site ID links → `/webgenesis/[site_id]`

---

### 2. New Site Page (`/webgenesis/new`)

**File:** `app/webgenesis/new/page.tsx`

**Purpose:** Create new websites using the guided SpecBuilder wizard.

**Features:**
- **Header:**
  - Back navigation to sites list
  - Globe icon
  - Title: "Create New Site"
- **SpecBuilder Wizard:**
  - 5-step process (see Components section)
  - Progress indicator
  - JSON preview
  - Deploy Now button

**Navigation:**
- Accessible from sidebar: WebGenesis → Create New Site
- Accessible from site list: "Create New Site" button
- Back button → `/webgenesis`
- On success → `/webgenesis/[site_id]` (auto-redirect)

---

### 3. Site Detail Page (`/webgenesis/[site_id]`)

**File:** `app/webgenesis/[site_id]/page.tsx`

**Purpose:** Detailed view of a single site with 4 tabs for different management aspects.

**Features:**
- **Header:**
  - Back navigation to sites list
  - Globe icon with site ID
  - Status badges (Status, Lifecycle, Health)
  - "Visit Site" button (if deployed)
- **Tab Navigation:**
  - Overview
  - Releases
  - DNS
  - Audit
- **Loading State:**
  - Spinner with "Loading site details..."
- **Error State:**
  - Red error panel with back button

**Tabs:**

#### Tab 1: Overview
- Quick actions (Start, Stop, Restart, Remove)
- Site Information (timestamps, hashes)
- Container Information (ID, image, ports)
- Error Info (if last_error present)
- Metadata viewer (JSON)

#### Tab 2: Releases
- Release history cards
- "Latest" badge for current release
- Rollback buttons (disabled for latest)
- Confirm dialog before rollback
- Empty state if no releases

#### Tab 3: DNS
- Trust tier warnings (DMZ/EXTERNAL blocked)
- DNS zones dropdown
- DNS record form (zone, type, name, value, TTL)
- Apply button (disabled if not LOCAL tier)
- Last result display (success/error)
- Empty state if no zones

#### Tab 4: Audit
- Timeline with vertical line
- Event cards with severity icons
- Timestamp, source, description
- Metadata viewer
- Empty state (backend endpoint not yet implemented)

**Navigation:**
- Accessible from site list: Click Site ID
- Back button → `/webgenesis`

---

## Components

### Data Display Components

#### SiteTable.tsx
**Purpose:** Main data table for site list view

**Features:**
- 10 columns (Site ID, Domain, Status, Lifecycle, Health, Release, DNS, URL, Updated, Actions)
- Clickable Site ID links
- External link icon for deployed URLs
- Empty state with helpful message
- Responsive with scrolling (max-height: 600px)

**Props:**
```typescript
interface SiteTableProps {
  sites: SiteListItem[];
  onRefresh?: () => void;
}
```

---

#### SiteStatusBadge.tsx
**Purpose:** Display site status with color coding

**States:**
- `pending` - Gray
- `generating` - Blue
- `generated` - Cyan
- `building` - Purple
- `built` - Indigo
- `deploying` - Amber
- `deployed` - Emerald (success)
- `failed` - Rose (error)

**Props:**
```typescript
interface SiteStatusBadgeProps {
  status: SiteStatus;
}
```

---

#### LifecycleBadge.tsx
**Purpose:** Display Docker container lifecycle status

**States:**
- `running` - Emerald (success)
- `stopped` - Gray
- `exited` - Orange
- `restarting` - Blue
- `paused` - Amber
- `dead` - Rose (error)
- `created` - Cyan
- `unknown` - Dark gray

**Props:**
```typescript
interface LifecycleBadgeProps {
  status: SiteLifecycleStatus;
}
```

---

#### HealthBadge.tsx
**Purpose:** Display health status with icons

**States:**
- `healthy` - Emerald + CheckCircle2 icon
- `unhealthy` - Rose + XCircle icon
- `starting` - Amber + Clock icon
- `unknown` - Gray + HelpCircle icon

**Props:**
```typescript
interface HealthBadgeProps {
  status: HealthStatus;
}
```

---

### Action Components

#### SiteActions.tsx
**Purpose:** Dropdown menu for site lifecycle operations

**Features:**
- Actions: Start, Stop, Restart, Rollback, Remove
- State-aware disabled logic:
  - Start: Only if stopped/exited
  - Stop: Only if running
  - Restart: Only if running
  - Rollback: Only if current_release_id exists
  - Remove: Always enabled
- Confirm dialog for destructive Remove action
- Auto-refresh after action
- Loading state during processing

**Props:**
```typescript
interface SiteActionsProps {
  site: SiteListItem;
  onRefresh?: () => void;
}
```

---

### Tab Components

#### SiteOverview.tsx
**Purpose:** Overview tab showing site metadata and quick actions

**Sections:**
1. **Quick Actions:**
   - Start, Stop, Restart, Remove buttons
   - Color-coded by action type
   - Disabled states based on lifecycle
2. **Site Information:**
   - Site ID, Spec Hash
   - Created, Updated, Generated, Built, Deployed timestamps
   - Artifact hash
3. **Container Information:**
   - Container ID, Image Tag
   - Deployed URL (clickable)
   - Ports, Deploy path
4. **Error Info (if present):**
   - Last error message
   - Error count
5. **Additional Metadata:**
   - JSON viewer for custom metadata

**Props:**
```typescript
interface SiteOverviewProps {
  siteId: string;
  manifest: SiteManifest;
  isRunning: boolean;
  healthStatus?: string;
  onRefresh?: () => void;
}
```

---

#### ReleaseList.tsx
**Purpose:** Releases tab showing release history with rollback

**Features:**
- Release cards with:
  - Release ID (full hash)
  - "Latest" badge for current release
  - Created timestamp
  - Artifact hash (truncated)
  - Health status badge
  - Deployed URL (clickable)
  - Metadata viewer (collapsible)
- Rollback button (disabled for latest release)
- Confirm dialog before rollback
- Refresh button
- Empty state if no releases

**Props:**
```typescript
interface ReleaseListProps {
  siteId: string;
  onRefresh?: () => void;
}
```

---

#### DNSPanel.tsx
**Purpose:** DNS tab for DNS record management (LOCAL tier only)

**Features:**
- **Trust Tier Warnings:**
  - Warning banner for DMZ/EXTERNAL tiers
  - Success banner for LOCAL tier
- **DNS Zones:**
  - Dropdown with allowlisted zones
  - Loading/error states
  - Empty state if no zones
- **DNS Record Form:**
  - Zone selection
  - Record type (A, AAAA, CNAME, MX, TXT)
  - Record name (@ or subdomain)
  - Record value (type-specific placeholders)
  - TTL input (60-86400 seconds)
  - Apply button (disabled if not LOCAL tier)
- **Last Result Display:**
  - Success/error indicator
  - Action performed (created/updated/no_change)
  - Record details
  - Errors and warnings lists

**Props:**
```typescript
interface DNSPanelProps {
  siteId: string;
}
```

**Trust Tier Enforcement:**
- Client-side hint: `getEstimatedTrustTier()`
- Backend enforces actual restriction (HTTP 403 if not LOCAL)
- Form disabled if not LOCAL tier
- Clear instructional messages

---

#### AuditTimeline.tsx
**Purpose:** Audit tab showing audit event timeline

**Features:**
- **Timeline:**
  - Vertical line connecting events
  - Chronological order
- **Event Cards:**
  - Severity icon (INFO, WARNING, ERROR, CRITICAL)
  - Event type and description
  - Timestamp and source
  - Metadata viewer (collapsible)
  - Color-coded severity badges
- **Refresh Button**
- **Empty State:**
  - Clock icon
  - Message: "Audit events are automatically created by the backend"

**Props:**
```typescript
interface AuditTimelineProps {
  siteId: string;
}
```

**Note:** Backend endpoint not yet implemented. Shows empty state with placeholder.

---

### Wizard Components

#### SpecBuilder.tsx
**Purpose:** Multi-step wizard for building WebsiteSpec

**Steps:**

**Step 1: Basic Info**
- Site Name (required)
- Domain (required)
- Template (static_html, nextjs, react)
- Default Locale (en, de, fr, es)

**Step 2: Theme**
- Color Pickers:
  - Primary (#3b82f6)
  - Secondary (#8b5cf6)
  - Accent (#10b981)
  - Background (#ffffff)
  - Text (#000000)
- Dual input: Color picker + hex input

**Step 3: SEO**
- Page Title (required)
- Meta Description (required, textarea)
- Keywords (comma-separated)
- Twitter Card Type (summary, summary_large_image, app, player)

**Step 4: Deployment**
- Deployment Target (compose, k8s)
- Healthcheck Path (default: /)
- SSL Enabled (checkbox)
- **DNS Configuration (Optional):**
  - Enable DNS (checkbox)
  - DNS Zone
  - Record Type (A, AAAA, CNAME)
  - Record Name (@ or subdomain)
  - TTL (60-86400 seconds)

**Step 5: Review & Deploy**
- Summary cards showing all configuration
- Deploy Now button

**Features:**
- **Progress Indicator:**
  - Visual step indicator
  - Active/completed/pending states
  - Step labels
- **Navigation:**
  - Previous/Next buttons
  - Previous hidden on Step 1
  - Next → Deploy Now on Step 5
- **JSON Preview:**
  - Toggle show/hide
  - Live preview of entire WebsiteSpec
  - Formatted JSON
- **Validation:**
  - Required fields enforced
  - Next button disabled if incomplete
- **Deploy Functionality:**
  - Calls `deployFullPipeline()` (spec → generate → build → deploy)
  - Loading state with spinner
  - Success/error feedback
  - Auto-redirect to site detail on success

**Props:** None (self-contained with local state)

---

### Safety Components

#### TrustTierBanner.tsx
**Purpose:** Reusable trust tier awareness banner

**Features:**
- Shows warnings/success based on current vs required tier
- Variants: info (success), warning (restriction), error (blocking)
- Custom feature name in messages
- Color-coded by severity

**Props:**
```typescript
interface TrustTierBannerProps {
  requiredTier?: TrustTier;
  feature?: string;
  variant?: "warning" | "info" | "error";
}
```

**Usage Example:**
```tsx
<TrustTierBanner
  requiredTier="LOCAL"
  feature="DNS management"
  variant="warning"
/>
```

---

#### ConfirmModal.tsx
**Purpose:** Reusable confirmation dialog for destructive actions

**Features:**
- Modal with backdrop blur
- Custom title and message
- Configurable button labels
- Variants: danger (red), warning (amber), info (blue)
- Click outside to close

**Props:**
```typescript
interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "warning" | "danger" | "info";
}
```

**Usage Example:**
```tsx
const [showConfirm, setShowConfirm] = useState(false);

<ConfirmModal
  isOpen={showConfirm}
  onClose={() => setShowConfirm(false)}
  onConfirm={() => handleRemove()}
  title="Remove Site"
  message="Are you sure? This action cannot be undone."
  variant="danger"
/>
```

---

#### ErrorBoundary.tsx
**Purpose:** React error boundary for graceful error handling

**Features:**
- Catches errors in component tree
- Displays user-friendly error message
- "Try again" button to reset
- Optional custom fallback UI

**Usage Example:**
```tsx
<ErrorBoundary>
  <SiteTable sites={sites} />
</ErrorBoundary>
```

**Props:**
```typescript
interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}
```

---

## Trust Tier Awareness

### Overview

WebGenesis Control Center implements **trust tier awareness** to restrict sensitive operations based on where the UI is accessed from. This follows the **Fail-Closed principle** from the STARTPROMPT.

### Trust Tiers

| Tier | Description | DNS Ops | Deployment | Lifecycle |
|------|-------------|---------|------------|-----------|
| **LOCAL** | Localhost (127.0.0.1, ::1) | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| **DMZ** | Private network (192.168.*, 10.*, 172.*) | ❌ Blocked | ✅ Allowed | ✅ Allowed |
| **EXTERNAL** | Public internet | ❌ Blocked | ⚠️ Warning | ✅ Allowed |
| **UNKNOWN** | Cannot detect | ❌ Blocked | ⚠️ Warning | ⚠️ Warning |

### Trust Tier Detection

**File:** `lib/dnsApi.ts`

**Functions:**
- `getEstimatedTrustTier()`: Returns "LOCAL" | "DMZ" | "EXTERNAL" | "UNKNOWN"
- `isLikelyLocalTier()`: Returns boolean

**Detection Logic:**
```typescript
const hostname = window.location.hostname;

if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]") {
  return "LOCAL";
}

if (hostname.startsWith("192.168.") || hostname.startsWith("10.") || hostname.startsWith("172.")) {
  return "DMZ";
}

if (hostname.includes(".")) {
  return "EXTERNAL";
}

return "UNKNOWN";
```

**⚠️ CRITICAL SECURITY NOTE:**

> **Client-side trust tier detection is a HINT ONLY, NOT a security boundary.**
>
> - The client-side detection is for **UX purposes only** (show warnings, disable buttons).
> - The **backend is the source of truth** and enforces actual restrictions.
> - Backend validates trust tier for every DNS operation and returns HTTP 403 if not LOCAL.
> - Never rely on client-side detection for security decisions.

### DNS Operations Restriction

**Rule:** DNS operations are **STRICT LOCAL-only** (DMZ/EXTERNAL → HTTP 403).

**Enforcement:**

1. **Backend:** Validates source IP for every DNS operation
   - LOCAL tier required
   - Returns HTTP 403 if DMZ/EXTERNAL

2. **Frontend:** Shows warnings and disables UI proactively
   - `DNSPanel` checks trust tier
   - Shows warning banner if not LOCAL
   - Disables form inputs if not LOCAL
   - Shows helpful instructions to access from localhost

**User Experience:**

- **LOCAL Tier:**
  - Green success banner: "LOCAL Trust Tier Detected"
  - Form enabled
  - Full DNS functionality

- **DMZ/EXTERNAL Tier:**
  - Amber/red warning banner: "DNS Operations Restricted"
  - Form disabled
  - Instructions: "Access from localhost (127.0.0.1) to enable"
  - HTTP 403 error if user somehow bypasses UI

### UI Behavior

**Fail-Closed Principle:**

- If uncertain about trust tier → disable operations
- If backend returns 403 → show clear error message
- Never assume permissions
- Always validate before allowing operations

**Examples:**

```tsx
// DNS Panel - Disabled if not LOCAL
const isLocalTier = trustTier === "LOCAL";

<button
  onClick={handleApplyDNS}
  disabled={!isLocalTier || isApplying}
  className="..."
>
  Apply DNS Record
</button>
```

```tsx
// Trust Tier Banner
<TrustTierBanner
  requiredTier="LOCAL"
  feature="DNS management"
  variant={trustTier === "LOCAL" ? "info" : "warning"}
/>
```

---

## Safety Features

### 1. Confirmation Modals

**Purpose:** Prevent accidental destructive actions.

**Actions Requiring Confirmation:**
- Remove site
- Rollback to previous release

**Implementation:**
- Use `ConfirmModal` component
- Show before executing destructive action
- User must explicitly confirm

**Example (SiteOverview):**
```tsx
// ✅ Updated to use ConfirmModal instead of browser confirm()
const [isConfirmOpen, setIsConfirmOpen] = useState(false);

async function handleAction(action: "remove") {
  setIsConfirmOpen(true); // Show ConfirmModal
}

async function handleRemoveConfirm() {
  await removeSite(siteId, false);
  window.location.href = "/webgenesis";
}

<ConfirmModal
  isOpen={isConfirmOpen}
  onClose={() => setIsConfirmOpen(false)}
  onConfirm={handleRemoveConfirm}
  title="Remove Site"
  message={`Are you sure you want to remove site ${siteId}?`}
  variant="danger"
/>
```

**Status:** ✅ All browser `confirm()` dialogs replaced with `ConfirmModal` for better UX.

---

### 2. Disabled States

**Purpose:** Prevent invalid operations based on current state.

**Examples:**
- Start button disabled if site already running
- Stop button disabled if site not running
- Restart button disabled if site not running
- Rollback button disabled for latest release
- DNS form disabled if not LOCAL tier

**Implementation:**
```tsx
const canStart = site.lifecycle_status === "stopped" || site.lifecycle_status === "exited";

<button disabled={!canStart || isProcessing}>
  Start
</button>
```

---

### 3. Error Boundaries

**Purpose:** Gracefully handle unexpected errors without crashing entire app.

**Implementation:**
- `ErrorBoundary` component (React class component)
- Wrap around WebGenesis pages/components
- Catches errors in component tree
- Displays user-friendly error message
- "Try again" button to recover

**Usage:**
```tsx
<ErrorBoundary>
  <WebGenesisPage />
</ErrorBoundary>
```

---

### 4. Loading States

**Purpose:** Provide feedback during async operations.

**Implementation:**
- LoadState pattern: `{ data?, loading, error? }`
- Spinner with descriptive text during loading
- Disabled buttons during processing

**Example:**
```tsx
{sitesState.loading ? (
  <div>Loading sites...</div>
) : sitesState.error ? (
  <div>Error: {sitesState.error}</div>
) : (
  <SiteTable sites={sitesState.data || []} />
)}
```

---

### 5. Error Handling

**Purpose:** Display clear error messages to users.

**Implementation:**
- Red error banners with AlertCircle icon
- Specific error messages (not generic "Error occurred")
- HTTP 403 → "DNS operations require LOCAL trust tier"
- Network errors → "Failed to fetch data: [reason]"

**Example (DNSPanel):**
```tsx
if (!res.ok) {
  if (res.status === 403) {
    throw new Error("DNS operations require LOCAL trust tier (localhost only)");
  }
  throw new Error(`Failed to apply DNS record: ${res.status} ${text}`);
}
```

---

### 6. Validation

**Purpose:** Ensure data integrity before submission.

**Implementation:**
- Required fields enforced in forms
- Next button disabled in wizard if fields missing
- Deploy button disabled if spec incomplete
- Client-side validation before API calls

**Example (SpecBuilder):**
```tsx
const canProceed = () => {
  switch (currentStep) {
    case 1:
      return spec.name && spec.domain;
    case 3:
      return spec.seo?.title && spec.seo?.description;
    default:
      return true;
  }
};

<button disabled={!canProceed()}>
  Next
</button>
```

---

## User Workflows

### Workflow 1: Create and Deploy New Site

**Steps:**

1. **Navigate:** Click "Create New Site" button (from sidebar or site list)
2. **Step 1 - Basic Info:**
   - Enter site name (e.g., "My Portfolio")
   - Enter domain (e.g., "myportfolio.com")
   - Select template (static_html/nextjs/react)
   - Select locale (en/de/fr/es)
   - Click "Next"
3. **Step 2 - Theme:**
   - Customize colors using color pickers
   - Or enter hex values manually
   - Click "Next"
4. **Step 3 - SEO:**
   - Enter page title
   - Enter meta description
   - Enter keywords (optional)
   - Select Twitter card type
   - Click "Next"
5. **Step 4 - Deployment:**
   - Select deployment target (compose/k8s)
   - Set healthcheck path
   - Enable SSL (checkbox)
   - (Optional) Enable DNS configuration:
     - Enter DNS zone
     - Select record type
     - Enter record name
     - Set TTL
   - Click "Next"
6. **Step 5 - Review & Deploy:**
   - Review all configuration
   - (Optional) Toggle "Show JSON" to view spec
   - Click "Deploy Now"
7. **Deployment:**
   - Wait for pipeline to complete (spec → generate → build → deploy)
   - Auto-redirect to site detail page on success
8. **Verify:**
   - Check site status (should be "deployed")
   - Check lifecycle status (should be "running")
   - Click "Visit Site" to open deployed URL

**Expected Result:**
- Site created, generated, built, and deployed
- Site ID assigned
- Container running
- Accessible via deployed URL

---

### Workflow 2: View Site Details and Manage Lifecycle

**Steps:**

1. **Navigate:** From site list, click on a Site ID
2. **Overview Tab:**
   - View site metadata (timestamps, hashes)
   - View container information
   - Use quick actions:
     - Click "Start" to start stopped site
     - Click "Stop" to stop running site
     - Click "Restart" to restart site
3. **Releases Tab:**
   - View release history
   - Click "Rollback" on older release to revert
   - Confirm rollback in dialog
4. **DNS Tab:**
   - (Only if LOCAL tier) Configure DNS records
   - Select zone, type, name, value
   - Click "Apply DNS Record"
   - View result (created/updated/no_change)
5. **Audit Tab:**
   - (When implemented) View audit events timeline

**Expected Result:**
- Full visibility into site state
- Ability to manage lifecycle
- Ability to rollback releases
- (LOCAL only) Ability to configure DNS

---

### Workflow 3: Rollback to Previous Release

**Steps:**

1. **Navigate:** Go to site detail page (`/webgenesis/[site_id]`)
2. **Open Releases Tab**
3. **Locate Release:**
   - Current release has "Latest" badge
   - Previous releases have "Rollback" button
4. **Click "Rollback"** on desired release
5. **Confirm:** Click "Confirm" in confirmation dialog
6. **Wait:** Rollback operation completes
7. **Verify:**
   - Releases tab auto-refreshes
   - New release is now marked "Latest"
   - Site detail page updates (via onRefresh callback)

**Expected Result:**
- Site rolled back to previous release
- Container restarted with old artifact
- Health check passes

---

### Workflow 4: Configure DNS Record (LOCAL Tier Only)

**Pre-requisite:** Must access Control Center from localhost (127.0.0.1)

**Steps:**

1. **Verify Trust Tier:**
   - Access UI from `http://localhost:3000`
   - Trust tier should show "LOCAL"
2. **Navigate:** Go to site detail page (`/webgenesis/[site_id]`)
3. **Open DNS Tab**
4. **Verify Banner:**
   - Should show green "LOCAL Trust Tier Detected" banner
   - Form should be enabled
5. **Select Zone:** Choose DNS zone from dropdown
6. **Configure Record:**
   - Record Type: Select A/AAAA/CNAME
   - Record Name: Enter @ (root) or subdomain
   - Record Value: Enter IP or domain
   - TTL: Set TTL in seconds (default: 3600)
7. **Click "Apply DNS Record"**
8. **View Result:**
   - Green success banner if succeeded
   - Shows action (created/updated/no_change)
   - Shows record details
   - Shows warnings/errors if any

**Expected Result:**
- DNS record created/updated in Hetzner DNS
- Result displayed in UI
- Record is idempotent (can re-apply without duplicate)

**Error Cases:**
- If accessed from DMZ/EXTERNAL: Shows warning banner, form disabled
- If zone not in allowlist: Backend returns error
- If invalid value: Backend validates and returns error

---

## Development Notes

### Type Safety

All components use TypeScript with strict typing:

```typescript
// DTOs match backend Pydantic schemas exactly
import type {
  WebsiteSpec,
  SiteManifest,
  SiteListItem,
  DNSApplyResult,
  ReleaseMetadata,
} from "@/types/webgenesis";
```

**Important:** When backend schemas change, update `types/webgenesis.ts` to match.

---

### API Client Pattern

All API calls go through centralized API clients:

**WebGenesis API (`lib/webgenesisApi.ts`):**
```typescript
export async function submitSpec(spec: WebsiteSpec): Promise<SpecSubmitResponse>;
export async function generateSite(siteId: string, force?: boolean): Promise<GenerateResponse>;
export async function buildSite(siteId: string, force?: boolean): Promise<BuildResponse>;
export async function deploySite(siteId: string, force?: boolean): Promise<DeployResponse>;
export async function getSiteStatus(siteId: string): Promise<SiteStatusResponse>;
export async function startSite(siteId: string): Promise<LifecycleOperationResponse>;
export async function stopSite(siteId: string): Promise<LifecycleOperationResponse>;
export async function restartSite(siteId: string): Promise<LifecycleOperationResponse>;
export async function removeSite(siteId: string, keepData: boolean): Promise<RemoveResponse>;
export async function rollbackSite(siteId: string, releaseId?: string): Promise<RollbackResponse>;
export async function fetchReleases(siteId: string): Promise<ReleasesListResponse>;
export async function deployFullPipeline(spec: WebsiteSpec, options?): Promise<PipelineResult>;
```

**DNS API (`lib/dnsApi.ts`):**
```typescript
export async function applyDNSRecord(request: DNSRecordApplyRequest): Promise<DNSApplyResult>;
export async function fetchDNSZones(): Promise<DNSZonesResponse>;
export function getEstimatedTrustTier(): "LOCAL" | "DMZ" | "EXTERNAL" | "UNKNOWN";
export function isLikelyLocalTier(): boolean;
export function isValidDNSName(name: string): boolean;
export function isValidDNSValue(value: string, recordType: string): { valid: boolean; error?: string };
```

---

### State Management

**Pattern:** LoadState for all async operations

```typescript
type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

const [sitesState, setSitesState] = useState<LoadState<SiteListItem[]>>({
  loading: true,
});

async function loadSites() {
  setSitesState((prev) => ({ ...prev, loading: true, error: undefined }));
  try {
    const sites = await fetchAllSites();
    setSitesState({ data: sites, loading: false });
  } catch (err) {
    setSitesState({ loading: false, error: String(err) });
  }
}
```

**Benefits:**
- Consistent loading/error/success states
- Easy to display spinners, errors, empty states
- Type-safe with TypeScript

---

### Styling Conventions

**Tailwind CSS Classes:**

**Common Patterns:**
```tsx
// Card wrapper
className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4"

// Table wrapper
className="rounded-xl border border-slate-800 bg-slate-950/80"

// Button (primary)
className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"

// Button (secondary)
className="rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 text-sm text-neutral-300 hover:bg-neutral-700"

// Input
className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"

// Badge
className="rounded-full px-2 py-1 text-[10px] uppercase"
```

**Color Palette:**
- Primary: Blue (`blue-500`, `blue-600`)
- Success: Emerald (`emerald-400`, `emerald-900/60`)
- Warning: Amber (`amber-400`, `amber-900/60`)
- Danger: Rose (`rose-400`, `rose-900/60`)
- Neutral: Slate/Neutral (`neutral-800`, `slate-900`)

---

### Component Best Practices

1. **Always use "use client" for interactive components**
   ```tsx
   "use client";

   import { useState } from "react";
   ```

2. **Use LoadState pattern for async data**
   ```tsx
   const [state, setState] = useState<LoadState<T>>({ loading: true });
   ```

3. **Handle empty states**
   ```tsx
   {items.length === 0 && (
     <div className="empty-state">
       <Icon />
       <p>No items found</p>
     </div>
   )}
   ```

4. **Handle error states**
   ```tsx
   {state.error && (
     <div className="error-banner">
       <AlertCircle />
       <p>{state.error}</p>
     </div>
   )}
   ```

5. **Use disabled states for buttons**
   ```tsx
   <button disabled={isLoading || !canProceed()}>
     {isLoading ? "Processing..." : "Submit"}
   </button>
   ```

6. **Provide onRefresh callbacks**
   ```tsx
   interface ComponentProps {
     onRefresh?: () => void;
   }

   // After mutation:
   if (onRefresh) onRefresh();
   ```

---

## API Integration

### Backend Endpoints Used

**WebGenesis Endpoints:**
```
POST   /api/webgenesis/spec                    # Submit spec
POST   /api/webgenesis/{site_id}/generate      # Generate site
POST   /api/webgenesis/{site_id}/build         # Build site
POST   /api/webgenesis/{site_id}/deploy        # Deploy site
GET    /api/webgenesis/{site_id}/status        # Get status
POST   /api/webgenesis/{site_id}/start         # Start site
POST   /api/webgenesis/{site_id}/stop          # Stop site
POST   /api/webgenesis/{site_id}/restart       # Restart site
POST   /api/webgenesis/{site_id}/rollback      # Rollback release
DELETE /api/webgenesis/{site_id}               # Remove site
GET    /api/webgenesis/{site_id}/releases      # List releases
GET    /api/webgenesis/sites                   # ✅ List all sites (IMPLEMENTED)
GET    /api/webgenesis/{site_id}/audit         # ✅ Fetch audit events (IMPLEMENTED)
```

**DNS Endpoints (LOCAL only):**
```
GET    /api/dns/hetzner/zones                  # Fetch DNS zones
POST   /api/dns/hetzner/apply                  # Apply DNS record
```

---

### ✅ Newly Implemented Endpoints (Sprint III Finalization)

**1. GET /api/webgenesis/sites**

**Purpose:** List all WebGenesis sites for site list view

**Status:** ✅ **IMPLEMENTED**

**Response:**
```json
{
  "sites": [
    {
      "site_id": "abc123...",
      "domain": "example.com",
      "status": "deployed",
      "lifecycle_status": "running",
      "health_status": "healthy",
      "current_release_id": "rel_xyz...",
      "deployed_url": "http://localhost:8080",
      "dns_enabled": true,
      "last_action": "deploy",
      "updated_at": "2025-12-25T10:00:00Z"
    }
  ],
  "total_count": 1
}
```

**Implementation:**
- Scans storage directory for site manifests
- Parses manifest.json files
- Returns SiteListItem[] array
- Fail-safe: broken manifests marked as "failed" status
- Includes health checks and container status

**Backend Files:**
- `backend/app/modules/webgenesis/service.py` - `list_all_sites()` method
- `backend/app/modules/webgenesis/router.py` - GET /sites endpoint
- `backend/app/modules/webgenesis/schemas.py` - SiteListItem, SitesListResponse DTOs

---

**2. GET /api/webgenesis/{site_id}/audit**

**Purpose:** Fetch audit events for audit timeline

**Status:** ✅ **IMPLEMENTED**

**Query Parameters:**
- `limit`: Maximum events to return (1-500, default 100)
- `severity`: Filter by severity (INFO, WARNING, ERROR, CRITICAL)
- `types`: Comma-separated event types to filter

**Response:**
```json
{
  "site_id": "abc123...",
  "events": [
    {
      "id": "evt_123",
      "timestamp": "2025-12-25T10:00:00Z",
      "site_id": "abc123...",
      "event_type": "site.deployed",
      "severity": "INFO",
      "source": "webgenesis.deploy",
      "description": "Site deployed successfully",
      "metadata": {
        "release_id": "rel_xyz",
        "container_id": "abc123"
      }
    }
  ],
  "total_count": 1,
  "filtered_count": 1
}
```

**Implementation:**
- Stores audit events in JSONL format (`storage/audit/webgenesis.jsonl`)
- Filters events by site_id
- Supports severity and event type filtering
- Chronological descending order (newest first)
- Fail-safe: returns empty array for invalid/missing site_id

**Backend Files:**
- `backend/app/modules/webgenesis/service.py` - `_log_audit_event()` and `get_site_audit_events()` methods
- `backend/app/modules/webgenesis/router.py` - GET /{site_id}/audit endpoint
- `backend/app/modules/webgenesis/schemas.py` - AuditEvent, AuditEventSeverity, SiteAuditResponse DTOs

---

## Future Enhancements

### ✅ Priority 1: Complete Missing Endpoints (COMPLETED)

1. **✅ Implement GET /api/webgenesis/sites**
   - ✅ Enable site list view
   - ✅ Remove backend endpoint notice
   - ✅ Allow users to browse existing sites

2. **✅ Implement GET /api/webgenesis/{site_id}/audit**
   - ✅ Enable audit timeline
   - ✅ Show deployment history, errors, warnings
   - ✅ Compliance and debugging

**Status:** All endpoints implemented with full fail-safe error handling and comprehensive tests.

---

### ✅ Priority 2: Upgrade Modals (COMPLETED)

**Previous:** Used browser `confirm()` for destructive actions

**Enhancement:** Replaced with `ConfirmModal` component ✅

**Benefits Achieved:**
- ✅ Better UX with branded modal dialogs
- ✅ Consistent styling with Tailwind CSS
- ✅ More information in dialog
- ✅ Accessibility improvements

**Components Updated:**
- ✅ `SiteActions.tsx` - Remove site confirmation
- ✅ `SiteOverview.tsx` - Remove site confirmation
- ✅ `ReleaseList.tsx` - Rollback confirmation

**Status:** All browser confirm() dialogs replaced with ConfirmModal component.

---

### Priority 3: Enhanced DNS Management

**Features:**
- List existing DNS records for site
- Edit existing records
- Delete records
- Bulk operations
- DNS propagation status
- DNSSEC support

---

### Priority 4: Advanced Filtering and Search

**Site List Enhancements:**
- Search by site ID, domain
- Filter by status, lifecycle, health
- Sort by updated, created, name
- Pagination for large lists

---

### Priority 5: Site Templates

**SpecBuilder Enhancement:**
- Pre-built templates (portfolio, blog, landing page, e-commerce)
- Load template → auto-populate spec
- Template gallery with previews

---

### Priority 6: Real-Time Updates

**WebSocket Integration:**
- Real-time status updates
- Live deployment progress
- Instant lifecycle changes
- No need for manual refresh

**Implementation:**
- Backend WebSocket endpoint
- Frontend useWebSocket hook
- Auto-update LoadState on messages

---

### Priority 7: Batch Operations

**Site List Enhancements:**
- Select multiple sites
- Batch start/stop/restart
- Batch remove
- Progress indicators

---

### Priority 8: Site Cloning

**Feature:**
- Clone existing site
- Copy spec to new site
- Modify domain, name
- Preserve theme, SEO, config

---

### Priority 9: Export/Import

**Features:**
- Export WebsiteSpec as JSON
- Import spec from file
- Share specs between teams
- Version control for specs

---

### Priority 10: Analytics Dashboard

**Features:**
- Deployment success rate
- Average deployment time
- Site health metrics
- DNS query statistics
- Error frequency

---

## Conclusion

The **WebGenesis Control Center UI (Sprint III)** provides a comprehensive, production-ready interface for managing website generation, deployment, and lifecycle operations within BRAiN.

### Key Achievements

✅ **Complete Site Management** - List, create, detail views
✅ **Guided Spec Builder** - 5-step wizard with validation
✅ **Lifecycle Operations** - Start, stop, restart, rollback, remove
✅ **Release Management** - History and rollback functionality
✅ **DNS Integration** - LOCAL tier enforced configuration
✅ **Trust Tier Awareness** - Client-side hints with fail-closed UI
✅ **Safety Features** - Confirmations, disabled states, error boundaries
✅ **Type Safety** - Full TypeScript with strict typing
✅ **Responsive Design** - Mobile-friendly layouts
✅ **Comprehensive Documentation** - This guide

### Security Posture

- **Fail-Closed UI:** Operations disabled when uncertain
- **Trust Tier Enforcement:** DNS operations require LOCAL tier
- **Backend Validation:** Source of truth for all restrictions
- **Confirmation Dialogs:** Prevent accidental destructive actions
- **Error Boundaries:** Graceful degradation on failures
- **No Direct Side Effects:** All operations via API (read/write only)

### Next Steps

1. **Backend:** Implement missing endpoints (sites list, audit events)
2. **Enhancement:** Replace browser confirm() with ConfirmModal
3. **Testing:** Add integration tests for workflows
4. **Optimization:** Add React Query for caching and revalidation
5. **Real-Time:** Add WebSocket support for live updates

---

**Sprint III Status:** ✅ **COMPLETE**

**Documentation Version:** 1.0
**Last Updated:** 2025-12-25
**Maintained By:** Claude (AI Assistant)
