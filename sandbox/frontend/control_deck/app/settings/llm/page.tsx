/**
 * LLM Configuration Settings Page
 *
 * Runtime LLM configuration with support for multiple providers
 */

"use client";

import React, { useState, useEffect } from 'react';
import { useLLMConfig, useUpdateLLMConfig, useResetLLMConfig } from '@/hooks/useLLMConfig';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Loader2, Save, RotateCcw, CheckCircle2, AlertTriangle, Zap } from 'lucide-react';

export default function LLMSettingsPage() {
  const { data: config, isLoading, error } = useLLMConfig();
  const updateMutation = useUpdateLLMConfig();
  const resetMutation = useResetLLMConfig();

  // Form state
  const [formData, setFormData] = useState({
    provider: '',
    host: '',
    model: '',
    temperature: 0.7,
    max_tokens: 2000,
    enabled: true,
  });

  // Sync form with fetched config
  useEffect(() => {
    if (config) {
      setFormData(config);
    }
  }, [config]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  const handleReset = () => {
    if (confirm('Reset LLM configuration to defaults?')) {
      resetMutation.mutate();
    }
  };

  const handleTestConnection = async () => {
    // TODO: Implement test connection endpoint
    alert('Test connection endpoint not yet implemented');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold">LLM Configuration</h1>
          <p className="text-muted-foreground">
            Configure language model provider and parameters
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load LLM configuration: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const hasChanges = config && JSON.stringify(formData) !== JSON.stringify(config);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">LLM Configuration</h1>
        <p className="text-muted-foreground">
          Configure language model provider and runtime parameters
        </p>
      </div>

      {/* Status Card */}
      <Card>
        <CardHeader>
          <CardTitle>Current Status</CardTitle>
          <CardDescription>
            LLM provider connection status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium">
                Provider: <Badge variant="secondary">{config?.provider}</Badge>
              </p>
              <p className="text-sm text-muted-foreground">
                Model: {config?.model}
              </p>
            </div>
            <Badge variant={config?.enabled ? 'default' : 'secondary'}>
              {config?.enabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Provider Settings</CardTitle>
            <CardDescription>
              LLM provider configuration (Ollama, OpenAI compatible)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="provider">Provider</Label>
                <Input
                  id="provider"
                  placeholder="e.g., ollama"
                  value={formData.provider}
                  onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  LLM provider type (ollama, openai, etc.)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="host">Host URL</Label>
                <Input
                  id="host"
                  placeholder="e.g., http://localhost:11434"
                  value={formData.host}
                  onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Provider API endpoint
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="model">Model Name</Label>
              <Input
                id="model"
                placeholder="e.g., llama3.2:latest"
                value={formData.model}
                onChange={(e) => setFormData({ ...formData, model: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Model identifier (must be available on provider)
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                className="h-4 w-4"
              />
              <label htmlFor="enabled" className="text-sm font-medium">
                Enable LLM integration
              </label>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Model Parameters</CardTitle>
            <CardDescription>
              Runtime parameters for LLM generation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="temperature">
                  Temperature: {formData.temperature.toFixed(2)}
                </Label>
                <input
                  type="range"
                  id="temperature"
                  min="0"
                  max="2"
                  step="0.1"
                  value={formData.temperature}
                  onChange={(e) =>
                    setFormData({ ...formData, temperature: parseFloat(e.target.value) })
                  }
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                />
                <p className="text-xs text-muted-foreground">
                  Controls randomness (0=deterministic, 2=creative)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="max_tokens">Max Tokens</Label>
                <Input
                  type="number"
                  id="max_tokens"
                  min="100"
                  max="32000"
                  step="100"
                  value={formData.max_tokens}
                  onChange={(e) =>
                    setFormData({ ...formData, max_tokens: parseInt(e.target.value) || 2000 })
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Maximum response length (tokens)
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Success/Error Messages */}
        {updateMutation.isSuccess && (
          <Alert>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>
              LLM configuration updated successfully
            </AlertDescription>
          </Alert>
        )}

        {updateMutation.error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Failed to update configuration: {updateMutation.error.message}
            </AlertDescription>
          </Alert>
        )}

        {resetMutation.isSuccess && (
          <Alert>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>
              LLM configuration reset to defaults
            </AlertDescription>
          </Alert>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            type="submit"
            disabled={updateMutation.isPending || !hasChanges}
            className="flex-1"
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Configuration
              </>
            )}
          </Button>

          <Button
            type="button"
            variant="outline"
            onClick={handleTestConnection}
            disabled={!config?.enabled}
          >
            <Zap className="mr-2 h-4 w-4" />
            Test Connection
          </Button>

          <Button
            type="button"
            variant="destructive"
            onClick={handleReset}
            disabled={resetMutation.isPending}
          >
            {resetMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Resetting...
              </>
            ) : (
              <>
                <RotateCcw className="mr-2 h-4 w-4" />
                Reset to Defaults
              </>
            )}
          </Button>
        </div>

        {hasChanges && (
          <Alert>
            <AlertDescription>
              You have unsaved changes. Click "Save Configuration" to apply them.
            </AlertDescription>
          </Alert>
        )}
      </form>

      {/* Information Card */}
      <Card>
        <CardHeader>
          <CardTitle>Supported Providers</CardTitle>
          <CardDescription>
            Compatible LLM providers and configuration examples
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border-l-4 border-blue-500 pl-4">
              <p className="font-semibold">Ollama (Local)</p>
              <p className="text-sm text-muted-foreground">
                Host: http://localhost:11434
                <br />
                Models: llama3.2:latest, mistral:latest, etc.
              </p>
            </div>
            <div className="border-l-4 border-green-500 pl-4">
              <p className="font-semibold">OpenAI Compatible</p>
              <p className="text-sm text-muted-foreground">
                Host: https://api.openai.com/v1
                <br />
                Models: gpt-4, gpt-3.5-turbo, etc.
              </p>
            </div>
            <div className="border-l-4 border-purple-500 pl-4">
              <p className="font-semibold">Custom Endpoint</p>
              <p className="text-sm text-muted-foreground">
                Any OpenAI-compatible API endpoint
                <br />
                Configure host URL and model name accordingly
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
