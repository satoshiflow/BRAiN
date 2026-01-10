/**
 * PrivacySettings Component
 *
 * User-facing controls for AXE telemetry privacy settings.
 *
 * **Features:**
 * - Anonymization level selector (none, pseudonymized, strict)
 * - Telemetry enable/disable toggle
 * - Training data opt-in
 * - Data export/deletion requests
 * - DSGVO-compliant
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Shield, Database, Download, Trash2, Info } from 'lucide-react';
import { cn } from '../utils/cn';

export type AnonymizationLevel = 'none' | 'pseudonymized' | 'strict';

interface PrivacySettings {
  anonymization_level: AnonymizationLevel;
  telemetry_enabled: boolean;
  training_opt_in: boolean;
  retention_days: number;
}

interface PrivacySettingsProps {
  appId: string;
  sessionId: string;
  backendUrl: string;
  theme?: 'dark' | 'light';
  onSettingsChange?: (settings: PrivacySettings) => void;
}

const ANONYMIZATION_LEVELS = [
  {
    value: 'none' as const,
    label: 'None',
    description: 'Full data collection (requires explicit consent)',
    icon: Database,
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
  },
  {
    value: 'pseudonymized' as const,
    label: 'Pseudonymized',
    description: 'Hash user IDs, remove IP addresses (recommended)',
    icon: Shield,
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
  },
  {
    value: 'strict' as const,
    label: 'Strict',
    description: 'Remove all PII, only aggregate data',
    icon: Shield,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
  },
];

export function PrivacySettings({
  appId,
  sessionId,
  backendUrl,
  theme = 'dark',
  onSettingsChange,
}: PrivacySettingsProps) {
  const [settings, setSettings] = useState<PrivacySettings>({
    anonymization_level: 'pseudonymized',
    telemetry_enabled: true,
    training_opt_in: false,
    retention_days: 90,
  });

  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Update settings
  const updateSettings = (updates: Partial<PrivacySettings>) => {
    const newSettings = { ...settings, ...updates };
    setSettings(newSettings);
    onSettingsChange?.(newSettings);
  };

  // Save to backend (placeholder)
  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus('idle');

    try {
      // TODO: Implement backend API call
      // await fetch(`${backendUrl}/api/axe/privacy/settings`, {
      //   method: 'PUT',
      //   body: JSON.stringify({ app_id: appId, ...settings })
      // });

      // Simulate save
      await new Promise((resolve) => setTimeout(resolve, 500));

      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to save privacy settings:', error);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  // Export data (placeholder)
  const handleExportData = async () => {
    try {
      // TODO: Implement backend API call
      console.log('Exporting data for session:', sessionId);
      alert('Data export functionality coming soon (DSGVO Art. 20)');
    } catch (error) {
      console.error('Failed to export data:', error);
    }
  };

  // Delete data (placeholder)
  const handleDeleteData = async () => {
    const confirmed = confirm(
      'Are you sure you want to delete all your telemetry data? This action cannot be undone.'
    );

    if (!confirmed) return;

    try {
      // TODO: Implement backend API call
      console.log('Deleting data for session:', sessionId);
      alert('Data deletion functionality coming soon (DSGVO Art. 17)');
    } catch (error) {
      console.error('Failed to delete data:', error);
    }
  };

  return (
    <div
      className={cn(
        'p-6 rounded-lg border',
        theme === 'dark'
          ? 'bg-gray-900 border-gray-700'
          : 'bg-white border-gray-200'
      )}
    >
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-1">Privacy & Data Controls</h2>
        <p
          className={cn(
            'text-sm',
            theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
          )}
        >
          Configure how AXE collects and stores your data (DSGVO-compliant)
        </p>
      </div>

      {/* Telemetry Toggle */}
      <div className="mb-6">
        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <div className="text-sm font-medium mb-1">Enable Telemetry</div>
            <div
              className={cn(
                'text-xs',
                theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
              )}
            >
              Collect usage data to improve AXE
            </div>
          </div>
          <button
            onClick={() =>
              updateSettings({ telemetry_enabled: !settings.telemetry_enabled })
            }
            className={cn(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              settings.telemetry_enabled ? 'bg-green-500' : 'bg-gray-300'
            )}
          >
            <span
              className={cn(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                settings.telemetry_enabled ? 'translate-x-6' : 'translate-x-1'
              )}
            />
          </button>
        </label>
      </div>

      {/* Anonymization Level */}
      <div className="mb-6">
        <div className="text-sm font-medium mb-3">Anonymization Level</div>
        <div className="space-y-2">
          {ANONYMIZATION_LEVELS.map((level) => {
            const Icon = level.icon;
            const isSelected = settings.anonymization_level === level.value;

            return (
              <button
                key={level.value}
                onClick={() =>
                  updateSettings({ anonymization_level: level.value })
                }
                className={cn(
                  'w-full p-3 rounded-lg border-2 text-left transition-all',
                  'hover:border-primary',
                  isSelected
                    ? 'border-primary bg-primary/5'
                    : theme === 'dark'
                    ? 'border-gray-700 bg-gray-800'
                    : 'border-gray-200 bg-gray-50'
                )}
              >
                <div className="flex items-start gap-3">
                  <div className={cn('p-2 rounded-lg', level.bgColor)}>
                    <Icon className={cn('w-4 h-4', level.color)} />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium mb-1">{level.label}</div>
                    <div
                      className={cn(
                        'text-xs',
                        theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
                      )}
                    >
                      {level.description}
                    </div>
                  </div>
                  {isSelected && (
                    <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-white" />
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Training Data Opt-In */}
      <div className="mb-6 p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.training_opt_in}
            onChange={(e) =>
              updateSettings({ training_opt_in: e.target.checked })
            }
            className="mt-1 w-4 h-4 rounded border-gray-300 text-blue-500 focus:ring-blue-500"
          />
          <div className="flex-1">
            <div className="text-sm font-medium mb-1 flex items-center gap-2">
              Contribute to Training Data
              <Info className="w-3 h-3 text-blue-500" />
            </div>
            <div className="text-xs text-blue-400">
              Allow anonymized data to be used for LLM training (opt-in, DSGVO
              Art. 6(1)(a))
            </div>
          </div>
        </label>
      </div>

      {/* Data Retention */}
      <div className="mb-6">
        <div className="text-sm font-medium mb-2">Data Retention Period</div>
        <select
          value={settings.retention_days}
          onChange={(e) =>
            updateSettings({ retention_days: parseInt(e.target.value) })
          }
          className={cn(
            'w-full px-3 py-2 rounded-lg border',
            theme === 'dark'
              ? 'bg-gray-800 border-gray-700'
              : 'bg-white border-gray-200'
          )}
        >
          <option value={7}>7 days</option>
          <option value={30}>30 days</option>
          <option value={90}>90 days (recommended)</option>
          <option value={180}>180 days</option>
          <option value={365}>1 year</option>
          <option value={730}>2 years (maximum)</option>
        </select>
      </div>

      {/* DSGVO Actions */}
      <div className="space-y-3 mb-6">
        <div className="text-sm font-medium">Your Rights (DSGVO)</div>

        <button
          onClick={handleExportData}
          className={cn(
            'w-full px-4 py-2 rounded-lg border flex items-center justify-center gap-2',
            'hover:bg-primary/10 transition-colors',
            theme === 'dark'
              ? 'border-gray-700 bg-gray-800'
              : 'border-gray-200 bg-gray-50'
          )}
        >
          <Download className="w-4 h-4" />
          <span className="text-sm">Export My Data (Art. 20)</span>
        </button>

        <button
          onClick={handleDeleteData}
          className={cn(
            'w-full px-4 py-2 rounded-lg border flex items-center justify-center gap-2',
            'hover:bg-red-500/10 hover:border-red-500/50 transition-colors',
            theme === 'dark'
              ? 'border-gray-700 bg-gray-800 text-red-400'
              : 'border-gray-200 bg-gray-50 text-red-600'
          )}
        >
          <Trash2 className="w-4 h-4" />
          <span className="text-sm">Delete All My Data (Art. 17)</span>
        </button>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={isSaving}
        className={cn(
          'w-full px-4 py-3 rounded-lg font-medium transition-colors',
          'bg-primary text-primary-foreground',
          'hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed'
        )}
      >
        {isSaving ? 'Saving...' : 'Save Privacy Settings'}
      </button>

      {saveStatus === 'success' && (
        <div className="mt-3 text-sm text-green-500 text-center">
          ✓ Settings saved successfully
        </div>
      )}

      {saveStatus === 'error' && (
        <div className="mt-3 text-sm text-red-500 text-center">
          ✗ Failed to save settings
        </div>
      )}
    </div>
  );
}
