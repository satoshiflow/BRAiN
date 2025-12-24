# BRAIN Control Center: Admin Module

**Version:** 1.0.0
**Status:** ✅ Production Ready
**Last Updated:** 2025-12-24

---

## 📋 Overview

The Admin Module provides a comprehensive control interface for BRAiN's Sovereign Mode and Fabric Bundle Management system. It enables secure offline operation with model bundle management, network monitoring, and comprehensive audit logging.

### Key Features

- 🛡️ **Sovereign Mode Control** - Switch between operation modes (Online, Offline, Sovereign, Quarantine)
- 📦 **Bundle Management** - Discover, validate, load, and manage offline model bundles
- 🌐 **Network Monitoring** - Real-time connectivity monitoring and network guard status
- 📊 **Audit Logging** - Comprehensive operation tracking with export capabilities

---

## 🏗️ Architecture

```
frontend/brain_control_ui/
├── src/
│   ├── app/(control-center)/admin/       # Admin pages
│   │   ├── sovereign/page.tsx            # Sovereign Mode control
│   │   ├── bundles/page.tsx              # Bundle management
│   │   ├── network/page.tsx              # Network & Gates status
│   │   └── audit/page.tsx                # Audit log viewer
│   │
│   ├── types/sovereign.ts                # TypeScript type definitions
│   ├── hooks/useSovereignMode.ts         # React Query hooks
│   ├── lib/brainApi.ts                   # API client (extended)
│   └── components/
│       ├── app-sidebar.tsx               # Sidebar (extended with Admin section)
│       └── ui/select.tsx                 # Select component (new)
```

---

## 📄 Pages & Features

### 1. **Sovereign Mode** (`/admin/sovereign`)

Main control interface for operation mode management.

**Features:**
- Current mode display with visual badges
- KPI cards (Network Status, Active Bundle, Available Bundles, Network Blocks)
- Mode switch interface (Online, Offline, Sovereign, Quarantine)
- 2-step confirmation dialog with reason input
- Preflight warnings for mode changes
- Real-time status updates (10s refresh)

**Use Cases:**
- Switch to Sovereign Mode when going offline
- Monitor system security status
- View quarantine alerts

---

### 2. **Bundles** (`/admin/bundles`)

Comprehensive bundle management interface.

**Features:**
- Bundle discovery and scanning
- Bundle list with filtering and search
- Validation (SHA256 hash verification)
- Bundle loading with preflight checks
- Quarantine management
- Statistics dashboard (Total, Validated, Loaded, Quarantined)

**Bundle Operations:**
- **Discover:** Scan `storage/models/bundles/` for new bundles
- **Validate:** Verify SHA256 integrity
- **Load:** Activate bundle for offline use
- **Remove Quarantine:** Reset quarantined bundles (with caution)

**Bundle States:**
- `PENDING` - Not yet validated
- `VALIDATED` - Hash verified, ready to load
- `LOADED` - Currently active
- `QUARANTINED` - Failed validation or security check
- `FAILED` - Load error

---

### 3. **Network & Gates** (`/admin/network`)

Network connectivity and security monitoring.

**Features:**
- Network status card (Online/Offline)
- Network guards configuration display
- Auto-detection settings
- Latest network check details
- Refresh capability

**Monitored Metrics:**
- Network connectivity status
- Total blocked requests
- Block HTTP/DNS settings
- Allowed domains whitelist
- Auto-detection interval

---

### 4. **Audit Log** (`/admin/audit`)

Comprehensive audit trail viewer.

**Features:**
- Audit entry table with expandable details
- Event type filtering (Mode Change, Bundle Load, Validation, Network Block)
- Success/failure status
- Metadata and error details
- Export to JSON
- Configurable entry limit (50-500)

**Event Types:**
- `mode_change` - Operation mode switches
- `bundle_load` - Bundle loading events
- `bundle_validation` - Integrity validation
- `network_block` - Blocked network requests

---

## 🔌 API Integration

### Endpoints Used

All endpoints are from `/api/sovereign-mode/*`:

