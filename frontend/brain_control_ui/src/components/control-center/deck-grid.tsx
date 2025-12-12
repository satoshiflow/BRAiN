import { DeckCard } from "./deck-card"

export function DeckGrid() {
  return (
    <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
      <DeckCard
        title="Control Deck"
        subtitle="Cluster · Services · Ressourcen"
        kpiLabel="STATUS"
        kpiValue="Online"
        meta="3 Cluster · 14 Services · 2 Wartungsfenster geplant"
        href="/control"
        accent="blue"
      />

      <DeckCard
        title="Mission Deck"
        subtitle="Planen · Ausführen · Überwachen"
        kpiLabel="MISSIONEN"
        kpiValue="12"
        meta="3 wartend · 4 heute abgeschlossen · 0 fehlgeschlagen"
        href="/missions"
        accent="gold"
      />

      <DeckCard
        title="Agenten Deck"
        subtitle="DNA · Rollen · Lebenszyklen"
        kpiLabel="AGENTEN"
        kpiValue="27"
        meta="24 aktiv · 2 im Self-Repair · 1 pausiert"
        href="/agents"
        accent="green"
      />

      <DeckCard
        title="Health Deck"
        subtitle="Uptime · Fehler · Resilienz"
        kpiLabel="HEALTH"
        kpiValue="98%"
        meta="Letzter Incident vor 3 Std · 0 offene Criticals"
        href="/health"
        accent="purple"
      />

      <DeckCard
        title="Settings"
        subtitle="Limits · API Keys · Sicherheit"
        kpiLabel="PROFILE"
        kpiValue="Config"
        meta="4 API-Keys · 3 Rollenprofile · 2 aktive Integrationen"
        href="/settings"
        accent="gold"
      />
    </section>
  )
}
