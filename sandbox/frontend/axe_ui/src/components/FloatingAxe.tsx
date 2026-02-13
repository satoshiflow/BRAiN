/**
 * FloatingAxe - Main Entry Point Component
 * Floating AI Assistant Widget for BRAiN
 */

'use client';

import React, { useState, useEffect } from 'react';
import { AxeWidget } from './AxeWidget';
import { useAxeStore } from '../store/axeStore';
import { generateSessionId } from '../utils/id';
import type { FloatingAxeProps, AxeConfig } from '../types';

export function FloatingAxe({
  appId,
  backendUrl,
  mode = 'assistant',
  theme = 'dark',
  position = { bottom: 20, right: 20 },
  defaultOpen = false,
  locale = 'de',
  userId,
  sessionId: providedSessionId,
  extraContext = {},
  onEvent
}: FloatingAxeProps) {
  const [sessionId] = useState(providedSessionId || generateSessionId());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { config, setConfig, setSession, updateContext } = useAxeStore();

  // ============================================================================
  // Fetch AXE Configuration
  // ============================================================================
  useEffect(() => {
    async function fetchConfig() {
      try {
        setIsLoading(true);
        const response = await fetch(`${backendUrl}/api/axe/config/${appId}`);

        if (!response.ok) {
          throw new Error(`Failed to fetch AXE config: ${response.statusText}`);
        }

        const fetchedConfig: AxeConfig = await response.json();
        setConfig(fetchedConfig);
        setError(null);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);
        console.error('AXE Config Error:', errorMessage);

        // Set fallback config
        setConfig({
          app_id: appId,
          display_name: 'AXE Assistant',
          theme: theme,
          position: position,
          default_open: defaultOpen,
          mode: mode,
          training_mode: 'per_app',
          allowed_scopes: [],
          knowledge_spaces: [],
          rate_limits: {
            requests_per_minute: 10,
            burst: 5
          },
          telemetry: {
            enabled: true,
            anonymization_level: 'pseudonymized',
            training_mode: 'per_app',
            collect_context_snapshots: true,
            upload_interval_ms: 30000
          },
          permissions: {
            can_run_tools: true,
            can_trigger_actions: false,
            can_access_apis: []
          },
          ui: {
            show_context_panel: true,
            show_mode_selector: true,
            enable_canvas: true
          }
        });
      } finally {
        setIsLoading(false);
      }
    }

    fetchConfig();
  }, [backendUrl, appId, theme, position, defaultOpen, mode, setConfig]);

  // ============================================================================
  // Initialize Session
  // ============================================================================
  useEffect(() => {
    setSession(sessionId, userId);
  }, [sessionId, userId, setSession]);

  // ============================================================================
  // Update Extra Context
  // ============================================================================
  useEffect(() => {
    updateContext(extraContext);
  }, [extraContext, updateContext]);

  // ============================================================================
  // Render States
  // ============================================================================
  if (isLoading) {
    return (
      <div
        className="fixed z-[9999] flex items-center justify-center"
        style={{
          bottom: position.bottom,
          right: position.right,
          top: position.top,
          left: position.left
        }}
      >
        <div className="w-14 h-14 bg-primary rounded-full flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error && !config) {
    return (
      <div
        className="fixed z-[9999] flex items-center justify-center"
        style={{
          bottom: position.bottom,
          right: position.right,
          top: position.top,
          left: position.left
        }}
      >
        <div className="w-14 h-14 bg-destructive rounded-full flex items-center justify-center cursor-pointer hover:scale-110 transition-transform"
          onClick={() => window.location.reload()}
        >
          <span className="text-2xl">⚠️</span>
        </div>
      </div>
    );
  }

  if (!config) return null;

  return (
    <AxeWidget
      position={position}
      defaultOpen={defaultOpen}
      theme={theme}
      mode={mode}
      locale={locale}
    />
  );
}
