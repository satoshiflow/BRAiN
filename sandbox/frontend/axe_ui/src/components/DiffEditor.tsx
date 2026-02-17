/**
 * DiffEditor - Monaco Diff Editor Wrapper
 * Side-by-side code diff view for Apply/Reject workflow
 */

'use client';

import React from 'react';
import { DiffEditor as MonacoDiffEditor } from '@monaco-editor/react';
import type { DiffEditorProps } from '../types';

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
        automaticLayout: true,
        // Diff-specific options
        enableSplitViewResizing: true,
        renderOverviewRuler: false,
        ignoreTrimWhitespace: false,
        // Disable editing in diff view
        renderValidationDecorations: 'on',
        // Line numbers
        lineNumbers: 'on',
        // Folding
        folding: false,
        // Word wrap
        wordWrap: 'on'
      }}
      loading={
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      }
    />
  );
}
