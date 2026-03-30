export type HelpTopic = {
  key: string;
  title: string;
  summary: string;
  whyItMatters: string;
  examples: string[];
  useCases: string[];
  docPath: string;
  surface: "controldeck-v3" | "axe-ui" | "shared";
};

export const CONTROLDECK_HELP_TOPICS: Record<string, HelpTopic> = {
  "skills.catalog": {
    key: "skills.catalog",
    title: "Skills-Katalog",
    summary: "Zeigt alle registrierten Skills inklusive Status, Risiko und Ausführbarkeit.",
    whyItMatters: "Der Katalog ist die zentrale Stelle, um Skills zu entdecken, zu prüfen und kontrolliert auszuführen.",
    examples: [
      "Filtere nach risk_tier, um nur low-risk Skills im Betrieb anzuzeigen.",
      "Öffne Skill-Details und starte einen Run direkt mit einem Test-Input.",
    ],
    useCases: ["Skill Governance", "Run Triggering", "Catalog Review"],
    docPath: "/help/skills.catalog",
    surface: "controldeck-v3",
  },
  "knowledge.explorer": {
    key: "knowledge.explorer",
    title: "Knowledge Explorer",
    summary: "Ermöglicht Hybrid-Suche über Metadaten und semantische Inhalte.",
    whyItMatters: "Wissen wird wiederverwendbar für Menschen und Skills statt in isolierten Notizen zu verbleiben.",
    examples: [
      "Suche mit Semantic aktiviert nach 'feature dev debugging'.",
      "Verknüpfe zwei Items, um Ursache-Wirkung transparent zu machen.",
    ],
    useCases: ["Runbook Retrieval", "Skill Context Enrichment", "Knowledge Curation"],
    docPath: "/help/knowledge.explorer",
    surface: "controldeck-v3",
  },
  "healing.actions": {
    key: "healing.actions",
    title: "Self-Healing Aktionen",
    summary: "Steuert manuelle Recovery-Entscheidungen wie Neu-Bewertung oder Eskalation.",
    whyItMatters: "Menschliche Eingriffe bleiben nachvollziehbar und fließen in die Governance-Historie ein.",
    examples: [
      "Nutze 'Neu bewerten' bei transienten Provider-Fehlern.",
      "Nutze 'Eskalieren' bei wiederkehrenden Critical Events.",
    ],
    useCases: ["Incident Triage", "Recovery Governance", "Stability Ops"],
    docPath: "/help/healing.actions",
    surface: "controldeck-v3",
  },
  "settings.appearance": {
    key: "settings.appearance",
    title: "Appearance & Runtime Settings",
    summary: "Steuert Theme, Live-Updates und lokale Runtime-Einstellungen.",
    whyItMatters: "Konsistente UX und Runtime-Parameter reduzieren Bedienfehler im Tagesbetrieb.",
    examples: [
      "Setze Theme auf system für automatische Anpassung.",
      "Deaktiviere Live-Updates bei Debugging von UI-Ständen.",
    ],
    useCases: ["Operator UX", "Live Monitoring Controls"],
    docPath: "/help/settings.appearance",
    surface: "controldeck-v3",
  },
};

export function getControlDeckHelpTopic(topicKey: string): HelpTopic | null {
  return CONTROLDECK_HELP_TOPICS[topicKey] || null;
}
