"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useSkills, useDeleteSkill, useSkillCategories } from "@/hooks/useSkills";
import { Skill, SkillCategory } from "@/lib/skillsApi";
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
import { Badge } from "@/components/ui/badge";
import {
  Plus,
  Search,
  MoreVertical,
  Edit,
  Trash2,
  Play,
  Puzzle,
  Globe,
  FileText,
  MessageSquare,
  Brain,
  Zap,
} from "lucide-react";

const categoryIcons: Record<SkillCategory, React.ElementType> = {
  api: Globe,
  file: FileText,
  communication: MessageSquare,
  analysis: Brain,
  custom: Zap,
};

const categoryColors: Record<SkillCategory, string> = {
  api: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  file: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  communication: "bg-green-500/10 text-green-400 border-green-500/20",
  analysis: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  custom: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

export default function SkillsLibraryPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [skillToDelete, setSkillToDelete] = useState<string | null>(null);

  // Stabilize query parameters to prevent refetching loops
  const queryCategory = category === "all" ? undefined : (category as SkillCategory);
  const querySearch = search || undefined;
  
  const { data: skillsData, isLoading } = useSkills(queryCategory, querySearch);
  const { data: categoriesData } = useSkillCategories();
  const deleteMutation = useDeleteSkill();

  const skills = skillsData?.items || [];
  const categories = categoriesData?.categories || [];

  const handleDelete = async () => {
    if (!skillToDelete) return;
    await deleteMutation.mutateAsync(skillToDelete);
    setSkillToDelete(null);
  };

  if (isLoading) {
    return <PageSkeleton variant="list" />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Skills Library</h1>
          <p className="text-muted-foreground">
            PicoClaw-style skills for agent capabilities
          </p>
        </div>
        <Button
          onClick={() => router.push("/agents/skills/new")}
          className="shrink-0 gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Skill
        </Button>
      </div>

      {/* Filters */}
      <Card className="border-border/50">
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search skills..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="w-full sm:w-[200px]">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Skills Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {skills.map((skill) => (
          <SkillCard
            key={skill.id}
            skill={skill}
            onDelete={() => setSkillToDelete(skill.id)}
            onEdit={() => router.push(`/agents/skills/${skill.id}`)}
            onExecute={() => router.push(`/agents/skills/${skill.id}?execute=true`)}
          />
        ))}
      </div>

      {skills.length === 0 && (
        <Card className="border-border/50">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Puzzle className="h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 text-lg font-semibold">No skills found</h3>
            <p className="text-muted-foreground">
              {search || category !== "all"
                ? "Try adjusting your filters"
                : "Create your first skill to get started"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Delete Dialog */}
      <AlertDialog
        open={!!skillToDelete}
        onOpenChange={() => setSkillToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Skill</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this skill? This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function SkillCard({
  skill,
  onDelete,
  onEdit,
  onExecute,
}: {
  skill: Skill;
  onDelete: () => void;
  onEdit: () => void;
  onExecute: () => void;
}) {
  const CategoryIcon = categoryIcons[skill.category];

  return (
    <Card className="group relative border-border/50 bg-card/50 transition-colors hover:border-primary/50 hover:bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`rounded-lg p-2 ${categoryColors[skill.category]}`}>
              <CategoryIcon className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-base">{skill.name}</CardTitle>
              <CardDescription className="text-xs">
                {skill.handler_path}
              </CardDescription>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onExecute}>
                <Play className="mr-2 h-4 w-4" />
                Execute
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onEdit}>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={onDelete}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="mb-3 text-sm text-muted-foreground line-clamp-2">
          {skill.description || "No description"}
        </p>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={categoryColors[skill.category]}
          >
            {skill.category}
          </Badge>
          {skill.enabled ? (
            <Badge variant="outline" className="border-green-500/20 text-green-400">
              Enabled
            </Badge>
          ) : (
            <Badge variant="outline" className="border-gray-500/20 text-gray-400">
              Disabled
            </Badge>
          )}
        </div>
        {skill.manifest?.parameters && skill.manifest.parameters.length > 0 && (
          <div className="mt-3 text-xs text-muted-foreground">
            {skill.manifest.parameters.length} parameter
            {skill.manifest.parameters.length !== 1 ? "s" : ""}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
