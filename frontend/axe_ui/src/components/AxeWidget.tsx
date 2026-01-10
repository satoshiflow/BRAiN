/**
 * AxeWidget - State Container & Layout Manager
 * Manages widget states: minimized, expanded, canvas
 */

'use client';

import React from 'react';
import { AxeMinimized } from './AxeMinimized';
import { AxeExpanded } from './AxeExpanded';
import { AxeCanvas } from './AxeCanvas';
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
        <AxeCanvas
          mode={mode}
          onModeChange={handleModeChange}
          onClose={handleExpand}
          locale={locale}
        />
      )}
    </div>
  );
}
