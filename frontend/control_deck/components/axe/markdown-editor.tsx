'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: string;
}

export function MarkdownEditor({
  value,
  onChange,
  placeholder = 'Write markdown...',
  minHeight = '400px',
}: MarkdownEditorProps) {
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit');

  return (
    <div className="space-y-2">
      {/* Mobile: Tabs */}
      <div className="md:hidden">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList className="w-full grid grid-cols-2">
            <TabsTrigger value="edit">Edit</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>

          <TabsContent value="edit" className="mt-2">
            <Textarea
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder={placeholder}
              className="font-mono text-sm resize-y"
              style={{ minHeight }}
            />
          </TabsContent>

          <TabsContent value="preview" className="mt-2">
            <Card className="p-4 prose prose-sm max-w-none dark:prose-invert" style={{ minHeight }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {value || '*No content*'}
              </ReactMarkdown>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Desktop: Side-by-side */}
      <div className="hidden md:grid md:grid-cols-2 gap-4">
        <div>
          <p className="text-sm font-medium mb-2">Markdown</p>
          <Textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="font-mono text-sm resize-y"
            style={{ minHeight }}
          />
        </div>
        <div>
          <p className="text-sm font-medium mb-2">Preview</p>
          <Card className="p-4 prose prose-sm max-w-none dark:prose-invert overflow-auto" style={{ minHeight }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {value || '*No content*'}
            </ReactMarkdown>
          </Card>
        </div>
      </div>
    </div>
  );
}