| Endpoint | Method | Hook | Purpose |
|----------|--------|------|---------|
| `/info` | GET | `useSovereignInfo()` | System information |
| `/status` | GET | `useSovereignStatus()` | Current status (10s refresh) |
| `/mode` | POST | `useModeChange()` | Change operation mode |
| `/bundles` | GET | `useBundles()` | List bundles |
| `/bundles/{id}` | GET | `useBundle()` | Bundle details |
| `/bundles/load` | POST | `useBundleLoad()` | Load bundle |
| `/bundles/{id}/validate` | POST | `useBundleValidate()` | Validate bundle |
| `/bundles/discover` | POST | `useBundleDiscover()` | Discover bundles |
| `/network/check` | GET | `useNetworkCheck()` | Check connectivity |
| `/config` | GET | `useSovereignConfig()` | Get configuration |
| `/config` | PUT | `useConfigUpdate()` | Update configuration |
| `/audit` | GET | `useAuditLog()` | Get audit entries |
| `/statistics` | GET | `useSovereignStatistics()` | Get statistics |

### Type Safety

All API calls are fully typed using TypeScript types defined in `src/types/sovereign.ts`:

```typescript
import type {
  SovereignMode,
  Bundle,
  BundleStatus,
  OperationMode,
  AuditEntry,
  // ... etc
} from "@/types/sovereign";
```

---

## 🎯 Usage Patterns

### Example 1: Switch to Sovereign Mode

```typescript
import { useModeChange } from "@/hooks/useSovereignMode";
import { OperationMode } from "@/types/sovereign";

function MyComponent() {
  const modeChangeMutation = useModeChange();

  const handleSwitch = () => {
    modeChangeMutation.mutate({
      target_mode: OperationMode.SOVEREIGN,
      reason: "Manual activation",
      force: false,
    });
  };

  return (
    <Button onClick={handleSwitch} disabled={modeChangeMutation.isPending}>
      Switch to Sovereign
    </Button>
  );
}
```

### Example 2: Load Bundle

```typescript
import { useBundleLoad } from "@/hooks/useSovereignMode";

function BundleLoadButton({ bundleId }: { bundleId: string }) {
  const loadMutation = useBundleLoad();

  const handleLoad = () => {
    loadMutation.mutate({
      bundle_id: bundleId,
      force_revalidate: true,
      skip_quarantine_check: false, // Safety first!
    });
  };

  return (
    <Button onClick={handleLoad} disabled={loadMutation.isPending}>
      {loadMutation.isPending ? "Loading..." : "Load Bundle"}
    </Button>
  );
}
```

### Example 3: Monitor Audit Log

```typescript
import { useAuditLog } from "@/hooks/useSovereignMode";

function AuditMonitor() {
  const { data: entries, isLoading, error } = useAuditLog(100, "mode_change");

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <ul>
      {entries?.map((entry) => (
        <li key={entry.id}>
          {entry.event_type} - {entry.success ? "✅" : "❌"}
        </li>
      ))}
    </ul>
  );
}
```

---

## 🔒 Security Considerations

### Fail-Closed Design

The system defaults to **blocking** all external access in offline modes:
- No accidental data exfiltration
- No external API calls
- No DNS leaks
- No network fingerprinting

### Hash Validation

All bundles must pass SHA256 validation:
- Model file hash verification
- Manifest file hash verification
- Automatic quarantine on failure

### Audit Trail

All operations are logged:
- Immutable (append-only)
- Timestamped
- Structured (JSON)
- Exportable

### Mode Change Confirmation

Mode switches require:
- 2-step confirmation dialog
- Optional reason input
- Preflight warnings for dangerous modes
- Audit logging

---

## 🎨 UI/UX Specifications

### Design System

- **Framework:** Next.js 14 (App Router)
- **UI Library:** shadcn/ui + Tailwind CSS
- **State Management:** TanStack React Query (server state) + Zustand (client state)
- **Icons:** lucide-react

### Color Coding

| Mode/Status | Color | Usage |
|-------------|-------|-------|
| Online | Emerald (`emerald-500`) | Success, validated, online |
| Offline | Amber (`amber-500`) | Warning, offline |
| Sovereign | Violet (`violet-500`) | Sovereign mode, special |
| Quarantine | Red (`red-500`) | Danger, quarantined, errors |

### State Handling

All pages implement comprehensive state handling:

- **Loading States:** Skeleton loaders and spinners
- **Error States:** Alert components with error messages
- **Empty States:** Placeholder UI with actionable guidance
- **Retry Buttons:** User-initiated refetch capabilities

### Responsive Design

- Mobile-first approach
- Grid layouts with responsive breakpoints
- Collapsible sidebar
- Touch-friendly buttons (min 44x44px)

---

## 📦 Dependencies

### New Dependencies

```json
{
  "@radix-ui/react-select": "^2.1.2" // Select dropdown component
}
```

### Existing Dependencies

- `@tanstack/react-query`: Server state management
- `lucide-react`: Icon library
- `tailwindcss`: Utility-first CSS
- `shadcn/ui`: UI component primitives

