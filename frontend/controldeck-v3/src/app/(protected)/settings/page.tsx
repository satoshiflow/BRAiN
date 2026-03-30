"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";

interface SystemConfig {
  autoRefreshInterval: number;
  enableLiveUpdates: boolean;
  notificationsEnabled: boolean;
  logLevel: "debug" | "info" | "warn" | "error";
  maxLogEntries: number;
}

const defaultConfig: SystemConfig = {
  autoRefreshInterval: 30,
  enableLiveUpdates: true,
  notificationsEnabled: true,
  logLevel: "info",
  maxLogEntries: 1000,
};

export default function SettingsPage() {
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  const [config, setConfig] = useState<SystemConfig>(defaultConfig);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    const savedTheme = localStorage.getItem("controldeck-theme") as "light" | "dark" | "system" | null;
    if (savedTheme) {
      setTheme(savedTheme);
    }

    const savedConfig = localStorage.getItem("controldeck-config");
    if (savedConfig) {
      try {
        setConfig(JSON.parse(savedConfig));
      } catch {
        setConfig(defaultConfig);
      }
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [theme]);

  const handleThemeChange = (newTheme: "light" | "dark" | "system") => {
    setTheme(newTheme);
    localStorage.setItem("controldeck-theme", newTheme);
  };

  const handleConfigChange = useCallback((key: keyof SystemConfig, value: number | boolean | string) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSaveConfig = () => {
    setIsSaving(true);
    setSaveMessage(null);

    setTimeout(() => {
      localStorage.setItem("controldeck-config", JSON.stringify(config));
      setIsSaving(false);
      setSaveMessage("Einstellungen gespeichert");
      setTimeout(() => setSaveMessage(null), 3000);
    }, 500);
  };

  const handleResetConfig = () => {
    if (confirm("Möchten Sie alle Einstellungen auf die Standardwerte zurücksetzen?")) {
      setConfig(defaultConfig);
      localStorage.setItem("controldeck-config", JSON.stringify(defaultConfig));
      setSaveMessage("Auf Standardwerte zurückgesetzt");
      setTimeout(() => setSaveMessage(null), 3000);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Erscheinungsbild
        </h3>
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex gap-3">
            {(["light", "dark", "system"] as const).map((t) => (
              <button
                key={t}
                onClick={() => handleThemeChange(t)}
                className={cn(
                  "flex-1 py-3 px-4 rounded-md border text-sm font-medium transition-colors",
                  theme === t
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                    : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700"
                )}
              >
                {t === "light" && (
                  <span className="flex items-center justify-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m6.34 17.66-1.41 1.41" /><path d="m19.07 4.93-1.41 1.41" />
                    </svg>
                    Hell
                  </span>
                )}
                {t === "dark" && (
                  <span className="flex items-center justify-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
                    </svg>
                    Dunkel
                  </span>
                )}
                {t === "system" && (
                  <span className="flex items-center justify-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="20" height="14" x="2" y="3" rx="2" /><line x1="8" x2="16" y1="21" y2="21" /><line x1="12" x2="12" y1="17" y2="21" />
                    </svg>
                    System
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Dashboard-Einstellungen
        </h3>
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Live-Updates aktivieren
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Echtzeit-Aktualisierung über SSE-Streams
              </p>
            </div>
            <button
              onClick={() => handleConfigChange("enableLiveUpdates", !config.enableLiveUpdates)}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                config.enableLiveUpdates ? "bg-blue-600" : "bg-slate-300 dark:bg-slate-600"
              )}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                  config.enableLiveUpdates ? "translate-x-6" : "translate-x-1"
                )}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Benachrichtigungen
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Desktop-Benachrichtigungen bei kritischen Events
              </p>
            </div>
            <button
              onClick={() => handleConfigChange("notificationsEnabled", !config.notificationsEnabled)}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                config.notificationsEnabled ? "bg-blue-600" : "bg-slate-300 dark:bg-slate-600"
              )}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                  config.notificationsEnabled ? "translate-x-6" : "translate-x-1"
                )}
              />
            </button>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-2">
              Auto-Aktualisierung (Sekunden)
            </label>
            <input
              type="number"
              min={10}
              max={300}
              value={config.autoRefreshInterval}
              onChange={(e) => handleConfigChange("autoRefreshInterval", parseInt(e.target.value) || 30)}
              className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm"
            />
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-2">
              Log-Level
            </label>
            <select
              value={config.logLevel}
              onChange={(e) => handleConfigChange("logLevel", e.target.value)}
              className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm"
            >
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warn">Warnung</option>
              <option value="error">Fehler</option>
            </select>
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-2">
              Maximale Log-Einträge
            </label>
            <input
              type="number"
              min={100}
              max={10000}
              step={100}
              value={config.maxLogEntries}
              onChange={(e) => handleConfigChange("maxLogEntries", parseInt(e.target.value) || 1000)}
              className="w-full px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              onClick={handleSaveConfig}
              disabled={isSaving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isSaving ? "Speichern..." : "Speichern"}
            </button>
            <button
              onClick={handleResetConfig}
              className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600"
            >
              Zurücksetzen
            </button>
            {saveMessage && (
              <span className="flex items-center text-sm text-green-600 dark:text-green-400">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                {saveMessage}
              </span>
            )}
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          System-Info
        </h3>
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Version</span>
              <span className="text-slate-900 dark:text-slate-100">1.0.0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Build</span>
              <span className="text-slate-900 dark:text-slate-100">2026.03.29</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Umgebung</span>
              <span className="text-slate-900 dark:text-slate-100">Lokal</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Backend</span>
              <span className="text-slate-900 dark:text-slate-100">http://localhost:8000</span>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Über ControlDeck v3
        </h3>
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            ControlDeck v3 ist die zentrale Governance-Konsole für das BRAiN Operating
            System. Hier können Sie die Systemgesundheit überwachen, Self-Healing
            konfigurieren, Neural-Parameter justieren und Skill-Ausführungen steuern.
          </p>
          <p className="text-sm text-blue-800 dark:text-blue-200 mt-2">
            <strong>Hinweis:</strong> Diese Konsole dient ausschließlich der Governance von
            BRAiN OS. Geschäftsanwendungsdaten werden in separaten UI-Oberflächen
            verwaltet.
          </p>
        </div>
      </div>
    </div>
  );
}
