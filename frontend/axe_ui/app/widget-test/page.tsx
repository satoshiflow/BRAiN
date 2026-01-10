/**
 * AXE UI - Widget Test Page
 * Demo page to test the FloatingAxe widget
 */

'use client';

import React from 'react';
import { FloatingAxe } from '../../src/components/FloatingAxe';

export default function WidgetTestPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">AXE UI Widget Test</h1>
          <p className="text-gray-400 mt-2">
            Testing the FloatingAxe widget component (Phase 1)
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-4xl">
          <div className="bg-gray-800 rounded-lg p-8 mb-8">
            <h2 className="text-2xl font-semibold mb-4">✅ Phase 1 Complete</h2>
            <ul className="space-y-2 text-gray-300">
              <li>✅ Project Structure: <code className="text-green-400">frontend/axe_ui/src/</code></li>
              <li>✅ TypeScript Types: 200+ lines</li>
              <li>✅ Zustand Stores: AxeStore + DiffStore</li>
              <li>✅ FloatingAxe Component: Entry point</li>
              <li>✅ AxeWidget: State manager (minimized/expanded/canvas)</li>
              <li>✅ AxeMinimized: 60x60px floating button</li>
              <li>✅ AxeExpanded: 320x480px chat panel</li>
            </ul>
          </div>

          <div className="bg-gray-800 rounded-lg p-8 mb-8">
            <h2 className="text-2xl font-semibold mb-4">How to Test</h2>
            <ol className="list-decimal list-inside space-y-2 text-gray-300">
              <li>Look for the floating AXE button in <strong>bottom-right corner</strong></li>
              <li>Click the button to <strong>expand</strong> the chat panel</li>
              <li>Type a message and press <strong>Enter</strong></li>
              <li>You'll get a mock response (no real AI backend yet)</li>
              <li>Click the <strong>maximize icon</strong> to open CANVAS mode (placeholder)</li>
              <li>Click <strong>minimize</strong> to collapse back to button</li>
            </ol>
          </div>

          <div className="bg-gray-800 rounded-lg p-8 mb-8">
            <h2 className="text-2xl font-semibold mb-4">⏳ Next Steps (Phase 2-5)</h2>
            <ul className="space-y-2 text-gray-300">
              <li className="flex items-start gap-2">
                <span className="text-yellow-400">🔄</span>
                <div>
                  <strong>Phase 2: CANVAS Layout (Week 2)</strong>
                  <ul className="ml-4 mt-1 text-sm space-y-1">
                    <li>→ ResizablePanel split-screen (40% Chat / 60% Code)</li>
                    <li>→ Monaco Editor integration</li>
                    <li>→ File tabs & syntax highlighting</li>
                  </ul>
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-yellow-400">🔄</span>
                <div>
                  <strong>Phase 3: Apply/Reject Workflow (Week 3)</strong>
                  <ul className="ml-4 mt-1 text-sm space-y-1">
                    <li>→ DiffEditor component (Monaco diff view)</li>
                    <li>→ DiffOverlay with apply/reject buttons</li>
                    <li>→ WebSocket for real-time code suggestions</li>
                  </ul>
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-yellow-400">🔄</span>
                <div>
                  <strong>Phase 4: Event Telemetry (Week 4)</strong>
                  <ul className="ml-4 mt-1 text-sm space-y-1">
                    <li>→ Backend: POST /api/axe/events</li>
                    <li>→ PostgreSQL schema (axe_events table)</li>
                    <li>→ Privacy controls (anonymization)</li>
                  </ul>
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-yellow-400">🔄</span>
                <div>
                  <strong>Phase 5: npm Package (Week 5)</strong>
                  <ul className="ml-4 mt-1 text-sm space-y-1">
                    <li>→ @brain/axe-widget package</li>
                    <li>→ Vite build config</li>
                    <li>→ Integration in FeWoHeroes</li>
                  </ul>
                </div>
              </li>
            </ul>
          </div>

          <div className="bg-gray-800 rounded-lg p-8">
            <h2 className="text-2xl font-semibold mb-4">📦 Dependencies Installed</h2>
            <div className="grid grid-cols-2 gap-4 text-sm text-gray-300">
              <div>
                <h3 className="font-semibold text-white mb-2">Core:</h3>
                <ul className="space-y-1">
                  <li>✓ Next.js 14.2.33</li>
                  <li>✓ React 18.3.1</li>
                  <li>✓ TypeScript 5.4.5</li>
                  <li>✓ Tailwind CSS 3.4.3</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-white mb-2">AXE-specific:</h3>
                <ul className="space-y-1">
                  <li>✓ Zustand 4.5.2</li>
                  <li>✓ Monaco Editor 0.45.0</li>
                  <li>✓ Lucide React 0.378.0</li>
                  <li>✓ Radix UI (Dialog, Tabs, etc.)</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* FloatingAxe Widget */}
      <FloatingAxe
        appId="widget-test"
        backendUrl={process.env.NEXT_PUBLIC_BRAIN_API_BASE || 'http://localhost:8000'}
        mode="assistant"
        theme="dark"
        position={{ bottom: 20, right: 20 }}
        defaultOpen={false}
        locale="de"
        extraContext={{
          page: 'widget-test',
          demo: true,
          phase: 1
        }}
        onEvent={(event) => {
          console.log('AXE Event:', event);
        }}
      />
    </div>
  );
}
