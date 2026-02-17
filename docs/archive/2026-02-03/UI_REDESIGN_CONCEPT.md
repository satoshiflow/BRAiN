# UI Redesign Konzept: Control Deck + AXE UI

**Version:** 1.0.0
**Date:** 2026-01-10
**Status:** Design Phase
**Target:** Mobile-first, Modern, Accessible

---

## 🎯 Projekt-Übersicht

### Ziele

1. **Mobile-First:** Responsive Design für alle Bildschirmgrößen
2. **Modern:** Zeitgemäßes, clean Design mit shadcn/ui
3. **Accessible:** WCAG 2.1 Level AA Compliance
4. **Performant:** Optimierte Loading-Zeiten und Interaktionen
5. **Consistent:** Einheitliches Design-System für alle Frontend-Apps

---

## 📊 Aktuelle Situation

### Control Deck
**Pages:** 20+ Pages
- Dashboard, Health, Settings
- NeuroRail (7 Sub-Pages): Trace Explorer, Health Matrix, Budget, Reflex, Lifecycle, Trace, Overview
- WebGenesis (3 Sub-Pages): Overview, New Site, Site Details
- Supervisor, Immune, Login

**Components:** 80 Components
- 50+ shadcn/ui Components bereits installiert
- Custom Components für spezifische Features

**Tech Stack:**
- Next.js 14.2.33 (App Router)
- React 18
- Tailwind CSS 3.4+
- shadcn/ui (Radix UI Primitives)
- TanStack React Query
- Zustand

**Status:** ⚠️ Funktional aber nicht mobil-optimiert

### AXE UI
**Pages:** 5 Pages
- Root, Dashboard, Chat, Agents, Settings

**Components:** 1 Component (minimal)

**Purpose:** Floating widget für externe Projekte

**Tech Stack:** Gleich wie Control Deck

**Status:** ⚠️ Grundstruktur vorhanden, braucht vollständiges Design

---

## 🎨 Design System

### Farb-Palette

**Primary (Brand):**
```css
--brain-primary: 220 70% 50%      /* Blau */
--brain-primary-hover: 220 70% 45%
--brain-primary-active: 220 70% 40%
```

**Semantic Colors:**
```css
--success: 142 76% 36%   /* Grün */
--warning: 38 92% 50%    /* Orange */
--error: 0 72% 51%       /* Rot */
--info: 199 89% 48%      /* Cyan */
```

**Neutral Palette (Dark Mode):**
```css
--background: 224 71% 4%          /* Fast schwarz */
--foreground: 213 31% 91%         /* Hellgrau */
--card: 224 71% 5%
--card-foreground: 213 31% 91%
--muted: 223 47% 11%
--muted-foreground: 215.4 16.3% 56.9%
--border: 216 34% 17%
--input: 216 34% 17%
```

**Neutral Palette (Light Mode):**
```css
--background: 0 0% 100%           /* Weiß */
--foreground: 224 71% 4%          /* Dunkelgrau */
--card: 0 0% 100%
--card-foreground: 224 71% 4%
--muted: 220 14.3% 95.9%
--muted-foreground: 220 8.9% 46.1%
--border: 220 13% 91%
--input: 220 13% 91%
```

### Typography

**Font Families:**
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

**Scale:**
```css
--text-xs: 0.75rem     /* 12px */
--text-sm: 0.875rem    /* 14px */
--text-base: 1rem      /* 16px */
--text-lg: 1.125rem    /* 18px */
--text-xl: 1.25rem     /* 20px */
--text-2xl: 1.5rem     /* 24px */
--text-3xl: 1.875rem   /* 30px */
--text-4xl: 2.25rem    /* 36px */
```

**Line Heights:**
```css
--leading-tight: 1.25
--leading-normal: 1.5
--leading-relaxed: 1.75
```

### Spacing

**Scale (Tailwind):**
```
0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64
```

**Common Patterns:**
- Padding: `p-4`, `p-6`, `px-6 py-4`
- Gap: `gap-4`, `gap-6`, `gap-8`
- Margin: `mb-4`, `mt-6`, `mx-auto`

### Shadows

```css
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
```

### Border Radius

```css
--radius-sm: 0.25rem    /* 4px */
--radius: 0.5rem        /* 8px */
--radius-md: 0.75rem    /* 12px */
--radius-lg: 1rem       /* 16px */
--radius-full: 9999px   /* Vollständig rund */
```

### Animations

```css
--transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1)
--transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1)
--transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1)
```

---

## 📱 Mobile-First Layout

### Breakpoints

