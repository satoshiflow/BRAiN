/**
 * NeuroRail Layout (Phase 3 Frontend)
 *
 * Provides SSE connection to all NeuroRail pages
 */

"use client";

import React from 'react';
import { SSEProvider } from '@/components/neurorail/sse-provider';

export default function NeuroRailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SSEProvider channels={['all']}>
      {children}
    </SSEProvider>
  );
}
