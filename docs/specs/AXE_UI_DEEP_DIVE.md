# AXE UI Deep-Dive: CANVAS + Event Architecture

**Version:** 1.0.0
**Date:** 2026-01-10
**Status:** Design Phase

---

## Table of Contents

1. [Component Architecture](#1-component-architecture)
2. [State Management](#2-state-management)
3. [Code Editor Integration](#3-code-editor-integration)
4. [Apply/Reject Workflow](#4-applyreject-workflow)
5. [Event Telemetry System](#5-event-telemetry-system)
6. [Floating Widget Package](#6-floating-widget-package)
7. [Implementation Guide](#7-implementation-guide)

---

## 1. Component Architecture

### 1.1 Component Tree

```
<FloatingAxe>                       # Root Component (npm package export)
├── <AxeWidget>                     # State Container + Layout Manager
│   ├── <AxeMinimized>              # Minimized State (60x60px)
│   │   └── <Avatar>                # AXE Avatar/Icon
│   │
│   ├── <AxeExpanded>               # Expanded State (320x480px)
│   │   ├── <ChatHeader>            # Header with Mode Selector
│   │   ├── <ChatMessages>          # Message List (ScrollArea)
│   │   ├── <ChatInput>             # Input + Send Button
│   │   └── <ContextPanel>          # Current Context Display
│   │
│   └── <AxeCanvas>                 # Full-Screen CANVAS (Builder Mode)
│       ├── <CanvasHeader>          # Top Bar (File Tabs, Actions)
│       ├── <ResizablePanelGroup>   # Split-Screen Container
│       │   ├── <LeftPanel>         # Chat + Context (40%)
│       │   │   ├── <ChatMessages>  # Reused from AxeExpanded
│       │   │   ├── <ContextPanel>  # File info, dependencies
│       │   │   └── <ChatInput>     # Reused from AxeExpanded
│       │   │
│       │   ├── <ResizableHandle>   # Draggable Divider
│       │   │
│       │   └── <RightPanel>        # Code Editor (60%)
│       │       ├── <FileTabs>      # Open Files (Tabs)
│       │       ├── <CodeEditor>    # Monaco/CodeMirror
│       │       └── <DiffOverlay>   # Apply/Reject UI
│       │
│       └── <CanvasFooter>          # Status Bar (optional)
│
└── <EventTelemetry>                # Background Event Tracker
    ├── <EventBuffer>               # Client-side event queue
    └── <EventUploader>             # Periodic upload to backend
```

### 1.2 Core Components

#### FloatingAxe.tsx (Entry Point)

```typescript
// frontend/axe_ui/src/components/FloatingAxe.tsx

import React, { useState, useEffect } from 'react';
import { AxeWidget } from './AxeWidget';
import { AxeProvider } from '../context/AxeContext';
import { EventTelemetry } from './EventTelemetry';
import type { AxeConfig, AxeMode, AxeTheme, AxeWidgetPosition } from '../types';

export interface FloatingAxeProps {
  appId: string;                     // "fewoheros" | "satoshiflow" | "brain_control"
  backendUrl: string;                // "https://dev.brain.falklabs.de"
  mode?: AxeMode;                    // Default: 'assistant'
  theme?: AxeTheme;                  // Default: 'dark'
  position?: AxeWidgetPosition;      // Default: { bottom: 20, right: 20 }
  defaultOpen?: boolean;             // Default: false
  locale?: string;                   // Default: 'de'
  userId?: string;                   // Optional (wenn angemeldet)
  sessionId?: string;                // Auto-generated wenn nicht provided
  extraContext?: Record<string, any>; // App-specific context
  onEvent?: (event: AxeEvent) => void; // Event callback
}

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
  const [config, setConfig] = useState<AxeConfig | null>(null);

  // Fetch AXE config from backend
  useEffect(() => {
    fetchAxeConfig(backendUrl, appId).then(setConfig);
  }, [backendUrl, appId]);

  if (!config) {
    return <AxeLoading />;
  }

  return (
    <AxeProvider
      config={config}
      sessionId={sessionId}
      userId={userId}
      extraContext={extraContext}
    >
      <AxeWidget
        position={position}
        defaultOpen={defaultOpen}
        theme={theme}
        mode={mode}
        locale={locale}
      />

      <EventTelemetry
        backendUrl={backendUrl}
        enabled={config.telemetry.enabled}
        onEvent={onEvent}
      />
    </AxeProvider>
  );
}

function generateSessionId(): string {
  return `axe_session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

async function fetchAxeConfig(backendUrl: string, appId: string): Promise<AxeConfig> {
  const response = await fetch(`${backendUrl}/api/axe/config/${appId}`);
  if (!response.ok) throw new Error('Failed to fetch AXE config');
  return response.json();
}
```

#### AxeWidget.tsx (State Manager)

```typescript
// frontend/axe_ui/src/components/AxeWidget.tsx

import React, { useState } from 'react';
import { AxeMinimized } from './AxeMinimized';
import { AxeExpanded } from './AxeExpanded';
import { AxeCanvas } from './AxeCanvas';
import { useAxeContext } from '../context/AxeContext';
import { cn } from '@/lib/utils';

type WidgetState = 'minimized' | 'expanded' | 'canvas';

export interface AxeWidgetProps {
  position: AxeWidgetPosition;
  defaultOpen: boolean;
  theme: AxeTheme;
  mode: AxeMode;
  locale: string;
}

export function AxeWidget({
  position,
  defaultOpen,
  theme,
  mode: initialMode,
  locale
}: AxeWidgetProps) {
  const [state, setState] = useState<WidgetState>(defaultOpen ? 'expanded' : 'minimized');
  const [mode, setMode] = useState<AxeMode>(initialMode);

  const handleMinimize = () => setState('minimized');
  const handleExpand = () => setState('expanded');
  const handleOpenCanvas = () => setState('canvas');

  // Switch to 'builder' mode when opening canvas
  const handleModeChange = (newMode: AxeMode) => {
    setMode(newMode);
    if (newMode === 'builder') {
      setState('canvas');
    }
  };

  return (
    <div
      className={cn(
        'axe-widget',
        `axe-widget--${state}`,
        `axe-theme--${theme}`
      )}
      style={{
        position: 'fixed',
        bottom: position.bottom,
        right: position.right,
        zIndex: 9999
      }}
    >
      {state === 'minimized' && (
        <AxeMinimized onClick={handleExpand} />
      )}

      {state === 'expanded' && (
        <AxeExpanded
          mode={mode}
          onModeChange={handleModeChange}
          onMinimize={handleMinimize}
          onOpenCanvas={handleOpenCanvas}
          locale={locale}
        />
      )}

      {state === 'canvas' && (
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
```

#### AxeCanvas.tsx (Full-Screen CANVAS)

```typescript
// frontend/axe_ui/src/components/AxeCanvas.tsx

import React, { useState } from 'react';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle
} from '@/components/ui/resizable';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { X, Maximize2, Minimize2 } from 'lucide-react';
import { ChatMessages } from './ChatMessages';
import { ChatInput } from './ChatInput';
import { ContextPanel } from './ContextPanel';
import { CodeEditor } from './CodeEditor';
import { DiffOverlay } from './DiffOverlay';
import { useAxeFiles } from '../hooks/useAxeFiles';
import { useAxeDiff } from '../hooks/useAxeDiff';

export interface AxeCanvasProps {
  mode: AxeMode;
  onModeChange: (mode: AxeMode) => void;
  onClose: () => void;
  locale: string;
}

export function AxeCanvas({ mode, onModeChange, onClose, locale }: AxeCanvasProps) {
  const { files, activeFile, setActiveFile, createFile, updateFile } = useAxeFiles();
  const { diff, applyDiff, rejectDiff } = useAxeDiff();

  return (
    <div className="axe-canvas fixed inset-0 bg-background z-[9999]">
      {/* Header */}
      <div className="h-14 border-b flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold">AXE Builder Mode</h1>

          {/* Mode Selector */}
          <Tabs value={mode} onValueChange={onModeChange as any}>
            <TabsList>
              <TabsTrigger value="assistant">Assistant</TabsTrigger>
              <TabsTrigger value="builder">Builder</TabsTrigger>
              <TabsTrigger value="support">Support</TabsTrigger>
              <TabsTrigger value="debug">Debug</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={onClose}>
            <Minimize2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Split-Screen Layout */}
      <div className="h-[calc(100vh-3.5rem)]">
        <ResizablePanelGroup direction="horizontal">
          {/* Left Panel: Chat + Context */}
          <ResizablePanel defaultSize={40} minSize={30} maxSize={50}>
            <div className="h-full flex flex-col">
              {/* Chat Messages */}
              <div className="flex-1 overflow-hidden">
                <ChatMessages />
              </div>

              {/* Context Panel */}
              <div className="border-t">
                <ContextPanel
                  currentFile={activeFile?.name}
                  dependencies={activeFile?.dependencies || []}
                />
              </div>

              {/* Chat Input */}
              <div className="border-t p-4">
                <ChatInput
                  placeholder="Describe what you want to build..."
                  onSend={(message) => {
                    // Send to backend
                    console.log('Send:', message);
                  }}
                />
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Right Panel: Code Editor */}
          <ResizablePanel defaultSize={60} minSize={50}>
            <div className="h-full flex flex-col">
              {/* File Tabs */}
              <div className="border-b">
                <Tabs value={activeFile?.id} onValueChange={setActiveFile}>
                  <TabsList className="h-10 rounded-none border-none">
                    {files.map(file => (
                      <TabsTrigger
                        key={file.id}
                        value={file.id}
                        className="rounded-none border-r"
                      >
                        {file.name}
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>
              </div>

              {/* Code Editor */}
              <div className="flex-1 relative">
                {activeFile && (
                  <CodeEditor
                    language={activeFile.language}
                    value={activeFile.content}
                    onChange={(value) => updateFile(activeFile.id, value)}
                    theme="vs-dark"
                  />
                )}

                {/* Diff Overlay (wenn AXE Änderungen vorschlägt) */}
                {diff && (
                  <DiffOverlay
                    diff={diff}
                    onApply={() => applyDiff(diff.id)}
                    onReject={() => rejectDiff(diff.id)}
                  />
                )}
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
}
```

---

## 2. State Management

### 2.1 Zustand Stores

#### AxeStore (Global State)

```typescript
// frontend/axe_ui/src/store/axeStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AxeConfig, AxeMode, AxeMessage, AxeFile } from '../types';

interface AxeStore {
  // Configuration
  config: AxeConfig | null;
  setConfig: (config: AxeConfig) => void;

  // Session
  sessionId: string;
  userId?: string;

  // Widget State
  widgetState: 'minimized' | 'expanded' | 'canvas';
  setWidgetState: (state: 'minimized' | 'expanded' | 'canvas') => void;

  // Mode
  mode: AxeMode;
  setMode: (mode: AxeMode) => void;

  // Chat
  messages: AxeMessage[];
  addMessage: (message: AxeMessage) => void;
  clearMessages: () => void;

  // Files (CANVAS)
  files: AxeFile[];
  activeFileId: string | null;
  addFile: (file: AxeFile) => void;
  updateFile: (fileId: string, content: string) => void;
  deleteFile: (fileId: string) => void;
  setActiveFile: (fileId: string) => void;

  // Context
  extraContext: Record<string, any>;
  updateContext: (context: Record<string, any>) => void;
}

export const useAxeStore = create<AxeStore>()(
  persist(
    (set, get) => ({
      // Initial State
      config: null,
      sessionId: '',
      widgetState: 'minimized',
      mode: 'assistant',
      messages: [],
      files: [],
      activeFileId: null,
      extraContext: {},

      // Actions
      setConfig: (config) => set({ config }),

      setWidgetState: (state) => set({ widgetState: state }),

      setMode: (mode) => set({ mode }),

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message]
        })),

      clearMessages: () => set({ messages: [] }),

      addFile: (file) =>
        set((state) => ({
          files: [...state.files, file],
          activeFileId: file.id
        })),

      updateFile: (fileId, content) =>
        set((state) => ({
          files: state.files.map(f =>
            f.id === fileId ? { ...f, content } : f
          )
        })),

      deleteFile: (fileId) =>
        set((state) => ({
          files: state.files.filter(f => f.id !== fileId),
          activeFileId: state.activeFileId === fileId
            ? state.files[0]?.id || null
            : state.activeFileId
        })),

      setActiveFile: (fileId) => set({ activeFileId: fileId }),

      updateContext: (context) =>
        set((state) => ({
          extraContext: { ...state.extraContext, ...context }
        }))
    }),
    {
      name: 'axe-storage', // localStorage key
      partialize: (state) => ({
        // Only persist these fields
        messages: state.messages,
        files: state.files,
        mode: state.mode
      })
    }
  )
);
```

#### DiffStore (Apply/Reject State)

```typescript
// frontend/axe_ui/src/store/diffStore.ts

import { create } from 'zustand';
import type { AxeDiff } from '../types';

interface DiffStore {
  pendingDiffs: AxeDiff[];
  currentDiff: AxeDiff | null;

  addDiff: (diff: AxeDiff) => void;
  applyDiff: (diffId: string) => Promise<void>;
  rejectDiff: (diffId: string) => void;
  clearDiffs: () => void;
}

export const useDiffStore = create<DiffStore>((set, get) => ({
  pendingDiffs: [],
  currentDiff: null,

  addDiff: (diff) =>
    set((state) => ({
      pendingDiffs: [...state.pendingDiffs, diff],
      currentDiff: diff // Auto-select new diff
    })),

  applyDiff: async (diffId) => {
    const diff = get().pendingDiffs.find(d => d.id === diffId);
    if (!diff) return;

    // Apply changes to file
    const { useAxeStore } = await import('./axeStore');
    useAxeStore.getState().updateFile(diff.fileId, diff.newContent);

    // Remove from pending
    set((state) => ({
      pendingDiffs: state.pendingDiffs.filter(d => d.id !== diffId),
      currentDiff: null
    }));
  },

  rejectDiff: (diffId) =>
    set((state) => ({
      pendingDiffs: state.pendingDiffs.filter(d => d.id !== diffId),
      currentDiff: null
    })),

  clearDiffs: () => set({ pendingDiffs: [], currentDiff: null })
}));
```

---

## 3. Code Editor Integration

### 3.1 Monaco vs. CodeMirror

| Feature | Monaco Editor | CodeMirror 6 | Recommendation |
|---------|---------------|--------------|----------------|
| **Size** | ~3MB (large) | ~500KB (small) | CodeMirror |
| **VS Code Features** | ✅ Full (IntelliSense, etc.) | ⚠️ Basic | Monaco (wenn Platz) |
| **Performance** | Good (large files) | Excellent | CodeMirror |
| **Customization** | Medium | High | CodeMirror |
| **Diff View** | ✅ Built-in | 🛠️ Custom needed | Monaco |
| **TypeScript Support** | ✅ Native | 🛠️ Via LSP | Monaco |

**Empfehlung:** **Monaco Editor** für AXE UI (trotz Größe)
- Grund: VS Code Features (IntelliSense, Autocomplete) sind kritisch für Code-Erstellung
- Diff-View ist built-in (wichtig für Apply/Reject)
- User erwarten VS Code-ähnliche Erfahrung

### 3.2 Monaco Editor Integration

#### Installation

```bash
npm install @monaco-editor/react monaco-editor
```

#### CodeEditor Component

```typescript
// frontend/axe_ui/src/components/CodeEditor.tsx

import React, { useRef } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';

export interface CodeEditorProps {
  language: string;              // 'typescript' | 'javascript' | 'python' | etc.
  value: string;
  onChange: (value: string) => void;
  theme?: 'vs-dark' | 'light';
  readOnly?: boolean;
  height?: string;
}

export function CodeEditor({
  language,
  value,
  onChange,
  theme = 'vs-dark',
  readOnly = false,
  height = '100%'
}: CodeEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Configure Monaco
    monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
      target: monaco.languages.typescript.ScriptTarget.Latest,
      allowNonTsExtensions: true,
      moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
      module: monaco.languages.typescript.ModuleKind.CommonJS,
      noEmit: true,
      esModuleInterop: true,
      jsx: monaco.languages.typescript.JsxEmit.React,
      reactNamespace: 'React',
      allowJs: true,
      typeRoots: ['node_modules/@types']
    });

    // Add custom keyboard shortcuts
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
      () => {
        // Save file (custom logic)
        console.log('Save file:', value);
      }
    );
  };

  return (
    <Editor
      height={height}
      language={language}
      value={value}
      onChange={(value) => onChange(value || '')}
      theme={theme}
      onMount={handleEditorDidMount}
      options={{
        readOnly,
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: 'on',
        renderWhitespace: 'selection',
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 2,
        wordWrap: 'on',
        quickSuggestions: true,
        suggestOnTriggerCharacters: true,
        acceptSuggestionOnEnter: 'on',
        snippetSuggestions: 'inline'
      }}
    />
  );
}
```

### 3.3 Diff Editor (Apply/Reject)

```typescript
// frontend/axe_ui/src/components/DiffEditor.tsx

import React from 'react';
import { DiffEditor as MonacoDiffEditor } from '@monaco-editor/react';

export interface DiffEditorProps {
  original: string;      // Old code
  modified: string;      // New code (AXE suggestions)
  language: string;
  theme?: 'vs-dark' | 'light';
  readOnly?: boolean;
}

export function DiffEditor({
  original,
  modified,
  language,
  theme = 'vs-dark',
  readOnly = true
}: DiffEditorProps) {
  return (
    <MonacoDiffEditor
      height="100%"
      language={language}
      original={original}
      modified={modified}
      theme={theme}
      options={{
        readOnly,
        renderSideBySide: true, // Side-by-side diff
        minimap: { enabled: false },
        fontSize: 14,
        scrollBeyondLastLine: false,
        automaticLayout: true
      }}
    />
  );
}
```

---

## 4. Apply/Reject Workflow

### 4.1 Diff Lifecycle

```
User sendet Anfrage: "Create React login form"
  ↓
AXE Backend generiert Code
  ↓
Backend sendet Diff zurück (WebSocket oder Polling)
  ↓
Frontend: DiffStore.addDiff(diff)
  ↓
UI zeigt DiffOverlay mit Apply/Reject Buttons
  ↓
User entscheidet:
  → Apply: updateFile(fileId, newContent)
  → Reject: removeDiff(diffId)
  ↓
Event loggen: axe_feedback (applied: true/false)
```

### 4.2 DiffOverlay Component

```typescript
// frontend/axe_ui/src/components/DiffOverlay.tsx

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Check, X, Eye, EyeOff } from 'lucide-react';
import { DiffEditor } from './DiffEditor';
import type { AxeDiff } from '../types';

export interface DiffOverlayProps {
  diff: AxeDiff;
  onApply: () => void;
  onReject: () => void;
}

export function DiffOverlay({ diff, onApply, onReject }: DiffOverlayProps) {
  const [showDiff, setShowDiff] = useState(true);

  return (
    <div className="absolute inset-0 bg-background/95 z-50 flex items-center justify-center p-8">
      <Card className="w-full max-w-5xl h-[80vh] flex flex-col">
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle>AXE Code Suggestion</CardTitle>

          <div className="flex items-center gap-2">
            {/* Toggle Diff View */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDiff(!showDiff)}
            >
              {showDiff ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {showDiff ? 'Hide Diff' : 'Show Diff'}
            </Button>

            {/* Reject Button */}
            <Button
              variant="destructive"
              size="sm"
              onClick={onReject}
            >
              <X className="h-4 w-4 mr-2" />
              Reject
            </Button>

            {/* Apply Button */}
            <Button
              variant="default"
              size="sm"
              onClick={onApply}
            >
              <Check className="h-4 w-4 mr-2" />
              Apply Changes
            </Button>
          </div>
        </CardHeader>

        <CardContent className="flex-1 overflow-hidden">
          {showDiff ? (
            <DiffEditor
              original={diff.oldContent}
              modified={diff.newContent}
              language={diff.language}
              theme="vs-dark"
            />
          ) : (
            <div className="h-full overflow-auto">
              <pre className="text-sm">
                <code>{diff.newContent}</code>
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

### 4.3 WebSocket for Real-Time Diffs

```typescript
// frontend/axe_ui/src/hooks/useAxeWebSocket.ts

import { useEffect, useRef } from 'react';
import { useDiffStore } from '../store/diffStore';
import type { AxeDiff } from '../types';

export function useAxeWebSocket(backendUrl: string, sessionId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const { addDiff } = useDiffStore();

  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket(`${backendUrl.replace('http', 'ws')}/ws/axe/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('AXE WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'diff') {
        // New diff from AXE
        const diff: AxeDiff = data.payload;
        addDiff(diff);
      } else if (data.type === 'message') {
        // Chat message from AXE
        // Handle chat message
      }
    };

    ws.onerror = (error) => {
      console.error('AXE WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('AXE WebSocket disconnected');
      // Auto-reconnect after 3 seconds
      setTimeout(() => {
        // Retry connection
      }, 3000);
    };

    // Cleanup
    return () => {
      ws.close();
    };
  }, [backendUrl, sessionId, addDiff]);

  return wsRef;
}
```

---

## 5. Event Telemetry System

### 5.1 Backend API Endpoints

#### POST /api/axe/events

**Request:**
```json
{
  "events": [
    {
      "event_id": "evt_abc123",
      "event_type": "axe_message",
      "timestamp": "2026-01-10T10:30:00Z",
      "app_id": "fewoheros",
      "user_id": "user_123",
      "session_id": "axe_session_1704883800_xyz",
      "mode": "builder",
      "client": {
        "user_agent": "Mozilla/5.0...",
        "screen_width": 1920,
        "screen_height": 1080,
        "locale": "de",
        "timezone": "Europe/Berlin"
      },
      "payload": {
        "message": "Create a React login form",
        "context": {
          "currentPage": "dashboard"
        },
        "training_enabled": true,
        "anonymization_level": "pseudonymized"
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "events_received": 1,
  "events_stored": 1
}
```

#### GET /api/axe/config/:appId

**Response:**
```json
{
  "app_id": "fewoheros",
  "display_name": "FeWoHeroes Assistant",
  "avatar_url": "https://cdn.brain.falklabs.de/avatars/axe.png",
  "theme": "dark",
  "position": { "bottom": 20, "right": 20 },
  "default_open": false,
  "mode": "assistant",
  "training_mode": "per_app",
  "allowed_scopes": ["bookings", "properties", "guests"],
  "knowledge_spaces": ["fewoheros_docs", "booking_faq"],
  "rate_limits": {
    "requests_per_minute": 10,
    "burst": 5
  },
  "telemetry": {
    "enabled": true,
    "anonymization_level": "pseudonymized",
    "training_mode": "per_app",
    "collect_context_snapshots": true,
    "upload_interval_ms": 30000
  },
  "permissions": {
    "can_run_tools": true,
    "can_trigger_actions": false,
    "can_access_apis": ["bookings", "properties"]
  },
  "ui": {
    "show_context_panel": true,
    "show_mode_selector": true,
    "enable_canvas": true
  }
}
```

### 5.2 PostgreSQL Schema

```sql
-- backend/alembic/versions/005_axe_events.py

CREATE TABLE axe_events (
    event_id VARCHAR(20) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    app_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50),
    session_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    mode VARCHAR(20) NOT NULL,

    -- Client context
    user_agent TEXT,
    screen_width INT,
    screen_height INT,
    locale VARCHAR(10),
    timezone VARCHAR(50),

    -- Event payload (JSONB for flexibility)
    payload JSONB NOT NULL,

    -- Privacy
    anonymization_level VARCHAR(20) NOT NULL,
    training_enabled BOOLEAN DEFAULT TRUE,

    -- Indexes
    INDEX idx_axe_events_app_id (app_id),
    INDEX idx_axe_events_user_id (user_id),
    INDEX idx_axe_events_session_id (session_id),
    INDEX idx_axe_events_timestamp (timestamp),
    INDEX idx_axe_events_type (event_type),
    INDEX idx_axe_events_training (training_enabled, anonymization_level)
);

-- Partitioning by month (for performance)
CREATE TABLE axe_events_2026_01 PARTITION OF axe_events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### 5.3 Frontend Event Tracking

#### EventTelemetry Component

```typescript
// frontend/axe_ui/src/components/EventTelemetry.tsx

import React, { useEffect } from 'react';
import { useEventBuffer } from '../hooks/useEventBuffer';
import { useAxeStore } from '../store/axeStore';
import type { AxeEvent } from '../types';

export interface EventTelemetryProps {
  backendUrl: string;
  enabled: boolean;
  onEvent?: (event: AxeEvent) => void;
}

export function EventTelemetry({ backendUrl, enabled, onEvent }: EventTelemetryProps) {
  const { config, sessionId, userId } = useAxeStore();
  const { addEvent, flush } = useEventBuffer(backendUrl, enabled);

  useEffect(() => {
    if (!enabled || !config) return;

    // Auto-flush every 30 seconds
    const interval = setInterval(() => {
      flush();
    }, config.telemetry.upload_interval_ms || 30000);

    return () => clearInterval(interval);
  }, [enabled, config, flush]);

  useEffect(() => {
    if (!enabled) return;

    // Track page visibility changes
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Flush events before page becomes hidden
        flush();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [enabled, flush]);

  // This component doesn't render anything
  return null;
}
```

#### useEventBuffer Hook

```typescript
// frontend/axe_ui/src/hooks/useEventBuffer.ts

import { useState, useCallback } from 'react';
import { useAxeStore } from '../store/axeStore';
import type { AxeEvent } from '../types';

export function useEventBuffer(backendUrl: string, enabled: boolean) {
  const [buffer, setBuffer] = useState<AxeEvent[]>([]);
  const { config } = useAxeStore();

  const addEvent = useCallback((event: AxeEvent) => {
    if (!enabled) return;

    setBuffer((prev) => [...prev, event]);

    // Auto-flush if buffer is full (100 events)
    if (buffer.length >= 100) {
      flush();
    }
  }, [enabled, buffer.length]);

  const flush = useCallback(async () => {
    if (buffer.length === 0) return;

    try {
      const response = await fetch(`${backendUrl}/api/axe/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events: buffer })
      });

      if (response.ok) {
        // Clear buffer on success
        setBuffer([]);
      } else {
        console.error('Failed to upload events:', response.statusText);
      }
    } catch (error) {
      console.error('Event upload error:', error);
    }
  }, [buffer, backendUrl]);

  return { addEvent, flush };
}
```

### 5.4 Anonymization Middleware

```typescript
// frontend/axe_ui/src/utils/anonymize.ts

