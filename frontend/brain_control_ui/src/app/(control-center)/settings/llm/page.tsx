"use client";

import { useEffect, useState } from "react";
import {
  useLLMConfig,
  useUpdateLLMConfig,
  useResetLLMConfig,
  useLLMTest,
  LLMConfig,
} from "@/hooks/useLLMConfig";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export default function LLMSettingsPage() {
  const { data: config, isLoading, error } = useLLMConfig();
  const updateMutation = useUpdateLLMConfig();
  const resetMutation = useResetLLMConfig();
  const testMutation = useLLMTest();

  const [form, setForm] = useState<LLMConfig>({
    provider: "openai",
    model: "phi3",
    host: "",
    temperature: 0.7,
    max_tokens: 4097,
    enabled: true,
  });

  const [testPrompt, setTestPrompt] = useState(
    "Sag kurz Hallo. Du bist BRAiN im Dev-Modus."
  );
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Wenn Config geladen → Form befüllen
  useEffect(() => {
    if (config) {
      setForm({
        provider: config.provider ?? "openai",
        model: config.model ?? "phi3",
        host: config.host ?? "",
        temperature:
          typeof config.temperature === "number" ? config.temperature : 0.7,
        max_tokens:
          typeof config.max_tokens === "number" ? config.max_tokens : 4097,
        enabled:
          typeof config.enabled === "boolean" ? config.enabled : true,
      });
    }
  }, [config]);

  const handleChange = (patch: Partial<LLMConfig>) => {
    setForm((prev) => ({ ...prev, ...patch }));
  };

  const handleSave = () => {
    setStatusMessage(null);
    updateMutation.mutate(form, {
      onSuccess: () => {
        setStatusMessage("LLM-Konfiguration gespeichert.");
      },
      onError: (err) => {
        setStatusMessage(
          "Fehler beim Speichern: " + (err as Error).message
        );
      },
    });
  };

  const handleReset = () => {
    setStatusMessage(null);
    resetMutation.mutate(undefined, {
      onSuccess: () => {
        setStatusMessage("LLM-Konfiguration auf Defaults zurückgesetzt.");
      },
      onError: (err) => {
        setStatusMessage(
          "Fehler beim Zurücksetzen: " + (err as Error).message
        );
      },
    });
  };

  const handleTest = () => {
    setStatusMessage(null);
    testMutation.mutate(
      { prompt: testPrompt }, // <— WICHTIG: JSON-Objekt, kein nackter String
      {
        onSuccess: (res: any) => {
          setStatusMessage(
            "LLM-Test erfolgreich: " + JSON.stringify(res, null, 2)
          );
        },
        onError: (err: any) => {
          setStatusMessage(
            "LLM-Test fehlgeschlagen: " + (err?.message ?? String(err))
          );
        },
      }
    );
  };

  const disabled = !form.enabled;

  return (
    <div className="flex flex-col gap-8 w-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="brain-shell-title">Settings</h1>
          <p className="brain-shell-subtitle">
            Zentrale Konfiguration von BRAiN (LLM, Agents, System).
          </p>
        </div>
        <div className="text-xs text-muted-foreground">
          {disabled ? "LLM disabled" : "LLM enabled"}
        </div>
      </div>

      {/* Status-Banner */}
      {statusMessage && (
        <div className="brain-card border-emerald-700/60 bg-emerald-900/30 text-emerald-200 text-sm">
          {statusMessage}
        </div>
      )}

      {/* Grid: Konfiguration + Test */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Grundkonfiguration */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">LLM Settings</h2>
          </div>

          {isLoading ? (
            <p className="text-sm text-muted-foreground">
              LLM-Konfiguration wird geladen…
            </p>
          ) : error ? (
            <p className="text-sm text-destructive">
              Fehler beim Laden: {(error as Error).message}
            </p>
          ) : (
            <div className="flex flex-col gap-6 text-sm">
              <div>
                <h3 className="font-medium mb-2">Grundkonfiguration</h3>
                <div className="grid gap-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Provider</Label>
                      <Input
                        value={form.provider}
                        onChange={(e) =>
                          handleChange({ provider: e.target.value })
                        }
                        placeholder="openai"
                      />
                    </div>
                    <div>
                      <Label>Model</Label>
                      <Input
                        value={form.model}
                        onChange={(e) =>
                          handleChange({ model: e.target.value })
                        }
                        placeholder="phi3"
                      />
                    </div>
                  </div>

                  <div>
                    <Label>Host</Label>
                    <Input
                      value={form.host}
                      onChange={(e) =>
                        handleChange({ host: e.target.value })
                      }
                      placeholder="Basis-URL des LLM-Backends (z.B. http://localhost:11434)"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4 items-center">
                    <div>
                      <div className="flex items-center justify-between">
                        <Label>Temperatur</Label>
                        <span className="text-xs text-muted-foreground">
                          {form.temperature.toFixed(2)}
                        </span>
                      </div>
                      <Slider
                        min={0}
                        max={1}
                        step={0.01}
                        value={[form.temperature]}
                        onValueChange={(vals) =>
                          handleChange({ temperature: vals[0] ?? 0.7 })
                        }
                      />
                      <p className="mt-1 text-[0.7rem] text-muted-foreground">
                        0 = deterministisch, 1+ = kreativer.
                      </p>
                    </div>
                    <div>
                      <Label>Max Tokens</Label>
                      <Input
                        type="number"
                        value={form.max_tokens}
                        onChange={(e) =>
                          handleChange({
                            max_tokens: Number(e.target.value) || 0,
                          })
                        }
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between border rounded-2xl px-4 py-3">
                    <div>
                      <p className="text-sm font-medium">
                        LLM global aktiviert
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Wenn deaktiviert, blockiert der LLM-Client alle
                        Anfragen (AXE, Debug, Missionen).
                      </p>
                    </div>
                    <Switch
                      checked={form.enabled}
                      onCheckedChange={(val) =>
                        handleChange({ enabled: val })
                      }
                    />
                  </div>

                  <div className="flex items-center justify-between gap-3">
                    <Button
                      variant="outline"
                      type="button"
                      onClick={handleReset}
                      disabled={resetMutation.isPending}
                    >
                      Auf Defaults zurücksetzen
                    </Button>
                    <Button
                      type="button"
                      onClick={handleSave}
                      disabled={updateMutation.isPending}
                    >
                      Speichern
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* LLM-Test */}
        <div className="brain-card">
          <div className="brain-card-header">
            <h2 className="brain-card-title">LLM-Test</h2>
          </div>

          <div className="flex flex-col gap-4 text-sm">
            <p className="text-muted-foreground">
              Testet die komplette Pipeline: Control Deck → Backend → LLMClient
              → LLM.
            </p>

            <div>
              <Label>Test-Prompt</Label>
              <Textarea
                rows={6}
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
              />
            </div>

            {testMutation.isError && (
              <div className="text-xs text-destructive whitespace-pre-wrap break-words">
                {String(
                  (testMutation.error as any)?.message ??
                    testMutation.error
                )}
              </div>
            )}

            {testMutation.isSuccess && (
              <div className="text-xs text-muted-foreground whitespace-pre-wrap break-words">
                {JSON.stringify(testMutation.data, null, 2)}
              </div>
            )}

            <Button
              type="button"
              onClick={handleTest}
              disabled={testMutation.isPending || disabled}
            >
              LLM testen
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}