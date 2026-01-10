/**
 * AxeExpanded - Expanded Widget State
 * 320x480px chat panel
 */

'use client';

import React, { useState } from 'react';
import { X, Minimize2, Maximize2, Send, Wifi, WifiOff } from 'lucide-react';
import { useAxeStore } from '../store/axeStore';
import { useAxeWebSocket } from '../hooks/useAxeWebSocket';
import { generateMessageId } from '../utils/id';
import { cn } from '../utils/cn';
import type { AxeMode, AxeMessage } from '../types';

interface AxeExpandedProps {
  mode: AxeMode;
  onModeChange: (mode: AxeMode) => void;
  onMinimize: () => void;
  onOpenCanvas: () => void;
  locale: string;
  theme: 'dark' | 'light';
}

export function AxeExpanded({
  mode,
  onModeChange,
  onMinimize,
  onOpenCanvas,
  locale,
  theme
}: AxeExpandedProps) {
  const [input, setInput] = useState('');
  const { messages, addMessage, config, sessionId } = useAxeStore();

  // ============================================================================
  // WebSocket Connection
  // ============================================================================
  const { isConnected, sendChat } = useAxeWebSocket({
    backendUrl: process.env.NEXT_PUBLIC_BRAIN_API_BASE || 'http://localhost:8000',
    sessionId: sessionId,
    onConnected: () => console.log('[AxeExpanded] WebSocket connected'),
    onDisconnected: () => console.log('[AxeExpanded] WebSocket disconnected'),
    onError: (error) => console.error('[AxeExpanded] WebSocket error:', error)
  });

  // ============================================================================
  // Send Message Handler
  // ============================================================================
  const handleSend = () => {
    if (!input.trim() || !isConnected) return;

    const userMessage: AxeMessage = {
      id: generateMessageId(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    };

    addMessage(userMessage);
    setInput('');

    // Send via WebSocket
    sendChat(userMessage.content, { mode });
  };

  return (
    <div
      className={cn(
        'w-80 h-[480px] rounded-lg shadow-xl',
        'flex flex-col overflow-hidden',
        'border',
        theme === 'dark'
          ? 'bg-gray-900 border-gray-700'
          : 'bg-white border-gray-200'
      )}
    >
      {/* ========================================================================
          Header
      ======================================================================== */}
      <div
        className={cn(
          'h-14 px-4 flex items-center justify-between border-b',
          theme === 'dark' ? 'border-gray-700' : 'border-gray-200'
        )}
      >
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-sm font-semibold">
            A
          </div>
          <div>
            <h3 className="text-sm font-semibold flex items-center gap-1.5">
              {config?.display_name || 'AXE Assistant'}
              {isConnected ? (
                <Wifi className="w-3 h-3 text-green-500" title="Connected" />
              ) : (
                <WifiOff className="w-3 h-3 text-red-500" title="Reconnecting..." />
              )}
            </h3>
            <p className="text-xs text-muted-foreground capitalize">{mode}</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {config?.ui.enable_canvas && (
            <button
              onClick={onOpenCanvas}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
              aria-label="Open Canvas"
              title="Open Canvas (Builder Mode)"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onMinimize}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
            aria-label="Minimize"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
          <button
            onClick={onMinimize}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ========================================================================
          Messages Area
      ======================================================================== */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center">
            <div>
              <p className="text-muted-foreground mb-2">
                👋 Hi! I'm AXE, your AI assistant.
              </p>
              <p className="text-sm text-muted-foreground">
                How can I help you today?
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
                  'max-w-[80%] rounded-lg px-3 py-2',
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : theme === 'dark'
                    ? 'bg-gray-800'
                    : 'bg-gray-100'
                )}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          ))
        )}
      </div>

      {/* ========================================================================
          Input Area
      ======================================================================== */}
      <div
        className={cn(
          'p-4 border-t',
          theme === 'dark' ? 'border-gray-700' : 'border-gray-200'
        )}
      >
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
            placeholder="Type your message..."
            rows={2}
            className={cn(
              'flex-1 resize-none rounded-md px-3 py-2 text-sm',
              'border outline-none focus:ring-2 focus:ring-primary',
              theme === 'dark'
                ? 'bg-gray-800 border-gray-700 text-white placeholder:text-gray-400'
                : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-500'
            )}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !isConnected}
            className={cn(
              'p-2 rounded-md transition-colors',
              'bg-primary text-primary-foreground',
              'hover:bg-primary/90',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
            aria-label="Send message"
            title={!isConnected ? 'WebSocket disconnected' : 'Send message'}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {isConnected ? (
            <>Press Enter to send, Shift+Enter for new line</>
          ) : (
            <span className="text-red-500">⚠ Reconnecting to server...</span>
          )}
        </p>
      </div>
    </div>
  );
}
