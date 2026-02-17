/**
 * FileTabs - File Tabs Component
 * Tab list for open files in CANVAS
 */

'use client';

import React from 'react';
import { X } from 'lucide-react';
import { cn } from '../utils/cn';
import type { AxeFile } from '../types';

interface FileTabsProps {
  files: AxeFile[];
  activeFileId: string | null;
  onSelectFile: (fileId: string) => void;
  onCloseFile: (fileId: string) => void;
}

export function FileTabs({
  files,
  activeFileId,
  onSelectFile,
  onCloseFile
}: FileTabsProps) {
  if (files.length === 0) {
    return (
      <div className="h-10 border-b border-border flex items-center px-4 text-sm text-muted-foreground">
        No files open
      </div>
    );
  }

  return (
    <div className="h-10 border-b border-border flex items-center overflow-x-auto scrollbar-thin">
      {files.map((file) => (
        <div
          key={file.id}
          className={cn(
            'group flex items-center gap-2 px-4 h-full border-r border-border cursor-pointer transition-colors',
            'hover:bg-accent',
            activeFileId === file.id
              ? 'bg-background text-foreground'
              : 'bg-muted text-muted-foreground'
          )}
          onClick={() => onSelectFile(file.id)}
        >
          {/* File Name */}
          <span className="text-sm font-mono">
            {file.name}
            {file.is_dirty && <span className="text-yellow-500 ml-1">●</span>}
          </span>

          {/* Close Button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCloseFile(file.id);
            }}
            className={cn(
              'opacity-0 group-hover:opacity-100 transition-opacity',
              'hover:bg-destructive/10 rounded p-0.5',
              activeFileId === file.id && 'opacity-100'
            )}
            aria-label={`Close ${file.name}`}
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}
    </div>
  );
}
