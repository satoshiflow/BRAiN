"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import React, { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  useTemplates,
  useDeleteTemplate,
  useTemplateCategories,
} from "@/hooks/useMissionTemplates";
import { MissionTemplate } from "@/lib/missionTemplatesApi";
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Plus,
  Search,
  MoreVertical,
  Edit,
  Trash2,
  Copy,
  Rocket,
  Layers,
} from "lucide-react";

export default function MissionTemplatesPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [templateToDelete, setTemplateToDelete] = useState<string | null>(null);

  const { data: templatesData, isLoading } = useTemplates(
    category === "all" ? undefined : category,
    search || undefined
  );
  const { data: categoriesData } = useTemplateCategories();
  const deleteMutation = useDeleteTemplate();

  const templates = templatesData?.items || [];
  const categories = categoriesData?.categories || [];

  const handleDelete = async () => {
    if (!templateToDelete) return;
    await deleteMutation.mutateAsync(templateToDelete);
    setTemplateToDelete(null);
  };

  if (isLoading) {
    return <PageSkeleton variant="list" />;
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">
            Mission Templates
          </h1>
          <p className="mt-1 text-sm text-neutral-400">
            Reusable mission templates for common workflows
          </p>
        </div>
        <Button
          onClick={() => router.push("/missions/templates/new")}
          className="bg-emerald-600 hover:bg-emerald-700"
        >
          <Plus className="mr-2 h-4 w-4" />
          New Template
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
          <Input
            placeholder="Search templates..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border-neutral-700 bg-neutral-900 pl-10 text-neutral-100 placeholder:text-neutral-500"
          />
        </div>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-full border-neutral-700 bg-neutral-900 text-neutral-100 sm:w-[200px]">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent className="border-neutral-700 bg-neutral-900">
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total Templates" value={templatesData?.total || 0} />
        <StatCard
          label="Categories"
          value={categories.length}
          icon={<Layers className="h-4 w-4" />}
        />
      </div>

      {/* Templates Grid */}
      {templates.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-neutral-800 bg-neutral-900/50 py-16">
          <div className="mb-4 rounded-full bg-neutral-800 p-4">
            <Layers className="h-8 w-8 text-neutral-500" />
          </div>
          <h3 className="text-lg font-medium text-white">No templates found</h3>
          <p className="mt-1 text-sm text-neutral-400">
            {search || category !== "all"
              ? "Try adjusting your filters"
              : "Create your first template to get started"}
          </p>
          {!search && category === "all" && (
            <Button
              onClick={() => router.push("/missions/templates/new")}
              className="mt-4 bg-emerald-600 hover:bg-emerald-700"
            >
              <Plus className="mr-2 h-4 w-4" />
              Create Template
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onEdit={() => router.push(`/missions/templates/${template.id}/edit`)}
              onDelete={() => setTemplateToDelete(template.id)}
              onInstantiate={() => router.push(`/missions?template=${template.id}`)}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      <AlertDialog
        open={!!templateToDelete}
        onOpenChange={() => setTemplateToDelete(null)}
      >
        <AlertDialogContent className="border-neutral-800 bg-neutral-900">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">
              Delete Template
            </AlertDialogTitle>
            <AlertDialogDescription className="text-neutral-400">
              Are you sure you want to delete this template? This action cannot
              be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-neutral-700 bg-neutral-800 text-neutral-200 hover:bg-neutral-700">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
      <div className="flex items-center gap-2">
        {icon && <span className="text-neutral-500">{icon}</span>}
        <span className="text-xs text-neutral-400">{label}</span>
      </div>
      <div className="mt-1 text-xl font-semibold text-white">{value}</div>
    </div>
  );
}

function TemplateCard({
  template,
  onEdit,
  onDelete,
  onInstantiate,
}: {
  template: MissionTemplate;
  onEdit: () => void;
  onDelete: () => void;
  onInstantiate: () => void;
}) {
  const stepCount = template.steps?.length || 0;
  const variableCount = Object.keys(template.variables || {}).length;

  return (
    <Card className="border-neutral-800 bg-neutral-900/70 transition-colors hover:border-neutral-700">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 pr-2">
            <CardTitle className="text-base font-semibold text-white line-clamp-1">
              {template.name}
            </CardTitle>
            <CardDescription className="mt-1 text-xs text-neutral-400 line-clamp-2">
              {template.description || "No description"}
            </CardDescription>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-neutral-400 hover:bg-neutral-800 hover:text-white"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="border-neutral-700 bg-neutral-900"
            >
              <DropdownMenuItem
                onClick={onEdit}
                className="text-neutral-200 focus:bg-neutral-800 focus:text-white"
              >
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={onInstantiate}
                className="text-emerald-400 focus:bg-neutral-800 focus:text-emerald-400"
              >
                <Rocket className="mr-2 h-4 w-4" />
                Create Mission
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={onDelete}
                className="text-red-400 focus:bg-neutral-800 focus:text-red-400"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-center gap-4 text-xs text-neutral-500">
          <span className="inline-flex items-center rounded-full bg-neutral-800 px-2 py-1 text-neutral-300">
            {template.category}
          </span>
          <span>{stepCount} step{stepCount !== 1 ? "s" : ""}</span>
          <span>{variableCount} variable{variableCount !== 1 ? "s" : ""}</span>
        </div>
      </CardContent>
    </Card>
  );
}
