/**
 * Course Factory Dashboard
 *
 * Template system for courses, learning paths, and educational content
 */

"use client";

import React, { useState } from 'react';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import {
  useCourseStats,
  useCourseTemplates,
  useCreateCourseTemplate,
  useDeleteCourseTemplate,
  useDuplicateCourseTemplate,
  usePublishCourseTemplate,
  type CourseTemplate,
  type DifficultyLevel,
  type CourseStatus,
} from '@/hooks/useCourseFactory';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Alert, AlertDescription } from '@/components/ui/alert';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Button } from '@/components/ui/button';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Input } from '@/components/ui/input';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Label } from '@/components/ui/label';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Textarea } from '@/components/ui/textarea';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Badge } from '@/components/ui/badge';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Loader2, BookOpen, Plus, Edit, Copy, Trash2, CheckCircle2, AlertTriangle, GraduationCap, Clock, Target } from 'lucide-react';
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";

export default function CourseFactoryPage() {
  const { data: stats, isLoading: statsLoading } = useCourseStats();
  
  // Show loading skeleton
  if (isLoading) {
    return <PageSkeleton variant="list" />;
  }
  const { data: templates, isLoading: templatesLoading, error: templatesError } = useCourseTemplates();
  
  // Show loading skeleton
  if (isLoading) {
    return <PageSkeleton variant="list" />;
  }
  const [searchQuery, setSearchQuery] = useState('');

  if (statsLoading || templatesLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (templatesError) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold">Course Factory</h1>
          <p className="text-muted-foreground">
            Template system for educational content
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load course templates: {templatesError.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Filter templates by search query
  const filteredTemplates = templates?.filter((t) =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.category.toLowerCase().includes(searchQuery.toLowerCase())
  ) ?? [];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Course Factory</h1>
        <p className="text-muted-foreground">
          Create and manage course templates for educational content
        </p>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Templates</CardTitle>
              <BookOpen className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_templates}</div>
              <p className="text-xs text-muted-foreground">
                {stats.published} published, {stats.draft} draft
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Modules</CardTitle>
              <GraduationCap className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_modules}</div>
              <p className="text-xs text-muted-foreground">
                {stats.total_lessons} lessons
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
              <Clock className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.average_duration_hours?.toFixed(1)}h</div>
              <p className="text-xs text-muted-foreground">
                Per course template
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Categories</CardTitle>
              <Target className="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{Object.keys(stats.templates_by_category).length}</div>
              <p className="text-xs text-muted-foreground">
                Active categories
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Category Distribution */}
      {stats && Object.keys(stats.templates_by_category).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Templates by Category</CardTitle>
            <CardDescription>Distribution across categories</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.templates_by_category).map(([category, count]) => (
                <Badge key={category} variant="secondary">
                  {category}: {count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <Tabs defaultValue="templates" className="space-y-4">
        <TabsList>
          <TabsTrigger value="templates">
            <BookOpen className="h-4 w-4 mr-2" />
            Templates
          </TabsTrigger>
          <TabsTrigger value="create">
            <Plus className="h-4 w-4 mr-2" />
            Create Template
          </TabsTrigger>
        </TabsList>

        <TabsContent value="templates">
          {/* Search */}
          <div className="mb-4">
            <Input
              placeholder="Search templates by name, description, or category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="max-w-md"
            />
          </div>

          <TemplatesList templates={filteredTemplates} />
        </TabsContent>

        <TabsContent value="create">
          <CreateTemplateForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================================
// Templates List Component
// ============================================================================

function TemplatesList({ templates }: { templates: CourseTemplate[] }) {
  const deleteMutation = useDeleteCourseTemplate();
  const duplicateMutation = useDuplicateCourseTemplate();
  const publishMutation = usePublishCourseTemplate();

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this course template?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleDuplicate = (id: string, name: string) => {
    const newName = prompt('Enter name for duplicated template:', `${name} (Copy)`);
    if (newName) {
      duplicateMutation.mutate({ id, newName });
    }
  };

  const handlePublish = (id: string) => {
    if (confirm('Publish this course template?')) {
      publishMutation.mutate(id);
    }
  };

  const getDifficultyColor = (difficulty: DifficultyLevel) => {
    switch (difficulty) {
      case 'beginner':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'intermediate':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'advanced':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'expert':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
    }
  };

  const getStatusColor = (status: CourseStatus) => {
    switch (status) {
      case 'published':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'draft':
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
      case 'archived':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
    }
  };

  if (templates.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center p-8">
          <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No course templates found</p>
          <p className="text-xs text-muted-foreground mt-1">
            {templates.length === 0 ? 'Create your first template to get started' : 'Try a different search term'}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {templates.map((template) => (
        <Card key={template.id}>
          <CardContent className="p-6">
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{template.name}</h3>
                  <p className="text-xs text-muted-foreground mt-1">{template.category}</p>
                </div>
                <div className="flex flex-col gap-1">
                  <Badge variant="outline" className={getDifficultyColor(template.difficulty)}>
                    {template.difficulty}
                  </Badge>
                  <Badge variant="outline" className={getStatusColor(template.status)}>
                    {template.status}
                  </Badge>
                </div>
              </div>

              <p className="text-sm text-muted-foreground line-clamp-2">
                {template.description}
              </p>

              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <GraduationCap className="h-3 w-3" />
                  <span>{template.modules.length} modules</span>
                </div>
                {template.duration_hours && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{template.duration_hours}h</span>
                  </div>
                )}
              </div>

              {template.tags && template.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {template.tags.slice(0, 3).map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  {template.tags.length > 3 && (
                    <Badge variant="secondary" className="text-xs">
                      +{template.tags.length - 3}
                    </Badge>
                  )}
                </div>
              )}

              {template.learning_objectives && template.learning_objectives.length > 0 && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                    Learning Objectives
                  </summary>
                  <ul className="mt-2 space-y-1 list-disc list-inside">
                    {template.learning_objectives.slice(0, 3).map((obj, idx) => (
                      <li key={idx}>{obj}</li>
                    ))}
                  </ul>
                </details>
              )}

              <div className="flex gap-2 pt-2">
                {template.status === 'draft' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePublish(template.id)}
                    disabled={publishMutation.isPending}
                  >
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Publish
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDuplicate(template.id, template.name)}
                  disabled={duplicateMutation.isPending}
                >
                  <Copy className="h-3 w-3 mr-1" />
                  Duplicate
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleDelete(template.id)}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>

              {template.usage_count !== undefined && (
                <p className="text-xs text-muted-foreground">
                  Used {template.usage_count} times
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// Create Template Form Component
// ============================================================================

function CreateTemplateForm() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [difficulty, setDifficulty] = useState<DifficultyLevel>('intermediate');
  const [prerequisites, setPrerequisites] = useState('');
  const [objectives, setObjectives] = useState('');
  const [tags, setTags] = useState('');
  const createMutation = useCreateCourseTemplate();

  const handleCreate = () => {
    if (!name.trim() || !description.trim() || !category.trim()) return;

    const prereqArray = prerequisites
      .split('\n')
      .map((p) => p.trim())
      .filter((p) => p.length > 0);

    const objArray = objectives
      .split('\n')
      .map((o) => o.trim())
      .filter((o) => o.length > 0);

    const tagsArray = tags
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    createMutation.mutate(
      {
        name,
        description,
        category,
        difficulty,
        status: 'draft',
        prerequisites: prereqArray.length > 0 ? prereqArray : undefined,
        learning_objectives: objArray.length > 0 ? objArray : undefined,
        tags: tagsArray.length > 0 ? tagsArray : undefined,
        modules: [],
      },
      {
        onSuccess: () => {
          // Reset form
          setName('');
          setDescription('');
          setCategory('');
          setDifficulty('intermediate');
          setPrerequisites('');
          setObjectives('');
          setTags('');
        },
      }
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Course Template</CardTitle>
        <CardDescription>
          Define a reusable course template for educational content
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Course Name</Label>
            <Input
              placeholder="e.g., Introduction to Python Programming"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Category</Label>
            <Input
              placeholder="e.g., Programming, AI/ML, Business"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Description</Label>
          <Textarea
            placeholder="Describe what this course teaches..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>

        <div className="space-y-2">
          <Label>Difficulty Level</Label>
          <div className="flex gap-2">
            {(['beginner', 'intermediate', 'advanced', 'expert'] as DifficultyLevel[]).map((d) => (
              <Badge
                key={d}
                variant={difficulty === d ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setDifficulty(d)}
              >
                {d.toUpperCase()}
              </Badge>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <Label>Prerequisites (one per line, optional)</Label>
          <Textarea
            placeholder="Basic computer skills&#10;Familiarity with text editors"
            value={prerequisites}
            onChange={(e) => setPrerequisites(e.target.value)}
            rows={3}
          />
        </div>

        <div className="space-y-2">
          <Label>Learning Objectives (one per line, optional)</Label>
          <Textarea
            placeholder="Understand Python syntax&#10;Write basic programs&#10;Work with data structures"
            value={objectives}
            onChange={(e) => setObjectives(e.target.value)}
            rows={4}
          />
        </div>

        <div className="space-y-2">
          <Label>Tags (comma-separated, optional)</Label>
          <Input
            placeholder="python, programming, beginner-friendly"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
        </div>

        <Alert>
          <AlertDescription className="text-xs">
            This template will be created as a draft. You can add modules and lessons after creation, then publish when ready.
          </AlertDescription>
        </Alert>

        <Button
          onClick={handleCreate}
          disabled={createMutation.isPending || !name.trim() || !description.trim() || !category.trim()}
          className="w-full"
        >
          {createMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating Template...
            </>
          ) : (
            <>
              <Plus className="mr-2 h-4 w-4" />
              Create Template
            </>
          )}
        </Button>

        {createMutation.isSuccess && (
          <Alert>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>Course template created successfully as draft</AlertDescription>
          </Alert>
        )}

        {createMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{createMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