import type { AxeEvent, AxeAnonymizationLevel } from '../types';

export function anonymizeEvent(
  event: AxeEvent,
  level: AxeAnonymizationLevel
): AxeEvent {
  if (level === 'none') return event;

  const anonymized = structuredClone(event); // Deep clone

  if (level === 'pseudonymized') {
    // Replace user_id with hash
    if (anonymized.user_id) {
      anonymized.user_id = hashUserId(anonymized.user_id);
    }

    // Replace email addresses in payload
    if (anonymized.payload) {
      anonymized.payload = anonymizePayload(anonymized.payload, 'pseudonymized');
    }

    // Keep client context but remove user_agent details
    if (anonymized.client?.user_agent) {
      anonymized.client.user_agent = simplifyUserAgent(anonymized.client.user_agent);
    }
  }

  if (level === 'strict') {
    // Remove all PII
    delete anonymized.user_id;
    delete anonymized.client?.user_agent;

    // Anonymize payload
    if (anonymized.payload) {
      anonymized.payload = anonymizePayload(anonymized.payload, 'strict');
    }
  }

  return anonymized;
}

function hashUserId(userId: string): string {
  // Simple hash (use crypto.subtle.digest in production)
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = (hash << 5) - hash + userId.charCodeAt(i);
    hash |= 0; // Convert to 32bit integer
  }
  return `user_${Math.abs(hash).toString(36)}`;
}

