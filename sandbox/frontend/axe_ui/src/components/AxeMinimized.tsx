/**
 * AxeMinimized - Minimized Widget State
 * 60x60px floating avatar/icon
 */

'use client';

import React from 'react';
import { Bot } from 'lucide-react';
import { cn } from '../utils/cn';

interface AxeMinimizedProps {
  onClick: () => void;
  theme: 'dark' | 'light';
}

export function AxeMinimized({ onClick, theme }: AxeMinimizedProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-14 h-14 rounded-full shadow-lg',
        'flex items-center justify-center',
        'transition-all duration-200',
        'hover:scale-110 hover:shadow-xl',
        'active:scale-95',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
        theme === 'dark'
          ? 'bg-primary text-primary-foreground'
          : 'bg-white text-primary border border-gray-200'
      )}
      aria-label="Open AXE Assistant"
    >
      <Bot className="w-7 h-7" />
    </button>
  );
}