```css
/* Mobile (Default) */
/* min-width: 0px */

/* Tablet */
@media (min-width: 640px) { /* sm */ }
@media (min-width: 768px) { /* md */ }

/* Desktop */
@media (min-width: 1024px) { /* lg */ }
@media (min-width: 1280px) { /* xl */ }
@media (min-width: 1536px) { /* 2xl */ }
```

### Layout Patterns

#### 1. Sidebar Navigation (Control Deck)

**Mobile (< 768px):**
```
┌─────────────────┐
│ [≡] Header      │
├─────────────────┤
│                 │
│ Main Content    │
│                 │
└─────────────────┘

Bottom Sheet Navigation
```

**Desktop (≥ 768px):**
```
┌────┬─────────────────┐
│    │ Header          │
│ S  ├─────────────────┤
│ i  │                 │
│ d  │ Main Content    │
│ e  │                 │
│    │                 │
└────┴─────────────────┘
```

#### 2. Floating Widget (AXE UI)

**Mobile (< 768px):**
```
┌─────────────────┐
│                 │
│                 │
│                 │
│                 │
│            [💬] │ <- Fixed bottom-right
└─────────────────┘

On click → Full screen overlay
```

**Desktop (≥ 768px):**
```
┌─────────────────────┐
│                     │
│                     │
│            ┌───────┐│
│            │ Chat  ││ <- Floating panel
│            │       ││    400px x 600px
│            └───────┘│
└─────────────────────┘
```

### Responsive Components

#### Cards
```tsx
<div className="
  grid
  grid-cols-1
  sm:grid-cols-2
  lg:grid-cols-3
  gap-4
  lg:gap-6
">
  <Card>...</Card>
</div>
```

#### Typography
```tsx
<h1 className="
  text-2xl
  sm:text-3xl
  lg:text-4xl
  font-bold
">
  Title
</h1>
```

#### Spacing
```tsx
<div className="
  p-4
  sm:p-6
  lg:p-8
">
  Content
</div>
```

---

## 🧩 Component Library

### Core Components (shadcn/ui)

**Already Installed (✅):**
- Accordion
- Alert Dialog
- Avatar
- Badge
- Button
- Card
- Collapsible
- Dialog
- Dropdown Menu
- Hover Card
- Input
- Label
- Progress
- Select
- Sidebar
- Tabs
- Toast

**To Add (📋):**
- Command (⌘K search)
- Popover
- Sheet (mobile sidebar)
- Skeleton (loading states)
- Switch
- Tooltip

### Custom Components

#### 1. Mobile Navigation (Sheet)
```tsx
"use client"

import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Menu } from "lucide-react"

export function MobileNav() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[280px]">
        <Navigation />
      </SheetContent>
    </Sheet>
  )
}
```

#### 2. Responsive Data Table
```tsx
export function DataTable({ data }) {
  return (
    <div className="overflow-x-auto">
      {/* Mobile: Cards */}
      <div className="md:hidden space-y-4">
        {data.map(item => (
          <Card key={item.id}>
            <CardContent className="grid grid-cols-2 gap-2 p-4">
              <div>
                <Label>Name</Label>
                <p>{item.name}</p>
              </div>
              <div>
                <Label>Status</Label>
                <Badge>{item.status}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Desktop: Table */}
      <table className="hidden md:table w-full">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.map(item => (
            <tr key={item.id}>
              <td>{item.name}</td>
              <td><Badge>{item.status}</Badge></td>
              <td><Button>Edit</Button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

#### 3. Status Badge
```tsx
interface StatusBadgeProps {
  status: "success" | "warning" | "error" | "info"
  children: React.ReactNode
}