function anonymizePayload(payload: any, level: 'pseudonymized' | 'strict'): any {
  const anonymized = { ...payload };

  if (typeof payload === 'string') {
    // Remove email addresses
    let text = payload.replace(/\b[\w.-]+@[\w.-]+\.\w+\b/g, 'user@example.com');

    // Remove phone numbers
    text = text.replace(/\b\d{10,15}\b/g, '***');

    if (level === 'strict') {
      // Remove names (simple heuristic: capitalized words)
      text = text.replace(/\b[A-Z][a-z]+\s[A-Z][a-z]+\b/g, '[NAME]');

      // Remove addresses (contains numbers + street keywords)
      text = text.replace(/\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)/gi, '[ADDRESS]');
    }

    return text;
  }

  if (typeof payload === 'object') {
    for (const key in payload) {
      if (typeof payload[key] === 'string') {
        anonymized[key] = anonymizePayload(payload[key], level);
      } else if (typeof payload[key] === 'object') {
        anonymized[key] = anonymizePayload(payload[key], level);
      }
    }
  }

  return anonymized;
}

function simplifyUserAgent(userAgent: string): string {
  // Extract only browser + OS
  const match = userAgent.match(/(Chrome|Firefox|Safari|Edge)\/[\d.]+/);
  return match ? match[0] : 'Unknown Browser';
}
```

---

## 6. Floating Widget Package

### 6.1 npm Package Setup

**Package Structure:**
```
@brain/axe-widget/
├── src/
│   ├── components/       # All React components
│   ├── hooks/            # Custom hooks
│   ├── store/            # Zustand stores
│   ├── types/            # TypeScript types
│   ├── utils/            # Utilities (anonymize, etc.)
│   └── index.ts          # Main export
├── package.json
├── tsconfig.json
├── vite.config.ts        # Build config (Vite)
└── README.md
```

**package.json:**
```json
{
  "name": "@brain/axe-widget",
  "version": "1.0.0",
  "description": "AXE AI Assistant Floating Widget for BRAiN",
  "main": "dist/index.js",
  "module": "dist/index.es.js",
  "types": "dist/index.d.ts",
  "files": ["dist"],
  "scripts": {
    "build": "vite build",
    "dev": "vite",
    "typecheck": "tsc --noEmit",
    "prepublishOnly": "npm run build"
  },
  "peerDependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "dependencies": {
    "zustand": "^4.5.2",
    "@monaco-editor/react": "^4.6.0",
    "lucide-react": "^0.378.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vite-plugin-dts": "^3.7.0"
  },
  "keywords": ["brain", "axe", "ai", "assistant", "widget", "react"],
  "author": "BRAiN Team",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/satoshiflow/BRAiN.git",
    "directory": "packages/axe-widget"
  }
}
```

**vite.config.ts:**
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import dts from 'vite-plugin-dts';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    react(),
    dts({ insertTypesEntry: true })
  ],
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'AxeWidget',
      formats: ['es', 'umd'],
      fileName: (format) => `index.${format}.js`
    },
    rollupOptions: {
      external: ['react', 'react-dom'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM'
        }
      }
    }
  }
});
```

