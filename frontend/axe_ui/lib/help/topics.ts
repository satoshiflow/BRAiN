export type HelpTopic = {
  key: string;
  title: string;
  summary: string;
  whyItMatters: string;
  examples: string[];
  useCases: string[];
  docPath: string;
  surface: "axe-ui" | "controldeck-v3" | "shared";
};

export const AXE_HELP_TOPICS: Record<string, HelpTopic> = {
  "axe.chat.intent": {
    key: "axe.chat.intent",
    title: "Intent Surface",
    summary: "Hier formulierst du Operator-Intents, die über SkillRun-Bridge ausgeführt werden.",
    whyItMatters: "Präzise Intents verbessern Routing, reduzieren Fehlentscheidungen und beschleunigen Delivery.",
    examples: [
      "'Implementiere Feature X mit TDD und liefere Testreport.'",
      "'Analysiere Produktionsfehler und starte strukturiertes Debugging.'",
    ],
    useCases: ["Feature Delivery", "Incident Handling", "Skill Orchestration"],
    docPath: "/help/axe.chat.intent",
    surface: "axe-ui",
  },
  "axe.health.indicator": {
    key: "axe.health.indicator",
    title: "API Health Indicator",
    summary: "Zeigt Erreichbarkeit und Fehlerstatus der Backend-API in Echtzeit.",
    whyItMatters: "Frühe Sichtbarkeit auf API-Probleme verhindert fehlerhafte Chat- oder Skill-Runs.",
    examples: [
      "Bei API error zuerst Backend/Token prüfen.",
      "Nutze den API-Link für direkte Health-Diagnose.",
    ],
    useCases: ["Runtime Diagnostics", "Operator Readiness"],
    docPath: "/help/axe.health.indicator",
    surface: "axe-ui",
  },
  "axe.navigation": {
    key: "axe.navigation",
    title: "AXE Navigation",
    summary: "Navigiert zwischen Chat, Dashboard, Neural, Settings und verlinkt ControlDeck.",
    whyItMatters: "AXE bleibt die operative Frontdoor, während Governance und Katalog in ControlDeck liegen.",
    examples: [
      "Von Chat zu Dashboard wechseln, um Ausführungen live zu prüfen.",
      "Bei Provider-Fragen direkt nach ControlDeck Settings springen.",
    ],
    useCases: ["Operator Workflow", "Cross-Surface Handover"],
    docPath: "/help/axe.navigation",
    surface: "axe-ui",
  },
};

export function getAxeHelpTopic(topicKey: string): HelpTopic | null {
  return AXE_HELP_TOPICS[topicKey] || null;
}
