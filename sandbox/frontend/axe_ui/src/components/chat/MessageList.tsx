'use client';

import { cn } from '@/src/utils/cn';

export interface ChatMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface MessageListProps {
  messages: ChatMessageItem[];
  loading?: boolean;
}

export function MessageList({ messages, loading = false }: MessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
        >
          <div
            className={cn(
              'max-w-[80%] rounded-lg p-4',
              message.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-100 border border-slate-700'
            )}
          >
            <div className="flex items-start gap-3">
              {message.role === 'assistant' && <span className="text-2xl">🤖</span>}
              <div className="flex-1">
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                <p className="text-xs opacity-70 mt-2">{message.timestamp.toLocaleTimeString()}</p>
              </div>
            </div>
          </div>
        </div>
      ))}

      {loading && (
        <div className="flex justify-start">
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" />
                <div className="w-2 h-2 rounded-full bg-slate-500 animate-bounce [animation-delay:0.1s]" />
                <div className="w-2 h-2 rounded-full bg-slate-500 animate-bounce [animation-delay:0.2s]" />
              </div>
              <span className="text-sm text-slate-400">AXE is thinking...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
