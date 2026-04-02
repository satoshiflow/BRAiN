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
  "external-operations.paperclip-governance": {
    key: "external-operations.paperclip-governance",
    title: "External Ops & Paperclip Governance",
    summary: "Erklärt Handoffs, bounded Actions, Retry-Requests und die Rolle von ControlDeck in External Operations.",
    whyItMatters: "Externe Executor bleiben steuerbar, wenn Operatoren klar zwischen Sichtbarkeit, Request und genehmigter Materialisierung unterscheiden.",
    examples: [
      "Öffne einen Task in Paperclip, ohne Governance aus BRAiN herauszulösen.",
      "Genehmige einen Retry-Request und prüfe danach die neue SkillRun- und TaskLease-Kette.",
    ],
    useCases: ["External Executor Governance", "Paperclip Handoffs", "Retry Review"],
    docPath: "/help/external-operations.paperclip-governance",
    surface: "controldeck-v3",
  },
  "external-operations.supervisor-handoffs": {
    key: "external-operations.supervisor-handoffs",
    title: "Supervisor Handoffs aus External Ops",
    summary: "Zeigt, wie genehmigte Eskalationen aus Paperclip in echte Supervisor-Faelle uebergehen.",
    whyItMatters: "So bleibt nachvollziehbar, wann eine External-Ops-Anfrage nur reviewt wurde und wann sie in den Supervisor-Workflow materialisiert wurde.",
    examples: [
      "Pruefe in der Timeline die supervisor_escalation_id nach einer genehmigten Eskalation.",
      "Springe aus External Operations direkt in die Supervisor-Inbox fuer Paperclip-Faelle.",
    ],
    useCases: ["Escalation Review", "Supervisor Routing", "Cross-Surface Auditability"],
    docPath: "/help/external-operations.supervisor-handoffs",
    surface: "controldeck-v3",
  },
  "supervisor.inbox": {
    key: "supervisor.inbox",
    title: "Supervisor Inbox",
    summary: "Listet Domain-Eskalationen zur operativen Pruefung, Filterung und Entscheidung in ControlDeck auf.",
    whyItMatters: "Die Inbox ist der Ort, an dem aus Requests konkrete supervisor-seitige Bearbeitung wird.",
    examples: [
      "Filtere auf Paperclip-Faelle ueber den scope-Parameter.",
      "Oeffne eine Eskalation und setze sie auf in_review, bevor du final entscheidest.",
    ],
    useCases: ["Supervisor Triage", "Escalation Intake", "Operator Review"],
    docPath: "/help/supervisor.inbox",
    surface: "controldeck-v3",
  },
  "supervisor.decisions": {
    key: "supervisor.decisions",
    title: "Supervisor Decisions",
    summary: "Beschreibt den Entscheidungsfluss fuer einzelne Eskalationen inklusive Statuswechsel und Notizen.",
    whyItMatters: "Saubere Statusuebergaenge und begruendete Entscheidungen machen Supervisor-Governance auditierbar und spaeter auswertbar.",
    examples: [
      "Markiere einen Fall zuerst als in_review, wenn noch Kontext fehlt.",
      "Nutze approved oder denied erst, wenn der Grund fuer die Entscheidung dokumentiert ist.",
    ],
    useCases: ["Escalation Decisioning", "Supervisor Audit", "Governed Review"],
    docPath: "/help/supervisor.decisions",
    surface: "controldeck-v3",
  },
};

export function getControlDeckHelpTopic(topicKey: string): HelpTopic | null {
  return CONTROLDECK_HELP_TOPICS[topicKey] || null;
}
