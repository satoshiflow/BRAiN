# Testing

ControlDeck v2 verwendet **Vitest** für Unit Tests und **Playwright** für E2E Tests.

## Unit Tests (Vitest)

### Ausführen

```bash
# Einmal ausführen
npm test

# Watch Mode
npm test -- --watch

# Mit Coverage
npm test -- --coverage
```

### Test-Struktur

```
packages/ui-core/src/components/
├── button.test.tsx
├── card.test.tsx
├── status-pill.test.tsx
├── kpi-card.test.tsx
└── ...

src/components/shell/
├── sidebar.test.tsx
├── topbar.test.tsx
└── page-layout.test.tsx

packages/ui-core/src/utils/
└── index.test.ts
```

### Was wird getestet

#### Components
- **Button:** Varianten (default, destructive, ghost), Disabled-State, Focus-Visible
- **Card:** Struktur, Styling, Rendering
- **StatusPill:** Alle Status (live, degraded, down, safe, idle), Pulse-Animation
- **KpiCard:** Werte, Delta-Indikatoren, Loading-State
- **Sidebar:** Navigation, Active-State, Gruppen
- **Topbar:** Titel, Subtitle, Actions
- **PageLayout:** PageContainer, PageHeader (ein h1), Grid

#### Utils
- **cn():** Class-Merging, Tailwind-Konflikte
- **formatDate():** Deutsche Datumsformatierung
- **formatRelativeTime():** Relative Zeit ("gerade eben", "5 Min.")
- **truncate():** String-Kürzung
- **generateId():** Eindeutige IDs

## E2E Tests (Playwright)

### Installation

```bash
npx playwright install
```

### Ausführen

```bash
# Alle Tests
npm run test:e2e

# Mit UI
npx playwright test --ui

# Nur Chrome
npx playwright test --project=chromium

# Debug
npx playwright test --debug
```

### Was wird getestet

- **Navigation:** Alle Menüpunkte funktionieren
- **Dashboard:** KPI Cards, Event Feed, Quick Actions sichtbar
- **Responsive:** Mobile Menü erscheint bei kleinen Screens
- **Seiten laden:** /missions, /events, /agents, /health, /settings

### Screenshots

Playwright macht automatisch Screenshots bei Fehlern:

```
test-results/
└── dashboard-navigation-fails/
    └── test-failed-1.png
```

## Test-Abdeckung Ziele

| Bereich | Ziel | Status |
|---------|------|--------|
| UI-Core Components | 90% | 🟡 In Progress |
| Shell Components | 80% | 🟡 In Progress |
| Utils | 100% | ✅ Done |
| Pages (E2E) | 70% | 🟡 In Progress |

## Best Practices

1. **Teste Verhalten, nicht Implementation**
   ```tsx
   // ✅ Gut
   expect(screen.getByRole('button')).toBeDisabled();
   
   // ❌ Schlecht
   expect(button).toHaveClass('disabled');
   ```

2. **Nutze data-testid sparsam**
   ```tsx
   // ✅ Vorzuziehen
   screen.getByRole('button', { name: 'Submit' });
   
   // ⚠️ Nur wenn nötig
   screen.getByTestId('submit-button');
   ```

3. **Ein h1 pro Page (Accessibility)**
   ```tsx
   const headings = screen.getAllByRole('heading', { level: 1 });
   expect(headings).toHaveLength(1);
   ```

4. **Teste alle Varianten**
   ```tsx
   it.each(['default', 'destructive', 'ghost'])('renders %s variant', (variant) => {
     render(<Button variant={variant}>{variant}</Button>);
   });
   ```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Unit Tests
  run: npm test -- --coverage

- name: Install Playwright
  run: npx playwright install --with-deps

- name: E2E Tests
  run: npm run test:e2e
```
