"use client";

import { useState } from "react";

import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";

import {
  useLLMConfig,
  useUpdateLLMConfig,
  useResetLLMConfig,
  useLLMTest,
} from "@/hooks/useLLMConfig";

export default function LLMSettingsPage() {
  const { data: config, isLoading, error } = useLLMConfig();
  const updateMutation = useUpdateLLMConfig();
  const resetMutation = useResetLLMConfig();
  const testMutation = useLLMTest();

  const [testPrompt, setTestPrompt] = useState("Sag kurz Hallo. Du bist BRAiN im Dev-Modus.");

  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const saving = updateMutation.isPending;
  const resetting = resetMutation.isPending;
  const testing = testMutation.isPending;

  const handleSave = () => {
    if (!config) return;
    setSuccessMessage(null);
    updateMutation.mutate(
      {
        provider: config.provider,
        host: config.host,
        model: config.model,
        temperature: config.temperature,
        max_tokens: config.max_tokens,
        enabled: config.enabled,
      },
      {
        onSuccess: () => setSuccessMessage("LLM-Konfiguration erfolgreich gespeichert."),
      },
    );
  };

  const handleReset = () => {
    setSuccessMessage(null);
    resetMutation.mutate(undefined, {
      onSuccess: () => setSuccessMessage("LLM-Konfiguration auf Defaults zurückgesetzt."),
    });
  };

  const handleTest = () => {
    testMutation.mutate(testPrompt);
  };

  const updateField = <K extends keyof typeof config>(key: K, value: (typeof config)[K]) => {
    if (!config) return;
    // Wir nutzen ein lokales "shadow" Objekt, das nur in diesem render gültig ist
    (config as any)[key] = value;
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold">LLM Settings</h1>
          <p className="text-sm text-muted-foreground">
            Konfiguration des zentralen BRAiN LLM-Clients (Ollama / Host / Model / Limits).
          </p>
        </div>
        {config && (
          <Badge variant={config.enabled ? "default" : "destructive"}>
            {config.enabled ? "LLM enabled" : "LLM disabled"}
          </Badge>
        )}
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Lade LLM-Konfiguration…</p>}

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {(error as Error).message}
        </div>
      )}

      {updateMutation.error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {(updateMutation.error as Error).message}
        </div>
      )}

      {resetMutation.error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {(resetMutation.error as Error).message}
        </div>
      )}

      {successMessage && (
        <div className="rounded-md border border-emerald-500/50 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-500">
          {successMessage}
        </div>
      )}

      {config && (
        <div className="grid gap-6 lg:grid-cols-[1.2fr,1fr]">
          {/* Konfiguration */}
          <Card className="h-fit">
            <CardHeader>
              <CardTitle>Grundkonfiguration</CardTitle>
              <CardDescription>
                Provider, Host, Model und Limits für den zentralen LLM-Client von BRAiN.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="provider">Provider</Label>
                  <Input
                    id="provider"
                    defaultValue={config.provider}
                    onChange={(e) => updateField("provider", e.target.value)}
                  />
                  <p className="text-[0.75rem] text-muted-foreground">z.B. ollama, openai, lmstudio</p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="model">Model</Label>
                  <Input
                    id="model"
                    defaultValue={config.model}
                    onChange={(e) => updateField("model", e.target.value)}
                  />
                  <p className="text-[0.75rem] text-muted-foreground">z.B. phi3, llama3 etc.</p>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="host">Host</Label>
                <Input
                  id="host"
                  defaultValue={config.host}
                  onChange={(e) => updateField("host", e.target.value)}
                />
                <p className="text-[0.75rem] text-muted-foreground">
                  Basis-URL des LLM-Backends (Ollama, LM Studio, Gateway…).
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Temperatur</Label>
                    <span className="text-xs text-muted-foreground">{config.temperature.toFixed(2)}</span>
                  </div>
                  <Slider
                    min={0}
                    max={2}
                    step={0.05}
                    value={[config.temperature]}
                    onValueChange={([v]) => updateField("temperature", v)}
                  />
                  <p className="text-[0.75rem] text-muted-foreground">0 = deterministisch, 1+ = kreativer.</p>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="max_tokens">Max Tokens</Label>
                  <Input
                    id="max_tokens"
                    type="number"
                    defaultValue={config.max_tokens}
                    onChange={(e) => updateField("max_tokens", Number(e.target.value) || 0)}
                  />
                  <p className="text-[0.75rem] text-muted-foreground">
                    Obergrenze der Antwortlänge (zu klein = abgeschnittene Antworten).
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <div className="space-y-0.5">
                  <Label>LLM global aktiviert</Label>
                  <p className="text-xs text-muted-foreground">
                    Wenn deaktiviert, blockiert der LLM-Client alle Anfragen (AXE, Debug, Missionen).
                  </p>
                </div>
                <Switch
                  checked={config.enabled}
                  onCheckedChange={(value) => updateField("enabled", value)}
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-wrap gap-2 justify-between">
              <Button
                variant="outline"
                type="button"
                onClick={handleReset}
                disabled={resetting || saving}
              >
                {resetting ? "Zurücksetzen…" : "Auf Defaults zurücksetzen"}
              </Button>
              <Button type="button" onClick={handleSave} disabled={saving}>
                {saving ? "Speichern…" : "Speichern"}
              </Button>
            </CardFooter>
          </Card>

          {/* Test Card */}
          <Card className="h-fit">
            <CardHeader>
              <CardTitle>LLM-Test</CardTitle>
              <CardDescription>
                Testet die komplette Pipeline: Control Deck → Backend → LLMClient → LLM.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="testPrompt">Test-Prompt</Label>
                <Textarea
                  id="testPrompt"
                  rows={4}
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                />
              </div>

              {testMutation.error && (
                <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  {(testMutation.error as Error).message}
                </div>
              )}

              {testMutation.data && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium">Antwort-Modell:</span>
                    <Badge variant={testMutation.data.ok ? "default" : "destructive"}>
                      {testMutation.data.model || "unbekannt"}
                    </Badge>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-medium">Prompt:</span>
                    <p className="text-xs break-words text-muted-foreground">
                      {testMutation.data.prompt}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-medium">Raw-Response (Auszug):</span>
                    <pre className="max-h-40 overflow-auto rounded-md bg-muted p-2 text-[0.7rem]">
                      {JSON.stringify(testMutation.data.raw_response, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </CardContent>
            <CardFooter>
              <Button
                type="button"
                variant="secondary"
                onClick={handleTest}
                disabled={testing}
              >
                {testing ? "Test läuft…" : "LLM testen"}
              </Button>
            </CardFooter>
          </Card>
        </div>
      )}
    </div>
  );
}
