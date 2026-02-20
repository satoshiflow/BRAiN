// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

/**
 * System Settings Page
 *
 * General system configuration and environment management
 */

"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Settings, Server, Database, Shield, Bell, LogsIcon, Save, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function SystemSettingsPage() {
  // Placeholder state - will be replaced with React Query hooks when backend is ready
  const [environment, setEnvironment] = useState<'development' | 'staging' | 'production'>('development');
  const [settings, setSettings] = useState({
    // API Settings
    apiTimeout: 30000,
    maxRetries: 3,
    retryDelay: 1000,

    // Database Settings
    dbPoolSize: 20,
    dbTimeout: 5000,
    enableQueryLogging: false,

    // Security Settings
    enableCORS: true,
    corsOrigins: 'http://localhost:3000,http://localhost:3001',
    enableRateLimiting: true,
    rateLimitWindow: 60000,
    rateLimitMaxRequests: 100,

    // Logging Settings
    logLevel: 'INFO',
    enableStructuredLogging: true,
    logRetentionDays: 30,

    // Notifications
    enableEmailNotifications: false,
    enableSlackNotifications: false,
    alertOnCriticalErrors: true,
  });

  const [hasChanges, setHasChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSettingChange = (key: string, value: string | number | boolean) => {
    setSettings({ ...settings, [key]: value });
    setHasChanges(true);
    setSaveSuccess(false);
  };

  const handleSave = () => {
    // TODO: Implement save to backend
    console.log('Saving settings:', settings);
    setHasChanges(false);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Settings</h1>
          <p className="text-muted-foreground">
            General system configuration and environment management
          </p>
        </div>
        <Button onClick={handleSave} disabled={!hasChanges}>
          <Save className="mr-2 h-4 w-4" />
          Save Changes
        </Button>
      </div>

      {/* Success/Warning Messages */}
      {saveSuccess && (
        <Alert>
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <AlertDescription>Settings saved successfully</AlertDescription>
        </Alert>
      )}

      {hasChanges && (
        <Alert>
          <AlertDescription>
            You have unsaved changes. Click "Save Changes" to apply them.
          </AlertDescription>
        </Alert>
      )}

      {/* Environment Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            Environment
          </CardTitle>
          <CardDescription>
            Current deployment environment
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            {(['development', 'staging', 'production'] as const).map((env) => (
              <Badge
                key={env}
                variant={environment === env ? 'default' : 'outline'}
                className="cursor-pointer px-4 py-2"
                onClick={() => setEnvironment(env)}
              >
                {env.toUpperCase()}
              </Badge>
            ))}
          </div>
          {environment === 'production' && (
            <Alert className="mt-4" variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Production environment: Changes require extra caution
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* API Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            API Configuration
          </CardTitle>
          <CardDescription>
            HTTP client and API request settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="apiTimeout">Timeout (ms)</Label>
              <Input
                id="apiTimeout"
                type="number"
                value={settings.apiTimeout}
                onChange={(e) =>
                  handleSettingChange('apiTimeout', parseInt(e.target.value) || 30000)
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxRetries">Max Retries</Label>
              <Input
                id="maxRetries"
                type="number"
                value={settings.maxRetries}
                onChange={(e) =>
                  handleSettingChange('maxRetries', parseInt(e.target.value) || 3)
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="retryDelay">Retry Delay (ms)</Label>
              <Input
                id="retryDelay"
                type="number"
                value={settings.retryDelay}
                onChange={(e) =>
                  handleSettingChange('retryDelay', parseInt(e.target.value) || 1000)
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Database Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Database Configuration
          </CardTitle>
          <CardDescription>
            PostgreSQL connection pool and query settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="dbPoolSize">Connection Pool Size</Label>
              <Input
                id="dbPoolSize"
                type="number"
                value={settings.dbPoolSize}
                onChange={(e) =>
                  handleSettingChange('dbPoolSize', parseInt(e.target.value) || 20)
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="dbTimeout">Query Timeout (ms)</Label>
              <Input
                id="dbTimeout"
                type="number"
                value={settings.dbTimeout}
                onChange={(e) =>
                  handleSettingChange('dbTimeout', parseInt(e.target.value) || 5000)
                }
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="enableQueryLogging"
              checked={settings.enableQueryLogging}
              onChange={(e) => handleSettingChange('enableQueryLogging', e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="enableQueryLogging" className="text-sm font-medium">
              Enable query logging (may impact performance)
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Security Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Security Settings
          </CardTitle>
          <CardDescription>
            CORS, rate limiting, and security policies
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="enableCORS"
              checked={settings.enableCORS}
              onChange={(e) => handleSettingChange('enableCORS', e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="enableCORS" className="text-sm font-medium">
              Enable CORS
            </label>
          </div>

          {settings.enableCORS && (
            <div className="space-y-2">
              <Label htmlFor="corsOrigins">Allowed CORS Origins (comma-separated)</Label>
              <Input
                id="corsOrigins"
                value={settings.corsOrigins}
                onChange={(e) => handleSettingChange('corsOrigins', e.target.value)}
                placeholder="http://localhost:3000,https://app.example.com"
              />
            </div>
          )}

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="enableRateLimiting"
              checked={settings.enableRateLimiting}
              onChange={(e) => handleSettingChange('enableRateLimiting', e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="enableRateLimiting" className="text-sm font-medium">
              Enable rate limiting
            </label>
          </div>

          {settings.enableRateLimiting && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="rateLimitWindow">Time Window (ms)</Label>
                <Input
                  id="rateLimitWindow"
                  type="number"
                  value={settings.rateLimitWindow}
                  onChange={(e) =>
                    handleSettingChange('rateLimitWindow', parseInt(e.target.value) || 60000)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rateLimitMaxRequests">Max Requests per Window</Label>
                <Input
                  id="rateLimitMaxRequests"
                  type="number"
                  value={settings.rateLimitMaxRequests}
                  onChange={(e) =>
                    handleSettingChange('rateLimitMaxRequests', parseInt(e.target.value) || 100)
                  }
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Logging Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LogsIcon className="h-5 w-5" />
            Logging Configuration
          </CardTitle>
          <CardDescription>
            Log level and retention settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="logLevel">Log Level</Label>
            <select
              id="logLevel"
              value={settings.logLevel}
              onChange={(e) => handleSettingChange('logLevel', e.target.value)}
              className="w-full h-10 px-3 rounded-md border border-slate-700 bg-slate-900 text-slate-100"
            >
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="logRetentionDays">Log Retention (days)</Label>
            <Input
              id="logRetentionDays"
              type="number"
              value={settings.logRetentionDays}
              onChange={(e) =>
                handleSettingChange('logRetentionDays', parseInt(e.target.value) || 30)
              }
            />
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="enableStructuredLogging"
              checked={settings.enableStructuredLogging}
              onChange={(e) => handleSettingChange('enableStructuredLogging', e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="enableStructuredLogging" className="text-sm font-medium">
              Enable structured logging (JSON format)
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notifications
          </CardTitle>
          <CardDescription>
            Alert and notification preferences
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="enableEmailNotifications"
              checked={settings.enableEmailNotifications}
              onChange={(e) => handleSettingChange('enableEmailNotifications', e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="enableEmailNotifications" className="text-sm font-medium">
              Enable email notifications
            </label>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="enableSlackNotifications"
              checked={settings.enableSlackNotifications}
              onChange={(e) => handleSettingChange('enableSlackNotifications', e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="enableSlackNotifications" className="text-sm font-medium">
              Enable Slack notifications
            </label>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="alertOnCriticalErrors"
              checked={settings.alertOnCriticalErrors}
              onChange={(e) => handleSettingChange('alertOnCriticalErrors', e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="alertOnCriticalErrors" className="text-sm font-medium">
              Alert on critical errors
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <Button onClick={handleSave} disabled={!hasChanges}>
          <Save className="mr-2 h-4 w-4" />
          Save All Settings
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            if (confirm('Reset all settings to defaults?')) {
              window.location.reload();
            }
          }}
        >
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}