### 6.2 Main Export

```typescript
// src/index.ts

export { FloatingAxe } from './components/FloatingAxe';
export type {
  FloatingAxeProps,
  AxeConfig,
  AxeMode,
  AxeTheme,
  AxeWidgetPosition,
  AxeEvent,
  AxeMessage,
  AxeFile
} from './types';
```

### 6.3 Usage in External Projects

**Installation:**
```bash
npm install @brain/axe-widget
```

**Usage (FeWoHeroes):**
```typescript
// app/layout.tsx

import { FloatingAxe } from '@brain/axe-widget';
import '@brain/axe-widget/dist/style.css'; // Import styles

export default function RootLayout({ children }) {
  return (
    <html lang="de">
      <body>
        {children}

        {/* AXE Widget */}
        <FloatingAxe
          appId="fewoheros"
          backendUrl={process.env.NEXT_PUBLIC_BRAIN_API_BASE}
          mode="assistant"
          theme="dark"
          position={{ bottom: 20, right: 20 }}
          defaultOpen={false}
          locale="de"
          userId={session?.user?.id}
          extraContext={{
            currentPage: pathname,
            userRole: session?.user?.role
          }}
          onEvent={(event) => {
            console.log('AXE Event:', event);
          }}
        />
      </body>
    </html>
  );
}
```

