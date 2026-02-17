"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Brain, Server, Globe, AlertTriangle } from "lucide-react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface LLMConfig {
  provider: "ollama" | "openrouter";
  ollamaHost: string;
  ollamaModel: string;
  openrouterModel: string;
}

export default function LLMSettingsPage() {
  const router = useRouter();
  const [config, setConfig] = useState<LLMConfig>({
    provider: "ollama",
    ollamaHost: "http://localhost:11434",
    ollamaModel: "llama3.2:latest",
    openrouterModel: "moonshotai/kimi-k2.5",
  });
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  // Load current config
  useEffect(() => {
    fetch("/api/admin/llm-config")
      .then((res) => res.json())
      .then((data) => {
        if (data.config) {
          setConfig(data.config);
        }
      })
      .catch((err) => console.error("Failed to load LLM config:", err));
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/admin/llm-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch (error) {
      console.error("Failed to save config:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="icon" onClick={() => router.push("/dashboard")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI/LLM Configuration</h1>
          <p className="text-sm text-muted-foreground">
            Configure AXE Chat LLM provider and models
          </p>
        </div>
      </div>

      {/* Security Warning */}
      <Alert variant="destructive" className="border-red-500/50 bg-red-500/10">
        <AlertTriangle className="h-4 w-4 text-red-400" />
        <AlertDescription className="text-red-200">
          <strong>Security Note:</strong> For F&E data protection, local Ollama is recommended. 
          External APIs (OpenRouter) may process sensitive data outside your infrastructure.
        </AlertDescription>
      </Alert>

      {/* Provider Selection */}
      <Card className="border-border/50">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/20 p-2">
              <Brain className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <CardTitle>LLM Provider</CardTitle>
              <CardDescription>
                Select the primary LLM provider for AXE Chat
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <RadioGroup
            value={config.provider}
            onValueChange={(value: "ollama" | "openrouter") =>
              setConfig({ ...config, provider: value })
            }
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            {/* Ollama Option */}
            <div className="flex items-start space-x-3 space-y-0 rounded-lg border border-border/50 p-4 hover:bg-secondary/50 cursor-pointer transition-colors">
              <RadioGroupItem value="ollama" id="ollama" className="mt-1" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-green-400" />
                  <Label htmlFor="ollama" className="font-semibold cursor-pointer">
                    Ollama (Local)
                  </Label>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  Recommended for F&E. Runs entirely on your infrastructure.
                  No data leaves your network.
                </p>
                <div className="mt-3 space-y-2">
                  <div>
                    <Label className="text-xs">Host</Label>
                    <input
                      type="text"
                      value={config.ollamaHost}
                      onChange={(e) =>
                        setConfig({ ...config, ollamaHost: e.target.value })
                      }
                      className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
                      placeholder="http://localhost:11434"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Model</Label>
                    <input
                      type="text"
                      value={config.ollamaModel}
                      onChange={(e) =>
                        setConfig({ ...config, ollamaModel: e.target.value })
                      }
                      className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
                      placeholder="llama3.2:latest"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* OpenRouter Option */}
            <div className="flex items-start space-x-3 space-y-0 rounded-lg border border-border/50 p-4 hover:bg-secondary/50 cursor-pointer transition-colors">
              <RadioGroupItem value="openrouter" id="openrouter" className="mt-1" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-yellow-400" />
                  <Label htmlFor="openrouter" className="font-semibold cursor-pointer">
                    OpenRouter (External)
                  </Label>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  Cloud API access to Kimi, Claude, GPT-4. 
                  <span className="text-yellow-500"> Data processed externally.</span>
                </p>
                <div className="mt-3 space-y-2">
                  <div>
                    <Label className="text-xs">Model</Label>
                    <select
                      value={config.openrouterModel}
                      onChange={(e) =>
                        setConfig({ ...config, openrouterModel: e.target.value })
                      }
                      className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
                    >
                      <option value="moonshotai/kimi-k2.5">Kimi K2.5 (Moonshot)</option>
                      <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                      <option value="openai/gpt-4-turbo">GPT-4 Turbo</option>
                      <option value="google/gemini-pro">Gemini Pro</option>
                    </select>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    API Key configured in backend .env (OPENROUTER_API_KEY)
                  </p>
                </div>
              </div>
            </div>
          </RadioGroup>

          {/* Save Button */}
          <div className="flex items-center gap-4 pt-4 border-t border-border/50">
            <Button onClick={handleSave} disabled={loading} className="min-w-[120px]">
              {loading ? "Saving..." : "Save Configuration"}
            </Button>
            {saved && (
              <span className="text-sm text-green-400">Configuration saved successfully!</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="border-border/50 bg-secondary/30">
        <CardHeader>
          <CardTitle className="text-sm font-medium">About AXE Chat LLM Selection</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            <strong>Ollama (Local):</strong> Best for sensitive F&E data. Requires GPU/CPU resources 
            on your infrastructure. No internet connection needed after model download.
          </p>
          <p>
            <strong>OpenRouter (External):</strong> Access to state-of-the-art models (Kimi, Claude). 
            Requires internet and API key. All prompts are processed externally.
          </p>
          <p className="text-xs text-muted-foreground mt-4">
            Future: Filter Agent will sanitize prompts before external API calls.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
