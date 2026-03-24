"use client";

export const dynamic = "force-dynamic";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Network, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  createProvider,
  createProviderModel,
  deactivateProviderSecret,
  listProviderModels,
  listProviders,
  patchProvider,
  patchProviderModel,
  ProviderAccount,
  ProviderModel,
  setProviderSecret,
  testProvider,
} from "@/lib/providerPortalApi";

type AsyncState = {
  loading: boolean;
  error: string | null;
  notice: string | null;
};

const emptyState: AsyncState = {
  loading: false,
  error: null,
  notice: null,
};

export default function LLMProvidersSettingsPage() {
  const [providers, setProviders] = useState<ProviderAccount[]>([]);
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [state, setState] = useState<AsyncState>(emptyState);

  const [providerForm, setProviderForm] = useState({
    slug: "",
    display_name: "",
    provider_type: "cloud",
    base_url: "",
    auth_mode: "api_key",
  });
  const [secretForm, setSecretForm] = useState({ providerId: "", secretValue: "" });
  const [modelForm, setModelForm] = useState({
    provider_id: "",
    model_name: "",
    display_name: "",
    capabilities_json: '{"modes":["chat"]}',
  });

  const hasProviders = providers.length > 0;

  const selectedProvider = useMemo(
    () => providers.find((p) => p.id === secretForm.providerId) || null,
    [providers, secretForm.providerId]
  );

  async function loadPortalData() {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      const [providerList, modelList] = await Promise.all([listProviders(), listProviderModels()]);
      setProviders(providerList.items || []);
      setModels(modelList.items || []);
      setState((prev) => ({ ...prev, loading: false, notice: null }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load provider portal data";
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }

  useEffect(() => {
    void loadPortalData();
  }, []);

  async function handleCreateProvider() {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null, notice: null }));
      await createProvider({
        slug: providerForm.slug,
        display_name: providerForm.display_name,
        provider_type: providerForm.provider_type as ProviderAccount["provider_type"],
        base_url: providerForm.base_url,
        auth_mode: providerForm.auth_mode as ProviderAccount["auth_mode"],
        is_enabled: true,
      });
      setProviderForm({
        slug: "",
        display_name: "",
        provider_type: "cloud",
        base_url: "",
        auth_mode: "api_key",
      });
      await loadPortalData();
      setState((prev) => ({ ...prev, notice: "Provider created." }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Provider creation failed";
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }

  async function handleToggleProvider(provider: ProviderAccount) {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      await patchProvider(provider.id, { is_enabled: !provider.is_enabled });
      await loadPortalData();
      setState((prev) => ({
        ...prev,
        notice: `Provider ${provider.display_name} ${provider.is_enabled ? "disabled" : "enabled"}.`,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Provider update failed";
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }

  async function handleSetSecret() {
    if (!secretForm.providerId || !secretForm.secretValue) return;
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      const result = await setProviderSecret(secretForm.providerId, secretForm.secretValue);
      setSecretForm((prev) => ({ ...prev, secretValue: "" }));
      await loadPortalData();
      setState((prev) => ({
        ...prev,
        notice: `Secret updated${result.key_hint_masked ? ` (${result.key_hint_masked})` : ""}.`,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Secret update failed";
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }

  async function handleDeactivateSecret() {
    if (!secretForm.providerId) return;
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      await deactivateProviderSecret(secretForm.providerId);
      await loadPortalData();
      setState((prev) => ({ ...prev, notice: "Secret deactivated." }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Secret deactivation failed";
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }

  async function handleCreateModel() {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      let capabilities: Record<string, unknown> = {};
      try {
        capabilities = JSON.parse(modelForm.capabilities_json);
      } catch {
        setState((prev) => ({ ...prev, loading: false, error: "Capabilities must be valid JSON" }));
        return;
      }
      await createProviderModel({
        provider_id: modelForm.provider_id,
        model_name: modelForm.model_name,
        display_name: modelForm.display_name,
        capabilities,
        is_enabled: true,
        priority: 100,
      });
      setModelForm({
        provider_id: "",
        model_name: "",
        display_name: "",
        capabilities_json: '{"modes":["chat"]}',
      });
      await loadPortalData();
      setState((prev) => ({ ...prev, notice: "Model created." }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Model creation failed";
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }

  async function handleToggleModel(model: ProviderModel) {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      await patchProviderModel(model.id, { is_enabled: !model.is_enabled });
      await loadPortalData();
      setState((prev) => ({
        ...prev,
        notice: `Model ${model.display_name} ${model.is_enabled ? "disabled" : "enabled"}.`,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Model update failed";
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }

  async function handleTestProvider(provider: ProviderAccount) {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null, notice: null }));
      const testResult = await testProvider(provider.id);
      await loadPortalData();
      setState((prev) => ({
        ...prev,
        notice: `${provider.display_name}: ${testResult.status}${
          typeof testResult.latency_ms === "number" ? ` (${testResult.latency_ms} ms)` : ""
        }${testResult.error_code ? ` [${testResult.error_code}]` : ""}`,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Provider test failed";
      setState((prev) => ({ ...prev, loading: false, error: message }));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-300/70">Governance Surface</p>
        <h1 className="text-2xl font-bold tracking-tight">LLM Providers</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Canonical ControlDeck surface for provider registry, credentials, models, and health checks.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={() => void loadPortalData()} disabled={state.loading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
        <Button asChild variant="outline">
          <Link href="/settings/llm" className="inline-flex items-center gap-2">
            Legacy LLM Runtime Settings
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/governance">Governance Overview</Link>
        </Button>
      </div>

      {state.error && (
        <Alert variant="destructive" className="border-red-500/50 bg-red-500/10">
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      )}

      {state.notice && (
        <Alert className="border-emerald-500/50 bg-emerald-500/10 text-emerald-100">
          <AlertDescription>{state.notice}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="providers" className="w-full">
        <TabsList>
          <TabsTrigger value="providers">Providers</TabsTrigger>
          <TabsTrigger value="secrets">Secrets</TabsTrigger>
          <TabsTrigger value="models">Models</TabsTrigger>
        </TabsList>

        <TabsContent value="providers" className="space-y-4">
          <Card className="border-border/50">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-secondary p-2">
                  <Network className="h-5 w-5 text-muted-foreground" />
                </div>
                <div>
                  <CardTitle>Create Provider</CardTitle>
                  <CardDescription>Control-plane provider registry entry.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              <div>
                <Label>Slug</Label>
                <Input
                  value={providerForm.slug}
                  onChange={(e) => setProviderForm((p) => ({ ...p, slug: e.target.value }))}
                  placeholder="openai-main"
                />
              </div>
              <div>
                <Label>Display Name</Label>
                <Input
                  value={providerForm.display_name}
                  onChange={(e) => setProviderForm((p) => ({ ...p, display_name: e.target.value }))}
                  placeholder="OpenAI Main"
                />
              </div>
              <div>
                <Label>Provider Type</Label>
                <Input
                  value={providerForm.provider_type}
                  onChange={(e) => setProviderForm((p) => ({ ...p, provider_type: e.target.value }))}
                  placeholder="cloud|gateway|local"
                />
              </div>
              <div>
                <Label>Auth Mode</Label>
                <Input
                  value={providerForm.auth_mode}
                  onChange={(e) => setProviderForm((p) => ({ ...p, auth_mode: e.target.value }))}
                  placeholder="api_key|none"
                />
              </div>
              <div className="md:col-span-2">
                <Label>Base URL</Label>
                <Input
                  value={providerForm.base_url}
                  onChange={(e) => setProviderForm((p) => ({ ...p, base_url: e.target.value }))}
                  placeholder="https://api.openai.com/v1"
                />
              </div>
              <div className="md:col-span-2">
                <Button onClick={() => void handleCreateProvider()} disabled={state.loading}>
                  Create Provider
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Registered Providers</CardTitle>
              <CardDescription>{providers.length} provider(s) loaded.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {!hasProviders && <p className="text-sm text-muted-foreground">No providers available.</p>}
              {providers.map((provider) => (
                <div key={provider.id} className="rounded border border-border/60 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{provider.display_name}</p>
                      <p className="text-xs text-muted-foreground">{provider.slug} • {provider.base_url}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => void handleTestProvider(provider)}>
                        Test
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => void handleToggleProvider(provider)}>
                        {provider.is_enabled ? "Disable" : "Enable"}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="secrets">
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Provider Secret</CardTitle>
              <CardDescription>
                Set or rotate provider credentials. Secret values are write-only and masked in responses.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label>Provider</Label>
                <select
                  className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
                  value={secretForm.providerId}
                  onChange={(e) => setSecretForm((s) => ({ ...s, providerId: e.target.value }))}
                >
                  <option value="">Select provider</option>
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Secret value</Label>
                <Input
                  type="password"
                  value={secretForm.secretValue}
                  onChange={(e) => setSecretForm((s) => ({ ...s, secretValue: e.target.value }))}
                  placeholder="Paste secret"
                />
              </div>
              {selectedProvider?.key_hint_masked && (
                <p className="text-xs text-muted-foreground">
                  Current hint: {selectedProvider.key_hint_masked}
                </p>
              )}
              <Button
                onClick={() => void handleSetSecret()}
                disabled={state.loading || !secretForm.providerId || !secretForm.secretValue}
              >
                Set Secret
              </Button>
              <Button
                variant="outline"
                onClick={() => void handleDeactivateSecret()}
                disabled={state.loading || !secretForm.providerId}
              >
                Deactivate Secret
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="models" className="space-y-4">
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Create Provider Model</CardTitle>
              <CardDescription>Register model metadata for controlled routing and tests.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              <div>
                <Label>Provider</Label>
                <select
                  className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
                  value={modelForm.provider_id}
                  onChange={(e) => setModelForm((m) => ({ ...m, provider_id: e.target.value }))}
                >
                  <option value="">Select provider</option>
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Model name</Label>
                <Input
                  value={modelForm.model_name}
                  onChange={(e) => setModelForm((m) => ({ ...m, model_name: e.target.value }))}
                  placeholder="gpt-4o-mini"
                />
              </div>
              <div>
                <Label>Display name</Label>
                <Input
                  value={modelForm.display_name}
                  onChange={(e) => setModelForm((m) => ({ ...m, display_name: e.target.value }))}
                  placeholder="GPT-4o Mini"
                />
              </div>
              <div>
                <Label>Capabilities (comma-separated)</Label>
                <Input
                  value={modelForm.capabilities_json}
                  onChange={(e) => setModelForm((m) => ({ ...m, capabilities_json: e.target.value }))}
                  placeholder='{"modes":["chat","responses"]}'
                />
              </div>
              <div className="md:col-span-2">
                <Button onClick={() => void handleCreateModel()} disabled={state.loading || !modelForm.provider_id}>
                  Create Model
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Registered Models</CardTitle>
              <CardDescription>{models.length} model(s) loaded.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {models.length === 0 && <p className="text-sm text-muted-foreground">No models available.</p>}
              {models.map((model) => (
                <div key={model.id} className="rounded border border-border/60 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{model.display_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {model.model_name} • {JSON.stringify(model.capabilities)}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => void handleToggleModel(model)}>
                      {model.is_enabled ? "Disable" : "Enable"}
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