---

## 7. Implementation Guide

### 7.1 Phase 1: Core Components (Week 1)

**Tasks:**
- [ ] Setup project structure (frontend/axe_ui)
- [ ] Install dependencies (Monaco, Zustand, shadcn/ui)
- [ ] Create FloatingAxe component (entry point)
- [ ] Create AxeWidget (state manager)
- [ ] Create AxeMinimized (60x60px avatar)
- [ ] Create AxeExpanded (320x480px chat panel)
- [ ] Test basic widget states (minimized ↔ expanded)

### 7.2 Phase 2: CANVAS Layout (Week 2)

**Tasks:**
- [ ] Create AxeCanvas component (full-screen)
- [ ] Integrate ResizablePanel (40% / 60% split)
- [ ] Add Monaco Editor (CodeEditor component)
- [ ] Create FileTabs component
- [ ] Test split-screen responsiveness
- [ ] Add keyboard shortcuts (Cmd+K, Cmd+S)

### 7.3 Phase 3: Apply/Reject Workflow (Week 3)

**Tasks:**
- [ ] Create DiffStore (Zustand)
- [ ] Create DiffEditor component (Monaco diff view)
- [ ] Create DiffOverlay component
- [ ] Add WebSocket for real-time diffs
- [ ] Test apply/reject workflow
- [ ] Add undo/redo stack

