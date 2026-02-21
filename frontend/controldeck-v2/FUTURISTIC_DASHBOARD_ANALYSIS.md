# Futuristic Dashboard Analysis

**Template:** v0.app/templates/futuristic-dashboard-ZAyrQvYVCUs  
**Analyse:** Komponenten-Anordnung, Menüpunkte, Layout-Struktur  
**Datum:** 2026-02-21

---

## Layout-Struktur (Typisch für Futuristic Dashboards)

### Grid-System

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TOPBAR (Fixed)                                                          │
│  [Logo] [Search]                    [Alerts] [Theme] [User]             │
├──────────┬──────────────────────────────────────────────────────────────┤
│          │  KPI CARDS (4-6 in einer Row)                                │
│          │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                 │
│          │  │ Metric │ │ Metric │ │ Metric │ │ Metric │                 │
│          │  └────────┘ └────────┘ └────────┘ └────────┘                 │
│          │                                                                │
│  SIDEBAR │  MAIN CONTENT AREA                                             │
│  (Fixed) │  ┌────────────────────┬─────────────────────┐                │
│          │  │                    │                     │                │
│  [Home]  │  │   CHART / GRAPH    │    STATUS PANEL     │                │
│  [Stats] │  │                    │                     │                │
│  [Data]  │  │  (Large, 60%)      │    (40%)            │                │
│  [Logs]  │  │                    │                     │                │
│  [...]   │  └────────────────────┴─────────────────────┘                │
│          │                                                                │
│          │  ┌──────────────────────────────────────────────────────┐    │
│          │  │           DATA TABLE / LIST                          │    │
│          │  │                                                      │    │
│          │  │   [Filter] [Search]                    [Actions]     │    │
│          │  │   ┌─────────────────────────────────────────────┐    │    │
│          │  │   │  Row 1                                      │    │    │
│          │  │   │  Row 2                                      │    │    │
│          │  │   │  Row 3                                      │    │    │
│          │  │   └─────────────────────────────────────────────┘    │    │
│          │  └──────────────────────────────────────────────────────┘    │
└──────────┴──────────────────────────────────────────────────────────────┘
```

---

## Komponenten-Anordnung

### 1. Top Section (KPI Cards)
- **Anzahl:** 4-6 Cards in einer horizontalen Row
- **Inhalt:**
  - Large Number (Value)
  - Label/Title
  - Trend-Indicator (Up/Down Arrow + %)
  - Mini-Chart (Sparkline) - Optional
  - Icon (links oder rechts)
- **Styling:**
  - Gleiche Höhe
  - Consistent Padding
  - Subtle Border oder Shadow
  - Accent-Farbe für Icons/Numbers

### 2. Middle Section (Split View)
- **Links (60-70%):**
  - Large Chart (Line, Area, oder Bar)
  - ODER: Main Content Panel
  - ODER: Map/Visualization
  
- **Rechts (30-40%):**
  - Status Panel
  - Activity Feed
  - Mini-Stats
  - Quick Actions

### 3. Bottom Section (Data Table)
- **Volle Breite**
- **Inhalt:**
  - Filter-Bar oben
  - Search Input
  - Sortable Columns
  - Action Buttons per Row
  - Pagination oder Infinite Scroll

---

## Menüpunkte-Struktur (Sidebar)

### Typische Navigation

```
Overview
├── Dashboard        (Home icon)
├── Analytics        (BarChart icon)
└── Reports          (FileText icon)

Operations
├── Missions         (Target icon)
├── Agents           (Bot icon)
├── Workflows        (GitBranch icon)
└── Events           (Radio icon)

Data
├── Logs             (ScrollText icon)
├── Metrics          (Activity icon)
└── Exports          (Download icon)

System
├── Health           (HeartPulse icon)
├── Settings         (Settings icon)
└── Help             (HelpCircle icon)
```

### Sidebar Features

1. **Collapsible**
   - Expanded: 240-280px
   - Collapsed: 64-80px (nur Icons)

2. **Active State**
   - Left Border Accent (2-4px)
   - Background Highlight
   - Icon Color Change

3. **Grouping**
   - Section Headers (Uppercase, Small, Muted)
   - Divider zwischen Groups

4. **Bottom Section**
   - User Profile
   - Logout
   - Theme Toggle

---

## Modal/Dialog Patterns

### Modal Types

1. **Slide-over Drawer (Rechts)**
   - Für Detail-Ansichten
   - Formulare
   - Settings
   - Width: 400-600px
   - Backdrop: Semi-transparent dark

2. **Center Modal (Dialog)**
   - Für Bestätigungen
   - Alerts
   - Quick Forms
   - Width: 400-500px
   - Centered vertically & horizontally

3. **Bottom Sheet (Mobile)**
   - Für Mobile View
   - Slides up from bottom
   - Full-width on mobile

### Modal Styling

```
┌─────────────────────────────────────────────┐
│  ┌─────────────────────────────────────┐    │
│  │  [X] Title                    │    │    │
│  ├─────────────────────────────────────┤    │
│  │                                     │    │
│  │  Content Area                       │    │
│  │  - Forms                            │    │
│  │  - Details                          │    │
│  │  - Confirmations                    │    │
│  │                                     │    │
│  ├─────────────────────────────────────┤    │
│  │  [Cancel]              [Confirm]    │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
       ↑ Backdrop (bg-black/50)
