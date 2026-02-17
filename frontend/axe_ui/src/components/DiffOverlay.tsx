/**
 * DiffOverlay - Apply/Reject Code Diff UI
 * Overlay showing code diff with apply/reject buttons
 */

'use client';

import React, { useState } from 'react';
import { Check, X, Eye, EyeOff } from 'lucide-react';
import { DiffEditor } from './DiffEditor';
import { cn } from '../utils/cn';
import type { DiffOverlayProps } from '../types';

export function DiffOverlay({ diff, onApply, onReject }: DiffOverlayProps) {
  const [showDiff, setShowDiff] = useState(true);

  return (
    <div className="absolute inset-0 bg-background/95 z-50 flex items-center justify-center p-8">
      <div className="w-full max-w-5xl h-[80vh] flex flex-col bg-card border border-border rounded-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h3 className="text-lg font-semibold">AXE Code Suggestion</h3>
            <p className="text-sm text-muted-foreground mt-1">
              {diff.fileName} • {diff.description}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Toggle Diff View */}
            <button
              onClick={() => setShowDiff(!showDiff)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-md border transition-colors',
                'hover:bg-accent'
              )}
            >
              {showDiff ? (
                <>
                  <EyeOff className="w-4 h-4 inline mr-2" />
                  Hide Diff
                </>
              ) : (
                <>
                  <Eye className="w-4 h-4 inline mr-2" />
                  Show Diff
                </>
              )}
            </button>

            {/* Reject Button */}
            <button
              onClick={onReject}
              className={cn(
                'px-3 py-1.5 text-sm rounded-md transition-colors',
                'bg-destructive text-destructive-foreground',
                'hover:bg-destructive/90'
              )}
            >
              <X className="w-4 h-4 inline mr-2" />
              Reject
            </button>

            {/* Apply Button */}
            <button
              onClick={onApply}
              className={cn(
                'px-3 py-1.5 text-sm rounded-md transition-colors',
                'bg-primary text-primary-foreground',
                'hover:bg-primary/90'
              )}
            >
              <Check className="w-4 h-4 inline mr-2" />
              Apply Changes
            </button>
          </div>
        </div>

        {/* Diff Content */}
        <div className="flex-1 overflow-hidden">
          {showDiff ? (
            <DiffEditor
              original={diff.oldContent}
              modified={diff.newContent}
              language={diff.language}
              theme="vs-dark"
              readOnly
            />
          ) : (
            <div className="h-full overflow-auto p-6 font-mono text-sm">
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                  New Code:
                </h4>
                <pre className="bg-muted p-4 rounded-md overflow-x-auto">
                  <code>{diff.newContent}</code>
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-muted/30">
          <p className="text-xs text-muted-foreground">
            💡 <strong>Tip:</strong> Review the changes carefully before
            applying. Press <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs">Esc</kbd> to
            reject.
          </p>
        </div>
      </div>
    </div>
  );
}