### 7.4 Phase 4: Event Telemetry (Week 4)

**Tasks:**
- [ ] Backend: Create /api/axe/events endpoint
- [ ] Backend: Create PostgreSQL schema (axe_events table)
- [ ] Frontend: Create EventTelemetry component
- [ ] Frontend: Create useEventBuffer hook
- [ ] Frontend: Add anonymization middleware
- [ ] Test event upload (30s interval, 100 events buffer)
- [ ] Add privacy settings UI (Sheet)

### 7.5 Phase 5: Floating Widget Package (Week 5)

**Tasks:**
- [ ] Setup npm package structure (@brain/axe-widget)
- [ ] Configure Vite build (lib mode)
- [ ] Export FloatingAxe + types
- [ ] Publish to npm (or private registry)
- [ ] Test integration in FeWoHeroes
- [ ] Write package README with usage examples

### 7.6 Testing Checklist

**Unit Tests:**
- [ ] Zustand stores (axeStore, diffStore)
- [ ] Anonymization utilities
- [ ] Event buffer logic

**Integration Tests:**
- [ ] Widget state transitions (minimized → expanded → canvas)
- [ ] Monaco Editor integration
- [ ] WebSocket connection
- [ ] Event upload to backend

**E2E Tests (Playwright):**
- [ ] User opens widget
- [ ] User sends chat message
- [ ] User switches to builder mode
- [ ] AXE suggests code change
- [ ] User applies/rejects change
- [ ] Event telemetry uploaded