---

## 🚀 Development Workflow

### Running Locally

```bash
# Start backend (if not already running)
cd backend
docker compose up -d

# Start frontend
cd frontend/brain_control_ui
npm install
npm run dev
```

Navigate to: **http://localhost:3000/admin/sovereign**

### Building

```bash
cd frontend/brain_control_ui
npm run build
npm run start
```

### Type Checking

```bash
npm run type-check
```

---

## 🧪 Testing

### Manual Testing Checklist

#### Sovereign Mode Page
- [ ] Page loads without errors
- [ ] KPIs display correctly
- [ ] Mode switch buttons are interactive
- [ ] Confirmation dialog appears on mode switch
- [ ] Mode change success updates UI
- [ ] Quarantine warnings display when applicable

#### Bundles Page
- [ ] Bundles list loads
- [ ] Search filtering works
- [ ] Discover button scans for bundles
- [ ] Validate button verifies hashes
- [ ] Load button activates bundle
- [ ] Quarantine removal prompts confirmation
- [ ] Statistics cards update

#### Network Page
- [ ] Network status displays correctly
- [ ] Network guards show configuration
- [ ] Auto-detection settings visible
- [ ] Refresh button updates data
- [ ] Latest check details display

#### Audit Log Page
- [ ] Audit entries load
- [ ] Event type filter works
- [ ] Entry limit selector functions
- [ ] Expandable rows show details
- [ ] Export to JSON downloads file
- [ ] Statistics cards calculate correctly

---

## 📝 API Testing

Use the backend directly:

```bash
# Get sovereign status
curl http://localhost:8000/api/sovereign-mode/status

# List bundles
curl http://localhost:8000/api/sovereign-mode/bundles

# Change mode
curl -X POST http://localhost:8000/api/sovereign-mode/mode \
  -H "Content-Type: application/json" \
  -d '{"target_mode": "sovereign", "reason": "Test"}'

# Get audit log
curl http://localhost:8000/api/sovereign-mode/audit?limit=50
```

---

## 🔧 Troubleshooting

### Issue: Pages not loading

**Solution:**
1. Check backend is running: `docker compose ps`
2. Verify API endpoint: `curl http://localhost:8000/api/sovereign-mode/status`
3. Check browser console for errors
4. Ensure environment variable is set: `NEXT_PUBLIC_BRAIN_API_BASE=http://localhost:8000`

### Issue: Types not found

**Solution:**
```bash
# Rebuild TypeScript
npm run type-check

# Restart dev server
npm run dev
```

### Issue: Select component not rendering

**Solution:**
1. Verify `@radix-ui/react-select` is installed
2. Check import paths in `/admin/audit/page.tsx`
3. Ensure `select.tsx` component exists in `src/components/ui/`

### Issue: Sidebar not showing Admin section

**Solution:**
1. Verify imports in `app-sidebar.tsx`:
   ```typescript
   import { Shield, Package, Globe, ScrollText } from "lucide-react";
   ```
2. Check `adminNav` array is defined
3. Ensure Admin section JSX is present

---

## 🔄 Future Enhancements

### Planned Features

- [ ] Real-time WebSocket updates for audit log
- [ ] Bundle comparison and diff viewer
- [ ] Network traffic visualization
- [ ] Configuration import/export
- [ ] Batch bundle operations
- [ ] Advanced audit log filtering (date range, user, etc.)
- [ ] Bundle version management UI
- [ ] Digital signature verification UI

### Integration Opportunities

- [ ] Policy Engine integration for permission checks
- [ ] Threats Module integration for security violations
- [ ] Foundation Layer safety checks

---

## 📚 Related Documentation

- [Backend Sovereign Mode README](../../backend/app/modules/sovereign_mode/README.md)
- [CLAUDE.md - Project Guide](../../CLAUDE.md)
- [shadcn/ui Docs](https://ui.shadcn.com/)
- [TanStack Query Docs](https://tanstack.com/query/latest)

---

## 👥 Contributors

- **Olaf Falk** - Initial implementation
- **Claude** - AI Assistant (Development)

---

## 📄 License

Part of BRAiN Framework - See main LICENSE file

---

## 🆘 Support

For issues or questions:
- Check frontend console: Browser DevTools → Console
- Check backend logs: `docker compose logs backend | grep sovereign`
- Review audit log: Navigate to `/admin/audit`
- Report issues: GitHub Issues

---

**Last Updated:** 2025-12-24
**Module Version:** 1.0.0
**Status:** ✅ Production Ready
