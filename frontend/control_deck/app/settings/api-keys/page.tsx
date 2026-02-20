"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


/**
 * API Keys Settings Page
 *
 * Manage API keys for external integrations and services
 */


import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Key, Eye, EyeOff, Copy, Trash2, Plus, CheckCircle2 } from 'lucide-react';

interface APIKey {
  id: string;
  name: string;
  service: string;
  key: string;
  created_at: string;
  last_used?: string;
}

export default function APIKeysSettingsPage() {
  // Placeholder state - will be replaced with React Query hooks when backend is ready
  const [apiKeys, setApiKeys] = useState<APIKey[]>([
    {
      id: '1',
      name: 'OpenAI Production',
      service: 'openai',
      key: 'sk-proj-...',
      created_at: '2024-01-15T10:30:00Z',
      last_used: '2024-01-20T14:22:00Z',
    },
    {
      id: '2',
      name: 'GitHub Integration',
      service: 'github',
      key: 'ghp_...',
      created_at: '2024-01-10T08:15:00Z',
    },
  ]);

  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [showNewKeyForm, setShowNewKeyForm] = useState(false);
  const [newKey, setNewKey] = useState({ name: '', service: '', key: '' });
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const toggleKeyVisibility = (id: string) => {
    setShowKeys((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const copyToClipboard = (id: string, key: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleAddKey = () => {
    if (!newKey.name.trim() || !newKey.service.trim() || !newKey.key.trim()) return;

    const key: APIKey = {
      id: Date.now().toString(),
      name: newKey.name,
      service: newKey.service,
      key: newKey.key,
      created_at: new Date().toISOString(),
    };

    setApiKeys([...apiKeys, key]);
    setNewKey({ name: '', service: '', key: '' });
    setShowNewKeyForm(false);
  };

  const handleDeleteKey = (id: string) => {
    if (confirm('Are you sure you want to delete this API key?')) {
      setApiKeys(apiKeys.filter((k) => k.id !== id));
    }
  };

  const maskKey = (key: string) => {
    if (key.length <= 8) return '***';
    return key.substring(0, 8) + '...' + '***';
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">API Keys</h1>
          <p className="text-muted-foreground">
            Manage API keys for external integrations
          </p>
        </div>
        <Button onClick={() => setShowNewKeyForm(!showNewKeyForm)}>
          <Plus className="mr-2 h-4 w-4" />
          Add API Key
        </Button>
      </div>

      {/* Notice */}
      <Alert>
        <Key className="h-4 w-4" />
        <AlertDescription>
          API keys are stored securely and encrypted. Never share your keys with anyone.
        </AlertDescription>
      </Alert>

      {/* New Key Form */}
      {showNewKeyForm && (
        <Card>
          <CardHeader>
            <CardTitle>Add New API Key</CardTitle>
            <CardDescription>
              Configure a new API key for external service integration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="key-name">Name</Label>
                <Input
                  id="key-name"
                  placeholder="e.g., OpenAI Production"
                  value={newKey.name}
                  onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="key-service">Service</Label>
                <Input
                  id="key-service"
                  placeholder="e.g., openai, github, stripe"
                  value={newKey.service}
                  onChange={(e) => setNewKey({ ...newKey, service: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="key-value">API Key</Label>
              <Input
                id="key-value"
                type="password"
                placeholder="Paste your API key here"
                value={newKey.key}
                onChange={(e) => setNewKey({ ...newKey, key: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Your key will be encrypted and stored securely
              </p>
            </div>

            <div className="flex gap-2">
              <Button onClick={handleAddKey}>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Add Key
              </Button>
              <Button variant="outline" onClick={() => setShowNewKeyForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* API Keys List */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Active API Keys</h2>
        {apiKeys.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center p-8">
              <Key className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No API keys configured</p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => setShowNewKeyForm(true)}
              >
                Add Your First API Key
              </Button>
            </CardContent>
          </Card>
        ) : (
          apiKeys.map((apiKey) => (
            <Card key={apiKey.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold">{apiKey.name}</h3>
                      <Badge variant="secondary">{apiKey.service}</Badge>
                    </div>

                    <div className="flex items-center gap-2">
                      <code className="text-sm bg-slate-900 px-3 py-1 rounded">
                        {showKeys[apiKey.id] ? apiKey.key : maskKey(apiKey.key)}
                      </code>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleKeyVisibility(apiKey.id)}
                      >
                        {showKeys[apiKey.id] ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(apiKey.id, apiKey.key)}
                      >
                        {copiedKey === apiKey.id ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>

                    <div className="text-xs text-muted-foreground space-y-1">
                      <p>Created: {new Date(apiKey.created_at).toLocaleString()}</p>
                      {apiKey.last_used && (
                        <p>Last used: {new Date(apiKey.last_used).toLocaleString()}</p>
                      )}
                    </div>
                  </div>

                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteKey(apiKey.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Security Best Practices */}
      <Card>
        <CardHeader>
          <CardTitle>Security Best Practices</CardTitle>
          <CardDescription>
            Guidelines for managing API keys securely
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Rotate API keys regularly (recommended: every 90 days)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Use separate keys for development, staging, and production</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Never commit API keys to version control</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Revoke keys immediately if compromised</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Monitor API key usage for unusual activity</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Use environment-specific keys with minimal required permissions</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