export function StatusBadge({ status, children }: StatusBadgeProps) {
  const variants = {
    success: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
    warning: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
    error: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
    info: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",
  }

  return (
    <Badge className={variants[status]}>
      {children}
    </Badge>
  )
}
```

#### 4. Metric Card
```tsx
export function MetricCard({ title, value, trend, icon: Icon }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && (
          <p className="text-xs text-muted-foreground mt-1">
            {trend}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

---

## ♿ Accessibility (WCAG 2.1 Level AA)

### Prinzipien

1. **Perceivable:** Informationen müssen wahrnehmbar sein
2. **Operable:** UI-Komponenten müssen bedienbar sein
3. **Understandable:** Informationen und Bedienung müssen verständlich sein
4. **Robust:** Inhalt muss von verschiedenen Technologien interpretiert werden können

### Implementierung

#### 1. Semantic HTML
```tsx
// ✅ GOOD
<nav aria-label="Main navigation">
  <ul>
    <li><a href="/dashboard">Dashboard</a></li>
  </ul>
</nav>

// ❌ BAD
<div className="nav">
  <div className="nav-item" onClick={() => router.push('/dashboard')}>
    Dashboard
  </div>
</div>
```

#### 2. Keyboard Navigation
```tsx
// Alle interaktiven Elemente müssen keyboard-accessible sein
<button
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick()
    }
  }}
>
  Action
</button>

// Fokus-Indikatoren
<Button className="focus:ring-2 focus:ring-primary focus:ring-offset-2">
  Click me
</Button>
```

#### 3. ARIA Labels
```tsx
// Icons ohne Text
<Button variant="ghost" size="icon" aria-label="Open menu">
  <Menu className="h-5 w-5" />
</Button>

// Status Updates
<div role="status" aria-live="polite">
  {loading ? "Loading..." : "Data loaded"}
</div>

// Error Messages
<div role="alert" aria-live="assertive">
  {error && <p>{error.message}</p>}
</div>
```

#### 4. Color Contrast

**Minimum Ratios (WCAG AA):**
- Normal Text: 4.5:1
- Large Text (18pt+): 3:1
- UI Components: 3:1

**Tools:**
- Chrome DevTools Lighthouse
- WAVE Browser Extension
- axe DevTools

#### 5. Focus Management
```tsx
import { useRef, useEffect } from 'react'

export function Modal({ isOpen, onClose }) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (isOpen) {
      // Focus first interactive element when modal opens
      closeButtonRef.current?.focus()
    }
  }, [isOpen])

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Modal Title</DialogTitle>
        </DialogHeader>
        <DialogFooter>
          <Button ref={closeButtonRef} onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

#### 6. Alternative Text
```tsx
// Images
<img
  src="/dashboard.png"
  alt="BRAiN Dashboard showing 5 active missions"
/>

// Decorative images
<img
  src="/pattern.svg"
  alt=""
  role="presentation"
/>
```

---

## 🎨 Control Deck Redesign

### Dashboard Page

**Desktop Layout:**
```
┌────────────────────────────────────────┐
│ [≡] BRAiN Control Deck    [@user] [⚙] │ <- Header
├────────────────────────────────────────┤
│                                        │
│ ┌──────────┐ ┌──────────┐ ┌─────────┐│
│ │ Active   │ │ Missions │ │ Agents  ││ <- Metrics (3 cols)
│ │ Agents   │ │ Queued   │ │ Online  ││
│ │   12     │ │    8     │ │   15    ││
│ └──────────┘ └──────────┘ └─────────┘│
│                                        │
│ ┌──────────────────────────────────┐  │
│ │ Recent Activity                  │  │ <- Activity Feed
│ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │
│ │ • Mission #123 completed         │  │
│ │ • Agent "Coder" started task     │  │
│ │ • NeuroRail trace created        │  │
│ └──────────────────────────────────┘  │
│                                        │
│ ┌─────────────┐ ┌──────────────────┐  │
│ │ System      │ │ Quick Actions    │  │ <- 2 column grid
│ │ Health      │ │ • New Mission    │  │
│ │ ✅ All OK   │ │ • View Logs      │  │
│ └─────────────┘ └──────────────────┘  │
└────────────────────────────────────────┘
```

**Mobile Layout:**
```
┌──────────────┐
│ [≡] BRAiN    │ <- Compact header
├──────────────┤
│ ┌──────────┐ │
│ │ Active   │ │ <- Metrics (stacked)
│ │ Agents:12│ │
│ └──────────┘ │
│ ┌──────────┐ │
│ │ Missions │ │
│ │ Queued:8 │ │
│ └──────────┘ │
│ ┌──────────┐ │
│ │ Recent   │ │ <- Compact activity
│ │ Activity │ │
│ │ ──────── │ │
│ │ • M #123 │ │
│ └──────────┘ │
└──────────────┘
```

### NeuroRail Trace Explorer

**Features:**
- Hierarchical tree view (mission → plan → job → attempt)
- Timeline visualization
- Filter by status, time range, entity type
- Search by ID
- Export to JSON/CSV

**Mobile Adaptations:**
- Collapsible tree nodes
- Swipe to reveal actions
- Bottom sheet for filters

---

## 🤖 AXE UI Redesign

### Floating Widget States

**1. Minimized (Default):**
```
┌──────────────────┐
│                  │
│                  │
│             [💬] │ <- Fixed bottom-right
└──────────────────┘
   Floating button (48x48px)
```

**2. Expanded (Chat Open):**

**Desktop:**
```
┌──────────────────┐
│            ┌────┐│
│            │Chat││ <- 400x600px panel
│            │[x] ││
│            │────││
│            │    ││
│            │    ││
│            │────││
│            │[→] ││
│            └────┘│
└──────────────────┘
```

**Mobile:**
```
Full screen overlay
┌──────────────┐
│ [←] AXE Chat │ <- Header with back
├──────────────┤
│              │
│ Chat         │ <- Full screen chat
│ Messages     │
│              │
├──────────────┤
│ [Type...]    │ <- Input at bottom
└──────────────┘
```

### Chat Interface

**Components:**
- Message bubbles (user vs AI)
- Typing indicator
- Quick actions (buttons)
- Code syntax highlighting
- File attachments
- Context panel (shows current page/data)

**Features:**
- Auto-scroll to latest message
- Message timestamps
- Error handling
- Retry failed messages
- Clear conversation

---

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Week 1)
**Ziel:** Design System Setup

- [ ] Create global CSS variables (colors, spacing, typography)
- [ ] Add missing shadcn/ui components (Command, Sheet, Skeleton)
- [ ] Setup dark mode toggle
- [ ] Create base layout templates
- [ ] Accessibility testing setup (axe DevTools)

**Deliverables:**
- `globals.css` with design tokens
- Component library documentation
- Dark mode working

---

### Phase 2: Control Deck Mobile (Week 2-3)
**Ziel:** Mobile-responsive Navigation & Dashboard

- [ ] Mobile sidebar (Sheet component)
- [ ] Responsive header with hamburger menu
- [ ] Dashboard page mobile layout
- [ ] Metric cards responsive grid
- [ ] Activity feed mobile optimization
- [ ] Test on real mobile devices

**Deliverables:**
- Mobile navigation working < 768px
- Dashboard fully responsive
- Accessibility audit passed

---

### Phase 3: Control Deck Pages (Week 4-5)
**Ziel:** All pages mobile-responsive

- [ ] NeuroRail pages mobile layouts
- [ ] WebGenesis pages responsive
- [ ] Supervisor page mobile
- [ ] Settings page mobile
- [ ] Data tables → mobile cards
- [ ] Forms mobile-optimized

**Deliverables:**
- All 20+ pages mobile-ready
- Consistent mobile UX

---

### Phase 4: AXE UI Complete Redesign (Week 6)
**Ziel:** Floating widget + mobile experience

- [ ] Floating button component
- [ ] Desktop: Draggable panel
- [ ] Mobile: Full screen overlay
- [ ] Chat interface responsive
- [ ] Quick actions mobile
- [ ] Context panel adaptive

**Deliverables:**
- AXE UI fully functional on all devices
- Smooth animations
- Accessibility compliant

---

### Phase 5: Polish & Testing (Week 7)
**Ziel:** Final refinements

- [ ] Performance optimization (lazy loading, code splitting)
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Cross-browser testing
- [ ] Mobile device testing
- [ ] User testing with real users
- [ ] Fix bugs and refinements

**Deliverables:**
- Lighthouse score > 90
- WCAG AA compliant
- All major browsers tested
- Bug-free release

---

## 📏 Success Metrics

### Performance
- [ ] Lighthouse Performance Score > 90
- [ ] First Contentful Paint < 1.5s
- [ ] Time to Interactive < 3s
- [ ] Cumulative Layout Shift < 0.1

### Accessibility
- [ ] WCAG 2.1 Level AA compliant
- [ ] Keyboard navigation 100% functional
- [ ] Screen reader compatible
- [ ] Color contrast ratios met

### Responsive
- [ ] Works on screens 320px - 2560px wide
- [ ] Touch-friendly (min 44x44px targets)
- [ ] No horizontal scrolling on mobile
- [ ] Text readable without zoom

### User Experience
- [ ] Intuitive navigation
- [ ] Fast perceived performance
- [ ] Consistent design language
- [ ] Clear visual hierarchy

---

## 🛠️ Tools & Resources

### Development
- **Next.js:** https://nextjs.org/docs
- **shadcn/ui:** https://ui.shadcn.com/
- **Tailwind CSS:** https://tailwindcss.com/docs
- **Radix UI:** https://www.radix-ui.com/

### Accessibility
- **axe DevTools:** https://www.deque.com/axe/devtools/
- **WAVE:** https://wave.webaim.org/
- **Lighthouse:** Chrome DevTools
- **WCAG Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/

### Testing
- **BrowserStack:** Cross-browser testing
- **Chrome DevTools:** Mobile emulation
- **Real Devices:** iPhone, Android testing

---

## 📋 Next Actions

**Immediate (Du entscheidest):**

1. **Review dieses Design-Konzept**
   - Feedback geben
   - Änderungen vorschlagen

2. **Priorität festlegen**
   - Welche Phase zuerst?
   - Control Deck oder AXE UI?

3. **Implementation starten**
   - Ich beginne mit Phase 1 (Foundation)
   - Oder direkt zu einer spezifischen Komponente

**Sag mir was du als nächstes willst!** 🚀

---

**Dokument erstellt:** 2026-01-10
**Version:** 1.0.0
**Status:** Bereit für Review & Implementation
