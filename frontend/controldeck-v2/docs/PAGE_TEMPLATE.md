# ControlDeck v2 - Page Template Guide

## Page Structure Template

Jede Seite im ControlDeck MUSS folgende Struktur haben:

```tsx
"use client"

import { DashboardLayout } from "@/components/shell/dashboard-layout";

export default function PageName() {
  return (
    <DashboardLayout
      title="Page Title"
      subtitle="Optional subtitle"
    >
      {/* Page Content Here */}
    </DashboardLayout>
  );
}
```

## DashboardLayout Component

Der `DashboardLayout` Component wrappt automatisch:
- ✅ Sidebar (Navigation)
- ✅ Topbar (Header mit Account-Menü)
- ✅ Main Content Area
- ✅ Mobile Responsiveness

### Props:

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `title` | string | ✅ | Page title in Topbar |
| `subtitle` | string | ❌ | Optional subtitle |
| `children` | ReactNode | ✅ | Page content |

## Full Example

```tsx
"use client"

import { useState } from "react";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@ui-core/components/card";

export default function ExamplePage() {
  const [data, setData] = useState([]);

  return (
    <DashboardLayout
      title="Example Page"
      subtitle="Manage your example data"
    >
      <div className="container mx-auto p-6">
        <Card>
          <CardHeader>
            <CardTitle>Content</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Your content */}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
```

## Common Mistakes

❌ **WRONG** - Missing DashboardLayout wrapper:
```tsx
export default function Page() {
  return (
    <div className="container mx-auto p-6">
      <h1>Title</h1>
      <p>Content</p>
    </div>
  );
}
```

✅ **CORRECT** - Using DashboardLayout:
```tsx
export default function Page() {
  return (
    <DashboardLayout title="Page Title" subtitle="Optional subtitle">
      <div className="container mx-auto p-6">
        {/* Content */}
      </div>
    </DashboardLayout>
  );
}
```

## Navigation Items

Routes are defined in `src/components/shell/sidebar.tsx`:

```tsx
const navItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Security", href: "/security", icon: Shield },
  { label: "Settings", href: "/settings", icon: Settings },
];
```

## API Integration Pattern

```tsx
const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de";

async function fetchData() {
  const res = await fetch(`${API_BASE}/api/endpoint`);
  return await res.json();
}
```

## File Structure

```
src/
├── app/
│   ├── page.tsx              # Dashboard
│   ├── layout.tsx            # Root layout
│   ├── security/
│   │   └── page.tsx          # Security settings
│   └── settings/
│       └── page.tsx          # General settings
├── components/
│   └── shell/
│       ├── dashboard-layout.tsx   # Main layout wrapper
│       ├── sidebar.tsx            # Navigation
│       └── topbar.tsx             # Header with account menu
└── docs/
    └── PAGE_TEMPLATE.md      # This file
```

---

**Created:** 2026-02-22  
**Version:** 1.0  
**Applies to:** All ControlDeck v2 pages
