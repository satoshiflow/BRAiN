/**
 * AxeWidget - State Container & Layout Manager
 * Manages widget states: minimized, expanded, canvas
 */

'use client';

import React from 'react';
import { AxeMinimized } from './AxeMinimized';
import { AxeExpanded } from './AxeExpanded';
import { useAxeStore } from '../store/axeStore';
import { cn } from '../utils/cn';
import type { AxeWidgetProps } from '../types';

export function AxeWidget({
  position,
  defaultOpen,
  theme,
  mode: initialMode,
  locale
}: AxeWidgetProps) {
  const { widgetState, mode, setWidgetState, setMode } = useAxeStore();

  // ============================================================================
  // Widget State Handlers
  // ============================================================================
  const handleMinimize = () => setWidgetState('minimized');
  const handleExpand = () => setWidgetState('expanded');
  const handleOpenCanvas = () => setWidgetState('canvas');

  // ============================================================================
  // Mode Change Handler
  // ============================================================================
  const handleModeChange = (newMode: typeof mode) => {
    setMode(newMode);
  };

  return (
    <div
      className={cn(
        'axe-widget',
        `axe-widget--${widgetState}`,
        `axe-theme--${theme}`,
        theme === 'dark' ? 'dark' : ''
      )}
      style={{
        position: 'fixed',
        bottom: position.bottom,
        right: position.right,
        top: position.top,
        left: position.left,
        zIndex: 9999
      }}
    >
      {widgetState === 'minimized' && (
        <AxeMinimized onClick={handleExpand} theme={theme} />
      )}

      {widgetState === 'expanded' && (
        <AxeExpanded
          mode={mode}
          onModeChange={handleModeChange}
          onMinimize={handleMinimize}
          onOpenCanvas={handleOpenCanvas}
          locale={locale}
          theme={theme}
        />
      )}

      {widgetState === 'canvas' && (
        <div className="axe-canvas-placeholder">
          {/* TODO: Implement AxeCanvas component */}
          <div className="fixed inset-0 bg-background flex items-center justify-center">
            <div className="text-center">
              <h1 className="text-2xl font-bold mb-4">CANVAS Mode</h1>
              <p className="text-muted-foreground">Coming soon...</p>
              <button
                onClick={handleExpand}
                className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md"
              >
                Back to Chat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
