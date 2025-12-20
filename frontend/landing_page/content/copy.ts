import type { Lang } from "./i18n";

export const PRICING = {
  currency: "EUR",
  baseMonthlyNet: 499,
  hourlyNet: 3.6,
  earlyDepositNet: 250,
  earlyTermMonths: 12,
} as const;

export type Copy = typeof COPY.de;

export const COPY: Record<Lang, any> = {
  de: {
    nav: { product: "Produkt", useCases: "Anwendungen", pricing: "Preise", trust: "Sicherheit", waitlist: "Warteliste" },
    hero: {
      badge: "Early Access – begrenzte Verfügbarkeit",
      h1: "Autonome Arbeitsleistung als Service für den Mittelstand",
      subline:
        "RYR (Robot as a Service) – orchestriert durch BRAiN™. Abrechnung und Verwaltung laufen systemseitig – planbar, kontrollierbar, industriell gedacht.",
      trustLine: "BRAiN steuert. Odoo verwaltet. Robo arbeitet – und rechnet selbst ab.",
      ctaPrimary: "Warteliste öffnen",
      ctaSecondary: "Early Adopter sichern",
      micro: "Für Handwerk, Dienstleistung, Tourismus und produzierendes Gewerbe (KMU).",
    },
    problem: {
      title: "KMU-Realität: Druck steigt, Personal wird knapper",
      bullets: [
        "Fachkräftemangel und Auslastungsschwankungen",
        "Steigende Lohn- und Nebenkosten",
        "Unplanbare Ausfälle, hohe Übergabe- und Einarbeitungszeiten",
        "Zu viel operative Administration, zu wenig Skalierung",
      ],
      note: "BRAiN × RYR ist darauf ausgelegt, Routine und Zuarbeit zu stabilisieren – ohne Ihre Fachkräfte zu verdrängen.",
    },
    solution: {
      title: "Die Lösung: BRAiN™ × RYR",
      blocks: [
        { title: "BRAiN orchestriert", desc: "Einsatzplanung, Priorisierung, Safety/Policies, Wirtschaftlichkeit, Lifecycle." },
        { title: "Odoo ist das ERP von BRAiN", desc: "Kunden, Verträge, Abos, Rechnungen, Assets, Service – ausgeführt nach BRAiN-Steuerung." },
        { title: "Robo ist ein Service-Worker", desc: "Leistung wird erfasst, gemeldet und nach Regeln abgerechnet – nachvollziehbar und auditierbar." },
      ],
      stepsTitle: "So funktioniert RYR im Betrieb",
      steps: [
        "Robo arbeitet (Aufgaben / Assistenz / Routine).",
        "BRAiN überwacht Regeln, Sicherheit und SLA.",
        "Leistung wird automatisch erfasst.",
        "BRAiN löst Prozesse im ERP aus (Odoo).",
        "Abrechnung, Reporting und Optimierung laufen kontinuierlich.",
      ],
    },
    useCases: {
      title: "Typische Anwendungen",
      cards: [
        { title: "Handwerk", desc: "Zuarbeit, Materialwege, Vorbereitung, Ordnung, Dokumentationshilfe." },
        { title: "Dienstleistung", desc: "Empfang/Assistenz, Kontrollgänge, Botengänge, Nacht- & Wochenend-Routine." },
        { title: "Tourismus", desc: "Check-in Assistenz, Gästeinfo, Nachtbetrieb, Peak-Entlastung, Mehrsprachigkeit." },
        { title: "Produktion", desc: "Interne Logistik, Maschinen-nahe Assistenz, Sicht-/Qualitätschecks, Schichtentlastung." },
      ],
    },
    pricing: {
      title: "Preise (netto) – transparent und KMU-tauglich",
      subtitle: "Planbare Monatsrate plus variable Nutzung. Keine Investitionskosten erforderlich.",
      base: "Grundpreis",
      hourly: "Nutzungsrate",
      earlyTitle: "Early Adopter",
      earlyBody:
        "Mit einer Reservierung sichern Sie sich priorisierten Zugang und fixe Konditionen in der Early-Access-Phase.",
      cta: "Warteliste & Early Adopter",
      smallPrint:
        "Hinweis: Leistungsumfang, SLA und Einsatzprofil werden im Pilot/Onboarding finalisiert. Preise netto zzgl. USt.",
    },
    trust: {
      title: "Sicherheit, Kontrolle, Nachvollziehbarkeit",
      bullets: [
        "Safety-/Policy-Layer mit definierter Übersteuerung",
        "Auditierbare Logs und Statusereignisse",
        "DSGVO- und Compliance-orientierte Datenflüsse",
        "Service- & Wartungsprozesse integriert (ERP-geführt)",
      ],
      note: "Industrie-nah umgesetzt: klare Zustände, klare Verantwortlichkeiten, klare Nachweise.",
    },
    waitlist: {
      title: "Warteliste",
      subtitle:
        "Lassen Sie sich vormerken. Sie erhalten als Erste Informationen zu Verfügbarkeit, Pilotmöglichkeiten und Rollout-Terminen.",
      form: { company: "Unternehmen", email: "E-Mail", name: "Ansprechpartner", submit: "Kostenfrei vormerken" },
      early: {
        title: "Early Adopter reservieren",
        body:
          "Sofortzahlung zur Reservierung. Sie erhalten priorisierte Zuteilung und 12 Monate Early-Adopter-Konditionen.",
        button: "250 € reservieren (Placeholder)",
        note: "Zahlung/Checkout wird in Phase 2 (Backend) angebunden.",
      },
      compliance: "Mit dem Absenden stimmen Sie der Kontaktaufnahme zu. Datenschutz und Widerruf jederzeit möglich.",
    },
    footer: {
      imprint: "Impressum",
      privacy: "Datenschutz",
      contact: "Kontakt",
      claim: "Powered by BRAiN™",
    },
  },

  en: {
    nav: { product: "Product", useCases: "Use cases", pricing: "Pricing", trust: "Safety", waitlist: "Waitlist" },
    hero: {
      badge: "Early Access – limited availability",
      h1: "Autonomous labor as a service for SMEs",
      subline:
        "RYR (Robot as a Service) orchestrated by BRAiN™. Billing and administration are system-driven—predictable, controlled, industry-grade.",
      trustLine: "BRAiN orchestrates. Odoo runs the ERP. Robo works—and bills itself within defined rules.",
      ctaPrimary: "Join the waitlist",
      ctaSecondary: "Secure Early Adopter",
      micro: "For craftsmanship, services, tourism, and manufacturing (SMEs).",
    },
    problem: {
      title: "SME reality: more pressure, fewer skilled workers",
      bullets: [
        "Labor shortages and fluctuating capacity",
        "Rising wages and overhead",
        "Unpredictable outages and onboarding friction",
        "Too much operational admin, too little scalability",
      ],
      note: "BRAiN × RYR stabilizes routine work and assistance—without displacing skilled teams.",
    },
    solution: {
      title: "The solution: BRAiN™ × RYR",
      blocks: [
        { title: "BRAiN orchestrates", desc: "Scheduling, prioritization, safety/policies, unit economics, lifecycle." },
        { title: "Odoo is BRAiN's ERP", desc: "Customers, contracts, subscriptions, invoices, assets, service—executed under BRAiN control." },
        { title: "Robo is a service worker", desc: "Work is tracked, reported, and billed under rules—traceable and auditable." },
      ],
      stepsTitle: "How RYR operates",
      steps: [
        "Robo performs tasks (assistance / routine).",
        "BRAiN monitors rules, safety, and SLA.",
        "Work is captured automatically.",
        "BRAiN triggers ERP processes (Odoo).",
        "Billing, reporting, and optimization run continuously.",
      ],
    },
    useCases: {
      title: "Typical use cases",
      cards: [
        { title: "Craft & Trades", desc: "Assistance, material runs, preparation, order, documentation support." },
        { title: "Services", desc: "Front desk/assistance, patrols, errands, night/weekend routines." },
        { title: "Tourism", desc: "Check-in assistance, guest info, night ops, peak relief, multilingual." },
        { title: "Manufacturing", desc: "Internal logistics, near-machine assistance, visual/quality checks, shift relief." },
      ],
    },
    pricing: {
      title: "Pricing (net) – transparent for SMEs",
      subtitle: "Predictable monthly fee plus usage-based hours. No upfront capex required.",
      base: "Base fee",
      hourly: "Usage rate",
      earlyTitle: "Early Adopter",
      earlyBody:
        "A reservation secures prioritized access and fixed conditions during early access.",
      cta: "Waitlist & Early Adopter",
      smallPrint:
        "Note: Scope, SLA, and deployment profile will be finalized during pilot/onboarding. Net prices excl. VAT.",
    },
    trust: {
      title: "Safety, control, traceability",
      bullets: [
        "Safety/policy layer with defined override",
        "Auditable logs and state events",
        "GDPR-/compliance-oriented data flows",
        "Service & maintenance processes integrated (ERP-led)",
      ],
      note: "Industry-grade execution: clear states, clear responsibilities, clear evidence.",
    },
    waitlist: {
      title: "Waitlist",
      subtitle:
        "Register interest. You'll be first to receive availability, pilot options, and rollout dates.",
      form: { company: "Company", email: "Email", name: "Contact person", submit: "Join waitlist" },
      early: {
        title: "Reserve Early Adopter",
        body:
          "Immediate payment to reserve. You receive prioritized allocation and 12 months Early-Adopter conditions.",
        button: "Reserve €250 (placeholder)",
        note: "Payment/checkout will be connected in Phase 2 (backend).",
      },
      compliance: "By submitting you agree to be contacted. You can withdraw anytime. Privacy applies.",
    },
    footer: {
      imprint: "Imprint",
      privacy: "Privacy",
      contact: "Contact",
      claim: "Powered by BRAiN™",
    },
  },
};