---

## Appendix

### A. TypeScript Types

```typescript
// src/types/index.ts

export type AxeMode = 'assistant' | 'builder' | 'support' | 'debug';
export type AxeTheme = 'dark' | 'light';
export type AxeTrainingMode = 'global' | 'per_app' | 'off';
export type AxeAnonymizationLevel = 'none' | 'pseudonymized' | 'strict';

export interface AxeWidgetPosition {
  bottom?: number;
  right?: number;
  top?: number;
  left?: number;
}

export interface AxeConfig {
  app_id: string;
  display_name: string;
  avatar_url?: string;
  theme: AxeTheme;
  position: AxeWidgetPosition;
  default_open: boolean;
  mode: AxeMode;
  training_mode: AxeTrainingMode;
  allowed_scopes: string[];
  knowledge_spaces: string[];
  rate_limits: {
    requests_per_minute: number;
    burst: number;
  };
  telemetry: {
    enabled: boolean;
    anonymization_level: AxeAnonymizationLevel;
    training_mode: AxeTrainingMode;
    collect_context_snapshots: boolean;
    upload_interval_ms: number;
  };
  permissions: {
    can_run_tools: boolean;
    can_trigger_actions: boolean;
    can_access_apis: string[];
  };
  ui: {
    show_context_panel: boolean;
    show_mode_selector: boolean;
    enable_canvas: boolean;
  };
}

export interface AxeMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  context?: Record<string, any>;
}

export interface AxeFile {
  id: string;
  name: string;
  language: string;
  content: string;
  dependencies?: string[];
}

export interface AxeDiff {
  id: string;
  fileId: string;
  language: string;
  oldContent: string;
  newContent: string;
  description: string;
  timestamp: string;
}

export type AxeEventType =
  | 'axe_message'
  | 'axe_feedback'
  | 'axe_click'
  | 'axe_context_snapshot'
  | 'axe_error';

export interface AxeEvent {
  event_id: string;
  event_type: AxeEventType;
  timestamp: string;
  app_id: string;
  user_id?: string;
  session_id: string;
  mode: AxeMode;
  client?: {
    user_agent: string;
    screen_width: number;
    screen_height: number;
    locale: string;
    timezone: string;
  };
  payload: Record<string, any>;
  anonymization_level: AxeAnonymizationLevel;
  training_enabled: boolean;
}
```