```

### Animationen

1. **Backdrop Fade**
   - Duration: 200ms
   - Easing: ease-out

2. **Modal Slide/Scale**
   - Drawer: Slide from right (300ms)
   - Center Modal: Scale from 0.95 + Fade (200ms)
   - Bottom Sheet: Slide from bottom (300ms)

3. **Close**
   - Reverse animations
   - Click outside to close
   - ESC key to close

---

## Farb-Palette (Futuristic/Cyberpunk)

### Dark Mode (Primary)

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Background | Deep Navy | #0F172A | Main bg |
| Surface | Dark Slate | #1E293B | Cards, Panels |
| Elevated | Darker | #0B1220 | Modals, Drawers |
| Border | Slate | #334155 | Dividers, Borders |
| Text Primary | Light Gray | #E5E7EB | Headings |
| Text Secondary | Gray | #9CA3AF | Body text |
| Accent | Gold/Amber | #C9A227 | Primary buttons |
| Success | Green | #10B981 | Success states |
| Warning | Yellow | #F59E0B | Warnings |
| Danger | Red | #EF4444 | Errors |
| Info | Blue | #3B82F6 | Info states |

### Accent Variations (Cyberpunk)

- **Neon Cyan:** #00F0FF (Alternative Accent)
- **Neon Pink:** #FF0080 (Highlights)
- **Neon Purple:** #8B5CF6 (Secondary)

---

## Typography

### Font Stack
- **Primary:** Inter, Geist Sans, or System
- **Monospace:** JetBrains Mono, Geist Mono (für Code/Logs)

### Hierarchy

| Element | Size | Weight | Usage |
|---------|------|--------|-------|
| H1 | 24-32px | 600 | Page Titles |
| H2 | 18-22px | 600 | Section Headers |
| H3 | 16-18px | 500 | Card Titles |
| Body | 14px | 400 | Normal Text |
| Small | 12-13px | 400 | Labels, Meta |
| Mono | 13-14px | 400 | Code, Timestamps |

---

## Interaktionen & Feedback

### Hover States
- **Cards:** Subtle lift (translateY -2px) + Shadow increase
- **Buttons:** Brightness increase + Scale 1.02
- **Table Rows:** Background highlight
- **Links:** Color change + Underline

### Focus States
- **Ring:** 2px offset, Accent color
- **Outline:** Never remove focus-visible!

### Loading States
- **Skeleton:** Shimmer animation
- **Spinners:** Rotate animation (nicht überall - nur bei Actions)
- **Progress:** Linear oder Circular

---

## Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Single column, Sidebar becomes Sheet |
| Tablet | 640-1024px | 2 columns, Collapsible Sidebar |
| Desktop | 1024-1280px | Full layout, Expanded Sidebar |
| Large | > 1280px | Full layout, More spacing |

---

## Empfohlene Implementierung für BRAiN

### 1. Layout-Komponenten erstellen

```tsx
// Layout primitives
<DashboardLayout>
  <Topbar />
  <Sidebar />
  <MainContent>
    <KpiGrid cols={4}>
      <KpiCard />
      <KpiCard />
      <KpiCard />
      <KpiCard />
    </KpiGrid>
    
    <SplitLayout left={60} right={40}>
      <ChartPanel />
      <StatusPanel />
    </SplitLayout>
    
    <DataTable />
  </MainContent>
</DashboardLayout>
```

### 2. Modal System

```tsx
// Modal primitives
<ModalProvider>
  <Drawer position="right" width={480}>
    <MissionDetail />
  </Drawer>
  
  <Dialog>
    <ConfirmAction />
  </Dialog>
</ModalProvider>
```

### 3. Navigation-Struktur

```tsx
const navStructure = [
  {
    group: "Overview",
    items: [
      { label: "Dashboard", href: "/", icon: Home },
      { label: "Analytics", href: "/analytics", icon: BarChart },
    ]
  },
  {
    group: "Operations",
    items: [
      { label: "Missions", href: "/missions", icon: Target },
      { label: "Agents", href: "/agents", icon: Bot },
      { label: "Events", href: "/events", icon: Radio },
    ]
  },
  // ...
];
```

---

## Zusammenfassung

**Key Takeaways:**
1. **Klare Hierarchie:** KPIs → Charts → Tables
2. **Konsistente Abstände:** 8px Grid-System
3. **Farb-Disziplin:** Dark Base + Ein Accent
4. **Typography:** Clear hierarchy, readable sizes
5. **Interaktionen:** Subtle but clear feedback
6. **Responsiveness:** Mobile-first, Sidebar als Sheet
7. **Modals:** Slide-over für Details, Center für Alerts

**Für BRAiN ControlDeck v2:**
- ✅ Bereits implementiert: Sidebar, Topbar, KPI Cards
- 🔄 Als nächstes: Modal/Drawer System
- 🔄 Dann: Data Table Komponente
- 🔄 Schließlich: Animations & Transitions
