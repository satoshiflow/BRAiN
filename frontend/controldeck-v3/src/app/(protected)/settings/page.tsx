"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { logout } from "@/lib/auth";
import { getAxeUIBase } from "@/lib/config";
import { HelpHint } from "@/components/help/help-hint";
import { getControlDeckHelpTopic } from "@/lib/help/topics";
import { ApiError } from "@/lib/api/client";
import {
  configVaultApi,
  VaultDefinition,
  VaultRotationRequest,
  VaultValue,
} from "@/lib/api/config-vault";

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
  const router = useRouter();
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  const [config, setConfig] = useState<SystemConfig>(defaultConfig);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [vaultDefinitions, setVaultDefinitions] = useState<VaultDefinition[]>([]);
  const [vaultValues, setVaultValues] = useState<Record<string, VaultValue>>({});
  const [vaultEdits, setVaultEdits] = useState<Record<string, string>>({});
  const [vaultStatus, setVaultStatus] = useState<string | null>(null);
  const [vaultError, setVaultError] = useState<string | null>(null);
  const [vaultBusyKey, setVaultBusyKey] = useState<string | null>(null);
  const [pendingRotations, setPendingRotations] = useState<VaultRotationRequest[]>([]);

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
    let cancelled = false;

    const loadVault = async () => {
      setVaultError(null);
      try {
        const [defs, values] = await Promise.all([
          configVaultApi.listDefinitions(),
          configVaultApi.listValues(),
        ]);
        const pending = await configVaultApi.listPendingRotations().catch(() => ({ items: [], total: 0 }));
        if (cancelled) {
          return;
        }
        setVaultDefinitions(defs.items);
        setVaultValues(Object.fromEntries(values.items.map((item) => [item.key, item])));
        setPendingRotations(pending.items);
      } catch (error) {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiError && error.status === 403) {
          setVaultError("Keine Berechtigung fuer Secret-Vault Ansicht.");
          return;
        }
        setVaultError("Secret-Vault konnte nicht geladen werden.");
      }
    };

    loadVault();
    return () => {
      cancelled = true;
    };
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

  const classificationLabel = (classification: VaultDefinition["classification"]) => {
    if (classification === "secret") {
      return "Secret";
    }
    if (classification === "sensitive") {
      return "Sensitive";
    }
    return "Config";
  };

  const handleVaultEditChange = (key: string, value: string) => {
    setVaultEdits((prev) => ({ ...prev, [key]: value }));
  };

  const reloadVaultValues = useCallback(async () => {
    const values = await configVaultApi.listValues();
    setVaultValues(Object.fromEntries(values.items.map((item) => [item.key, item])));
  }, []);

  const reloadPendingRotations = useCallback(async () => {
    const response = await configVaultApi.listPendingRotations();
    setPendingRotations(response.items);
  }, []);

  const handleVaultSave = async (definition: VaultDefinition) => {
    const edited = vaultEdits[definition.key];
    if (!edited || !edited.trim()) {
      setVaultError("Bitte zuerst einen neuen Wert eingeben.");
      return;
    }

    try {
      setVaultBusyKey(definition.key);
      setVaultError(null);
      setVaultStatus(null);

      const validation = await configVaultApi.validateValue(definition.key, edited);
      if (!validation.valid) {
        setVaultError(validation.errors.join(" "));
        return;
      }

      await configVaultApi.updateValue(definition.key, edited, "Updated via ControlDeck v3");
      setVaultStatus(`${definition.key} gespeichert.`);
      setVaultEdits((prev) => {
        const next = { ...prev };
        delete next[definition.key];
        return next;
      });
      await reloadVaultValues();
    } catch (error) {
      if (error instanceof ApiError) {
        setVaultError(`Update fehlgeschlagen (${error.status}).`);
      } else {
        setVaultError("Update fehlgeschlagen.");
      }
    } finally {
      setVaultBusyKey(null);
    }
  };

  const handleVaultGenerate = async (definition: VaultDefinition) => {
    try {
      setVaultBusyKey(definition.key);
      setVaultError(null);
      setVaultStatus(null);
      const generated = await configVaultApi.generateValue(
        definition.key,
        definition.value_type === "string" ? 40 : undefined,
        "Generated via ControlDeck v3"
      );
      setVaultStatus(`${generated.key} neu generiert.`);
      await reloadVaultValues();
    } catch (error) {
      if (error instanceof ApiError) {
        setVaultError(`Generierung fehlgeschlagen (${error.status}).`);
      } else {
        setVaultError("Generierung fehlgeschlagen.");
      }
    } finally {
      setVaultBusyKey(null);
    }
  };

  const handleRequestRotation = async (definition: VaultDefinition) => {
    const edited = vaultEdits[definition.key];
    const useGenerate = !edited?.trim() && definition.generator_supported;
    if (!useGenerate && (!edited || !edited.trim())) {
      setVaultError("Bitte Wert eingeben oder Generator verwenden.");
      return;
    }

    try {
      setVaultBusyKey(definition.key);
      setVaultError(null);
      setVaultStatus(null);

      if (!useGenerate) {
        const validation = await configVaultApi.validateValue(definition.key, edited);
        if (!validation.valid) {
          setVaultError(validation.errors.join(" "));
          return;
        }
      }

      await configVaultApi.requestRotation(definition.key, {
        value: useGenerate ? undefined : edited,
        generate: useGenerate,
        length: definition.value_type === "string" ? 40 : undefined,
        reason: "Rotation requested via ControlDeck v3",
      });

      setVaultStatus(`Rotation fuer ${definition.key} angefordert.`);
      setVaultEdits((prev) => {
        const next = { ...prev };
        delete next[definition.key];
        return next;
      });
      await reloadPendingRotations();
    } catch (error) {
      if (error instanceof ApiError) {
        setVaultError(`Rotation request fehlgeschlagen (${error.status}).`);
      } else {
        setVaultError("Rotation request fehlgeschlagen.");
      }
    } finally {
      setVaultBusyKey(null);
    }
  };

  const handleApproveRotation = async (key: string) => {
    try {
      setVaultBusyKey(key);
      setVaultError(null);
      setVaultStatus(null);
      await configVaultApi.approveRotation(key, "Approved in ControlDeck v3");
      setVaultStatus(`Rotation fuer ${key} aktiviert.`);
      await Promise.all([reloadPendingRotations(), reloadVaultValues()]);
    } catch (error) {
      if (error instanceof ApiError) {
        setVaultError(`Approve fehlgeschlagen (${error.status}).`);
      } else {
        setVaultError("Approve fehlgeschlagen.");
      }
    } finally {
      setVaultBusyKey(null);
    }
  };

  const handleRejectRotation = async (key: string) => {
    try {
      setVaultBusyKey(key);
      setVaultError(null);
      setVaultStatus(null);
      await configVaultApi.rejectRotation(key, "Rejected in ControlDeck v3");
      setVaultStatus(`Rotation fuer ${key} verworfen.`);
      await reloadPendingRotations();
    } catch (error) {
      if (error instanceof ApiError) {
        setVaultError(`Reject fehlgeschlagen (${error.status}).`);
      } else {
        setVaultError("Reject fehlgeschlagen.");
      }
    } finally {
      setVaultBusyKey(null);
    }
  };

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem("refresh_token");
      await logout(token || undefined);
    } catch {
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user_email");
      router.push("/login");
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Einstellungen</h1>
        {(() => {
          const topic = getControlDeckHelpTopic("settings.appearance");
          return topic ? <HelpHint topic={topic} /> : null;
        })()}
      </div>
      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Schnellaktionen
        </h3>
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 flex flex-wrap gap-3">
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-700 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600"
          >
            Abmelden
          </button>
          <a
            href={getAxeUIBase()}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 text-sm font-medium text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg hover:bg-cyan-100 dark:hover:bg-cyan-900/30"
          >
            AXE UI oeffnen
          </a>
        </div>
      </div>

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
          Secret Vault
        </h3>
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Governance-Oberflaeche fuer sensible Runtime-Konfiguration. Secrets bleiben maskiert.
          </p>

          {vaultError && (
            <div className="text-sm text-red-600 dark:text-red-400">{vaultError}</div>
          )}
          {vaultStatus && (
            <div className="text-sm text-green-600 dark:text-green-400">{vaultStatus}</div>
          )}

          <div className="space-y-3 max-h-[420px] overflow-auto pr-1">
            {vaultDefinitions.map((definition) => {
              const current = vaultValues[definition.key];
              const busy = vaultBusyKey === definition.key;
              const pending = pendingRotations.find((item) => item.key === definition.key);
              return (
                <div
                  key={definition.key}
                  className="border border-slate-200 dark:border-slate-700 rounded-md p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {definition.key}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        {definition.description}
                      </div>
                    </div>
                    <span className="text-[11px] px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                      {classificationLabel(definition.classification)}
                    </span>
                  </div>

                  <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                    Quelle: {current?.effective_source || "default"} | Aktuell: {String(current?.masked_value ?? "(unset)")}
                  </div>
                  {pending && (
                    <div className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                      Pending Rotation vorhanden ({pending.requested_by}).
                    </div>
                  )}

                  <div className="mt-2 flex gap-2">
                    <input
                      type={definition.classification === "secret" ? "password" : "text"}
                      placeholder="Neuen Wert setzen"
                      value={vaultEdits[definition.key] || ""}
                      onChange={(e) => handleVaultEditChange(definition.key, e.target.value)}
                      className="flex-1 px-3 py-2 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm"
                    />
                    {definition.rotation_supported ? (
                      <button
                        onClick={() => handleRequestRotation(definition)}
                        disabled={busy || Boolean(pending)}
                        className="px-3 py-2 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                      >
                        {busy ? "..." : "Rotation anfordern"}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleVaultSave(definition)}
                        disabled={busy}
                        className="px-3 py-2 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                      >
                        {busy ? "..." : "Speichern"}
                      </button>
                    )}
                    {definition.generator_supported && !definition.rotation_supported && (
                      <button
                        onClick={() => handleVaultGenerate(definition)}
                        disabled={busy}
                        className="px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-700 rounded-md hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50"
                      >
                        Generieren
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-3 border-t border-slate-200 dark:border-slate-700 space-y-2">
            <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
              Pending Approvals
            </div>
            {pendingRotations.length === 0 ? (
              <div className="text-xs text-slate-500 dark:text-slate-400">Keine offenen Rotation-Requests.</div>
            ) : (
              <div className="space-y-2">
                {pendingRotations.map((item) => {
                  const busy = vaultBusyKey === item.key;
                  return (
                    <div
                      key={item.key}
                      className="border border-slate-200 dark:border-slate-700 rounded-md p-2"
                    >
                      <div className="text-xs text-slate-600 dark:text-slate-300">
                        {item.key} | requested_by: {item.requested_by} | candidate: {String(item.masked_candidate)}
                      </div>
                      <div className="mt-2 flex gap-2">
                        <button
                          onClick={() => handleApproveRotation(item.key)}
                          disabled={busy}
                          className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 rounded-md hover:bg-emerald-700 disabled:opacity-50"
                        >
                          {busy ? "..." : "Approve"}
                        </button>
                        <button
                          onClick={() => handleRejectRotation(item.key)}
                          disabled={busy}
                          className="px-3 py-1.5 text-xs font-medium text-white bg-rose-600 rounded-md hover:bg-rose-700 disabled:opacity-50"
                        >
                          {busy ? "..." : "Reject"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
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
