# Frontend App Design Skill

**Based on:** BRAiN ControlDeck v2 Experience  
**Date:** 2026-02-21  
**Purpose:** Best practices for building enterprise frontend applications

---

## 1. Component Architecture

### File Structure
```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Page components
│   └── globals.css        # Global styles
├── components/
│   ├── shell/             # Layout components (Sidebar, Topbar)
│   └── features/          # Feature-specific components
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities, API clients
└── types/                 # TypeScript types
```

### Component Types
1. **Primitives** - Button, Card, Input (reusable, no business logic)
2. **Composite** - KpiCard, EventFeed (combine primitives)
3. **Shell** - Sidebar, Topbar, Layout (app structure)
4. **Features** - MissionList, EventStream (domain-specific)

---

## 2. Design System Rules

### Color Palette (Dark Theme)
```css
--background: #0F172A     /* Deep Navy - Main bg */
--card: #1E293B           /* Dark Slate - Cards */
--primary: #C9A227        /* Gold - Accent */
--border: #334155         /* Slate - Borders */
--success: #10B981
--warning: #F59E0B
--danger: #EF4444
--info: #3B82F6
```

### Layout Constraints
- **Max 4 KPI cards per row**
- **Max 2 charts per page**
- **Max 3 major panels per page**
- **Desktop-first responsive** (mobile = functional)

### Typography
- **Sans:** Inter or system-ui
- **Mono:** JetBrains Mono (for logs/code)
- **Hierarchy:** H1 (24-32px), H2 (18-22px), Body (14px)

---

## 3. Testing Best Practices

### E2E Testing with Playwright

#### Always Use Data-TestIDs
```typescript
// ❌ Bad - Brittle selectors
await page.getByText('Dashboard').click();
await page.locator('button').click();
await page.getByRole('link', { name: 'Events' }).click(); // Can match multiple!

// ✅ Good - Stable selectors
await page.getByTestId('nav-dashboard').click();
await page.getByTestId('submit-button').click();
await page.getByTestId('nav-events').click(); // Unique, reliable
```

#### Component TestID Convention
```typescript
// Navigation
<aside data-testid="sidebar-desktop">...</aside>
<a data-testid="nav-dashboard">...</a>
<a data-testid="nav-missions">...</a>
<a data-testid="nav-events">...</a>

// Forms
<button data-testid="submit-button">...</button>
<input data-testid="email-input" />
<form data-testid="login-form">...</form>

// Cards
<div data-testid="kpi-card-active-missions">...</div>
<div data-testid="kpi-card-system-health">...</div>
<div data-testid="event-feed">...</div>

// Quick Actions
<button data-testid="quick-action-new-mission">...</button>
<button data-testid="quick-action-agents">...</button>

// Tables
<table data-testid="missions-table">...</table>
<tr data-testid="mission-row-m-001">...</tr>

// Modals/Drawers
<div data-testid="modal-alert">...</div>
<div data-testid="drawer-mission-details">...</div>
```

#### TestID Naming Convention
```typescript
// Pattern: {component}-{context}-{identifier}
// Lowercase, kebab-case

// Navigation
nav-{name}              // nav-dashboard, nav-missions

// KPI Cards
kpi-card-{metric}       // kpi-card-active-missions

// Quick Actions
quick-action-{action}   // quick-action-new-mission

// Form Elements
{element}-{purpose}     // submit-button, email-input

// Tables
{entity}-table          // missions-table, events-table
{entity}-row-{id}       // mission-row-m-001

// Modals
modal-{type}            // modal-alert, modal-confirm
drawer-{purpose}        // drawer-mission-details
```

#### Wait for Network Idle
```typescript
test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
});
```

#### Handle API Loading
```typescript
test('displays data', async ({ page }) => {
  await page.waitForResponse(response => 
    response.url().includes('/api/missions')
  );
  await expect(page.getByTestId('mission-list')).toBeVisible();
});
```

### Unit Testing with Vitest

```typescript
import { render, screen } from '@testing-library/react';
import { Button } from './button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('handles click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    screen.getByRole('button').click();
    expect(handleClick).toHaveBeenCalled();
  });
});
```

---

## 4. API Integration

### TanStack Query Pattern
```typescript
// hooks/use-api.ts
export function useMissions(limit = 20) {
  return useQuery({
    queryKey: ['missions', 'queue', limit],
    queryFn: () => api.missions.getQueue(limit),
    refetchInterval: 5000, // Auto-refresh
  });
}
```

### Error Handling
```typescript
export function useDashboardData() {
  const { isLoading, isError, data, refetch } = useQuery({...});
  
  if (isError) {
    return {
      isError: true,
      errorComponent: <ErrorState onRetry={refetch} />
    };
  }
  
  return { data, isLoading };
}
```

---

## 5. Modal/Drawer System