### B. Backend API Stubs

```python
# backend/api/routes/axe.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter(prefix="/api/axe", tags=["axe"])

class AxeEvent(BaseModel):
    event_id: str
    event_type: str
    timestamp: str
    app_id: str
    user_id: str | None = None
    session_id: str
    mode: str
    client: Dict[str, Any] | None = None
    payload: Dict[str, Any]
    anonymization_level: str
    training_enabled: bool

class AxeEventsRequest(BaseModel):
    events: List[AxeEvent]

@router.post("/events")
async def log_events(request: AxeEventsRequest):
    """Log AXE telemetry events."""
    # TODO: Store in PostgreSQL (axe_events table)
    # TODO: Respect anonymization_level
    # TODO: Rate limiting per app_id
    return {
        "success": True,
        "events_received": len(request.events),
        "events_stored": len(request.events)
    }

@router.get("/config/{app_id}")
async def get_config(app_id: str):
    """Get AXE configuration for app."""
    # TODO: Load from database or config file
    return {
        "app_id": app_id,
        "display_name": f"{app_id.title()} Assistant",
        "theme": "dark",
        "mode": "assistant",
        "training_mode": "per_app",
        "telemetry": {
            "enabled": True,
            "anonymization_level": "pseudonymized",
            "upload_interval_ms": 30000
        },
        "ui": {
            "enable_canvas": True
        }
    }
```

---

**Ende AXE UI Deep-Dive**

**Nächster Schritt:** Implementierung starten (Phase 1) oder weitere Details ausarbeiten?
