"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useCreateKnowledgeDocument } from '@/hooks/useAxeKnowledge';
import { MarkdownEditor } from '@/components/axe/markdown-editor';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowLeft, Save, Loader2 } from 'lucide-react';
import { DocumentCategory } from '@/lib/axeKnowledgeApi';

export default function NewKnowledgePage() {
  const router = useRouter();
  const createMutation = useCreateKnowledgeDocument();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: 'custom' as DocumentCategory,
    content: '',
    tags: '',
    importance_score: 5,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await createMutation.mutateAsync({
        name: formData.name,
        description: formData.description || undefined,
        category: formData.category,
        content: formData.content,
        tags: formData.tags ? formData.tags.split(',').map((t) => t.trim()) : [],
        importance_score: formData.importance_score,
      });

      router.push('/axe/knowledge');
    } catch (error) {
      console.error('Failed to create document:', error);
    }
  };

  return (
    <div className="space-y-4 p-4 md:p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/axe/knowledge">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">New Document</h1>
          <p className="text-sm text-muted-foreground">
            Add knowledge to AXE&apos;s database
          </p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info Card */}
        <Card>
          <CardHeader>
            <CardTitle>Document Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="BRAiN Architecture Overview"
                required
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="High-level overview of system architecture"
                rows={2}
                className="resize-none"
              />
            </div>

            {/* Category & Score - Grid on desktop */}
            <div className="grid gap-4 sm:grid-cols-2">
              {/* Category */}
              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select
                  value={formData.category}
                  onValueChange={(val) =>
                    setFormData({ ...formData, category: val as DocumentCategory })
                  }
                >
                  <SelectTrigger id="category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="system">System</SelectItem>
                    <SelectItem value="domain">Domain</SelectItem>
                    <SelectItem value="procedure">Procedure</SelectItem>
                    <SelectItem value="faq">FAQ</SelectItem>
                    <SelectItem value="reference">Reference</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Importance Score */}
              <div className="space-y-2">
                <Label htmlFor="importance">
                  Importance Score: {formData.importance_score}
                </Label>
                <Slider
                  id="importance"
                  min={0}
                  max={10}
                  step={0.5}
                  value={[formData.importance_score]}
                  onValueChange={([val]) =>
                    setFormData({ ...formData, importance_score: val })
                  }
                  className="py-4"
                />
              </div>
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <Label htmlFor="tags">Tags</Label>
              <Input
                id="tags"
                value={formData.tags}
                onChange={(e) =>
                  setFormData({ ...formData, tags: e.target.value })
                }
                placeholder="architecture, core, system"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated tags
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Content Card */}
        <Card>
          <CardHeader>
            <CardTitle>Content (Markdown)</CardTitle>
          </CardHeader>
          <CardContent>
            <MarkdownEditor
              value={formData.content}
              onChange={(val) => setFormData({ ...formData, content: val })}
              placeholder="# Document Title&#10;&#10;Your markdown content here..."
            />
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex flex-col-reverse sm:flex-row gap-3">
          <Link href="/axe/knowledge" className="w-full sm:w-auto">
            <Button type="button" variant="outline" className="w-full">
              Cancel
            </Button>
          </Link>
          <Button
            type="submit"
            disabled={createMutation.isPending}
            className="w-full sm:w-auto sm:ml-auto"
          >
            {createMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Create Document
          </Button>
        </div>
      </form>
    </div>
  );
}