### Dialog Pattern
```typescript
const { open, onOpen, onClose } = useModal();

<Dialog open={open} onOpenChange={onClose}>
  <DialogHeader>
    <DialogTitle>Confirm Action</DialogTitle>
  </DialogHeader>
  <DialogContent>Are you sure?</DialogContent>
  <DialogFooter>
    <Button variant="outline" onClick={onClose}>Cancel</Button>
    <Button onClick={handleConfirm}>Confirm</Button>
  </DialogFooter>
</Dialog>
```

### Drawer Pattern
```typescript
<Drawer open={open} onOpenChange={onClose} width={480}>
  <DrawerHeader onClose={onClose}>
    <DrawerTitle>Details</DrawerTitle>
  </DrawerHeader>
  <DrawerContent>
    {/* Content */}
  </DrawerContent>
</Drawer>
```

---

## 6. Responsive Design

### Breakpoints
```typescript
// Tailwind default breakpoints
sm: '640px'   // Mobile landscape
md: '768px'   // Tablet
lg: '1024px'  // Desktop
xl: '1280px'  // Large desktop
```

### Mobile-First Approach
```typescript
// Desktop sidebar, mobile sheet
<aside className="hidden lg:flex">...</aside>
<Sheet className="lg:hidden">...</Sheet>
```

---

## 7. Accessibility

### Required
- **Focus visible** never removed
- **Keyboard navigation** (Tab, Enter, Escape)
- **ARIA labels** for icons
- **Semantic HTML** (nav, main, aside)

### Example
```typescript
<button 
  aria-label="Close modal"
  className="focus-visible:ring-2 focus-visible:ring-ring"
>
  <XIcon />
</button>
```

---

## 8. Performance

### Optimization Rules
- **Virtualize** lists > 100 items
- **Lazy load** heavy components
- **Skeletons** > spinners
- **Image optimization** via Next.js

### Code Splitting
```typescript
const HeavyChart = dynamic(() => import('./heavy-chart'), {
  loading: () => <Skeleton className="h-64" />
});
```

---

## 9. Common Mistakes to Avoid

| Mistake | Solution |
|---------|----------|
| Hardcoded colors | Use design tokens |
| Missing loading states | Add skeletons |
| No error handling | Add error boundaries |
| Brittle E2E selectors | Use data-testid |
| No keyboard nav | Test Tab/Enter/Escape |
| Props drilling | Use context or composition |
| Too many re-renders | Use React.memo wisely |
| **Multiple elements with same text** | **Use data-testid or first()** |
| **Playwright strict mode violation** | **Add unique data-testids** |

### Strict Mode Violations in Playwright

**Problem:**
```
Error: strict mode violation: getByRole('link', { name: 'Events' }) 
resolved to 2 elements:
1) <a href="/events">Events</a>  // Navigation
2) <a href="/events">Events filtern</a>  // Quick Action
```

**Solutions:**

1. **Use data-testid (Recommended):**
```typescript
// Component
<a data-testid="nav-events" href="/events">Events</a>
<a data-testid="quick-action-events" href="/events">Events filtern</a>

// Test
await page.getByTestId('nav-events').click();
```

2. **Use first() as quick fix:**
```typescript
await page.getByRole('link', { name: 'Events' }).first().click();
```

3. **Use exact match:**
```typescript
await page.getByRole('link', { name: 'Events', exact: true }).click();
```

4. **Use locator with context:**
```typescript
await page.locator('aside', { hasText: 'Events' }).click();
```

**Best Practice:** Always use data-testid for elements that appear multiple times on a page.

---

## 10. Checklist for New Components

- [ ] Design tokens used (no hardcoded values)
- [ ] Loading state implemented
- [ ] Error state handled
- [ ] Keyboard accessible
- [ ] Focus visible working
- [ ] **data-testid added for all interactive elements**
- [ ] **Unique data-testid (no duplicates on same page)**
- [ ] Unit tests written
- [ ] E2E tests updated with data-testid selectors
- [ ] Responsive checked
- [ ] Accessibility verified

### Data-TestID Quick Reference

Add to interactive elements:
- Buttons: `data-testid="{action}-button"`
- Links: `data-testid="nav-{name}"` or `data-testid="link-{purpose}"`
- Inputs: `data-testid="{field}-input"`
- Cards: `data-testid="{type}-card-{identifier}"`
- Tables: `data-testid="{entity}-table"` and `data-testid="{entity}-row-{id}"`
- Modals: `data-testid="modal-{type}"`
- Drawers: `data-testid="drawer-{purpose}"`

**Example:**
```typescript
// Before
<button onClick={handleSubmit}>Save</button>

// After
<button data-testid="save-button" onClick={handleSubmit}>Save</button>
```

---

## Resources

- **Design System:** packages/ui-core/
- **Test Examples:** e2e/dashboard.spec.ts
- **Component Examples:** src/components/
- **API Patterns:** src/hooks/use-api.ts

---

**Remember:** Build for the user, test for reliability, document for the team.
