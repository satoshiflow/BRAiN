/**
 * AxeCanvas - Full-Screen CANVAS Component
 * Split-screen layout: 40% Chat + 60% Code Editor
 */

'use client';

import React, { useState, useEffect } from 'react';
import { X, Minimize2, Send, Plus, FileCode } from 'lucide-react';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle
} from './ui/resizable';
import { CodeEditor } from './CodeEditor';
import { FileTabs } from './FileTabs';
import { DiffOverlay } from './DiffOverlay';
import { useAxeStore } from '../store/axeStore';
import { useDiffStore } from '../store/diffStore';
import { generateMessageId, generateFileId } from '../utils/id';
import { cn } from '../utils/cn';
import type { AxeCanvasProps, AxeMessage } from '../types';

export function AxeCanvas({
  mode,
  onModeChange,
  onClose,
  locale
}: AxeCanvasProps) {
  const [input, setInput] = useState('');

  const {
    config,
    messages,
    addMessage,
    files,
    activeFileId,
    addFile,
    updateFile,
    deleteFile,
    setActiveFile,
    getActiveFile
  } = useAxeStore();

  const { currentDiff, applyDiff, rejectDiff } = useDiffStore();

  const activeFile = getActiveFile();

  // ============================================================================
  // Create Default File if None Exist
  // ============================================================================
  useEffect(() => {
    if (files.length === 0) {
      addFile({
        id: generateFileId(),
        name: 'untitled.tsx',
        language: 'typescript',
        content: '// Start coding here...\n\n',
        dependencies: ['react'],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
    }
  }, [files.length, addFile]);

  // ============================================================================
  // Handle Send Message
  // ============================================================================
  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: AxeMessage = {
      id: generateMessageId(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    };

    addMessage(userMessage);
    setInput('');

    // TODO: Send to backend API
    console.log('Sending message in CANVAS:', userMessage);

    // Mock response with code suggestion (for testing)
    setTimeout(() => {
      const assistantMessage: AxeMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content: `I'll help you with that. Here's a suggestion for "${userMessage.content}".`,
        timestamp: new Date().toISOString()
      };
      addMessage(assistantMessage);

      // TODO: Add mock diff for testing
      // useDiffStore.getState().addDiff({ ... });
    }, 1000);
  };

  // ============================================================================
  // Handle File Actions
  // ============================================================================
  const handleAddFile = () => {
    const newFile = {
      id: generateFileId(),
      name: `untitled-${files.length + 1}.tsx`,
      language: 'typescript',
      content: '// New file\n\n',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    addFile(newFile);
  };

  const handleCodeChange = (value: string) => {
    if (activeFile) {
      updateFile(activeFile.id, value);
    }
  };

  // ============================================================================
  // Render
  // ============================================================================
  return (
    <div className="fixed inset-0 bg-background z-[9999] flex flex-col">
      {/* ========================================================================
          Header
      ======================================================================== */}
      <div className="h-14 border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <FileCode className="w-5 h-5 text-primary" />
            <h1 className="text-lg font-semibold">AXE Builder Mode</h1>
          </div>

          {/* Mode Indicator */}
          <div className="px-3 py-1 bg-primary/10 text-primary text-xs font-medium rounded-full">
            {mode}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Add File Button */}
          <button
            onClick={handleAddFile}
            className="p-2 hover:bg-accent rounded-md transition-colors"
            aria-label="Add new file"
            title="Add new file (Cmd+N)"
          >
            <Plus className="w-4 h-4" />
          </button>

          {/* Minimize Button */}
          <button
            onClick={onClose}
            className="p-2 hover:bg-accent rounded-md transition-colors"
            aria-label="Minimize"
          >
            <Minimize2 className="w-4 h-4" />
          </button>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="p-2 hover:bg-accent rounded-md transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ========================================================================
          Split-Screen Layout
      ======================================================================== */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* ====================================================================
              Left Panel: Chat + Context (40%)
          ==================================================================== */}
          <ResizablePanel defaultSize={40} minSize={30} maxSize={50}>
            <div className="h-full flex flex-col bg-muted/30">
              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-center">
                    <div className="max-w-sm">
                      <p className="text-muted-foreground mb-3">
                        🎨 Welcome to CANVAS mode!
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Describe what you want to build, and I'll help you write
                        the code.
                      </p>
                    </div>
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={cn(
                        'flex',
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                      )}
                    >
                      <div
                        className={cn(
                          'max-w-[85%] rounded-lg px-3 py-2',
                          message.role === 'user'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-card border border-border'
                        )}
                      >
                        <p className="text-sm whitespace-pre-wrap">
                          {message.content}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Context Panel */}
              <div className="border-t border-border p-4 bg-background/50">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                  Current Context
                </h3>
                <div className="space-y-1 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">File:</span>
                    <code className="text-foreground font-mono text-xs">
                      {activeFile?.name || 'none'}
                    </code>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Language:</span>
                    <span className="text-foreground">{activeFile?.language || '-'}</span>
                  </div>
                  {activeFile?.dependencies && activeFile.dependencies.length > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Dependencies:</span>
                      <span className="text-foreground text-xs">
                        {activeFile.dependencies.join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Chat Input */}
              <div className="border-t border-border p-4">
                <div className="flex items-end gap-2">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    placeholder="Describe what you want to build..."
                    rows={2}
                    className={cn(
                      'flex-1 resize-none rounded-md px-3 py-2 text-sm',
                      'border border-border outline-none',
                      'focus:ring-2 focus:ring-primary',
                      'bg-background'
                    )}
                  />
                  <button
                    onClick={handleSend}
                    disabled={!input.trim()}
                    className={cn(
                      'p-2 rounded-md transition-colors',
                      'bg-primary text-primary-foreground',
                      'hover:bg-primary/90',
                      'disabled:opacity-50 disabled:cursor-not-allowed'
                    )}
                    aria-label="Send message"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Press Enter to send, Shift+Enter for new line
                </p>
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* ====================================================================
              Right Panel: Code Editor (60%)
          ==================================================================== */}
          <ResizablePanel defaultSize={60} minSize={50}>
            <div className="h-full flex flex-col">
              {/* File Tabs */}
              <FileTabs
                files={files}
                activeFileId={activeFileId}
                onSelectFile={setActiveFile}
                onCloseFile={deleteFile}
              />

              {/* Code Editor */}
              <div className="flex-1 relative">
                {activeFile ? (
                  <CodeEditor
                    language={activeFile.language}
                    value={activeFile.content}
                    onChange={handleCodeChange}
                    theme="vs-dark"
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-center">
                    <div>
                      <FileCode className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground">No file selected</p>
                      <button
                        onClick={handleAddFile}
                        className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                      >
                        Create New File
                      </button>
                    </div>
                  </div>
                )}

                {/* Diff Overlay */}
                {currentDiff && (
                  <DiffOverlay
                    diff={currentDiff}
                    onApply={() => applyDiff(currentDiff.id)}
                    onReject={() => rejectDiff(currentDiff.id)}
                  />
                )}
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {/* ========================================================================
          Status Bar (Optional)
      ======================================================================== */}
      <div className="h-6 border-t border-border px-4 flex items-center justify-between text-xs text-muted-foreground bg-muted/30">
        <div className="flex items-center gap-4">
          <span>{files.length} file(s)</span>
          <span>{messages.length} message(s)</span>
        </div>
        <div>
          {config?.app_id}
        </div>
      </div>
    </div>
  );
}
