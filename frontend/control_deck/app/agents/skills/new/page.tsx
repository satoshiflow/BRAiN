"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useCreateSkill, useSkillCategories } from "@/hooks/useSkills";
import { SkillCategory, SkillManifest, SkillParameter } from "@/lib/skillsApi";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Plus,
  Trash2,
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

const builtinHandlers: Record<string, string> = {
  "HTTP Request": "app.modules.skills.builtins.http_request",
  "File Read": "app.modules.skills.builtins.file_read",
  "File Write": "app.modules.skills.builtins.file_write",
  "Shell Command": "app.modules.skills.builtins.shell_command",
  "Web Search": "app.modules.skills.builtins.web_search",
  "Custom": "custom",
};

export default function NewSkillPage() {
  const router = useRouter();
  const createMutation = useCreateSkill();
  const { data: categoriesData } = useSkillCategories();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<SkillCategory>("custom");
  const [handler, setHandler] = useState("custom");
  const [customHandler, setCustomHandler] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [parameters, setParameters] = useState<SkillParameter[]>([]);
  const [returnType, setReturnType] = useState("object");
  const [returnDesc, setReturnDesc] = useState("");

  const categories = categoriesData?.categories || [
    "api",
    "file",
    "communication",
    "analysis",
    "custom",
  ];

  const handleAddParameter = () => {
    setParameters([
      ...parameters,
      {
        name: "",
        type: "string",
        description: "",
        required: true,
      },
    ]);
  };

  const handleRemoveParameter = (index: number) => {
    setParameters(parameters.filter((_, i) => i !== index));
  };

  const handleParamChange = (
    index: number,
    field: keyof SkillParameter,
    value: unknown
  ) => {
    const newParams = [...parameters];
    newParams[index] = { ...newParams[index], [field]: value };
    setParameters(newParams);
  };

  const handleSubmit = async () => {
    const manifest: SkillManifest = {
      name,
      description,
      category,
      version: "1.0.0",
      parameters,
      returns: {
        type: returnType,
        description: returnDesc,
      },
    };

    const handlerPath = handler === "custom" ? customHandler : handler;

    try {
      await createMutation.mutateAsync({
        name,
        description,
        category,
        manifest,
        handler_path: handlerPath,
        enabled,
      });
      router.push("/agents/skills");
    } catch (error) {
      console.error("Failed to create skill:", error);
    }
  };

  const isValid =
    name.trim() &&
    (handler !== "custom" || customHandler.trim()) &&
    parameters.every((p) => p.name.trim());

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="icon"
          onClick={() => router.push("/agents/skills")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Create Skill</h1>
          <p className="text-sm text-muted-foreground">
            Define a new PicoClaw-style skill
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Basic Info */}
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Name, description, and category for the skill
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                placeholder="e.g., HTTP Request"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="What does this skill do?"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Category *</Label>
              <Select
                value={category}
                onValueChange={(v) => setCategory(v as SkillCategory)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((cat) => {
                    const Icon = categoryIcons[cat as SkillCategory];
                    return (
                      <SelectItem key={cat} value={cat}>
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4" />
                          {cat.charAt(0).toUpperCase() + cat.slice(1)}
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Handler *</Label>
              <Select value={handler} onValueChange={setHandler}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(builtinHandlers).map(([label, path]) => (
                    <SelectItem key={path} value={path}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {handler === "custom" && (
                <Input
                  placeholder="e.g., myapp.skills.custom_handler"
                  value={customHandler}
                  onChange={(e) => setCustomHandler(e.target.value)}
                  className="mt-2"
                />
              )}
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border/50 p-4">
              <div className="space-y-0.5">
                <Label>Enabled</Label>
                <p className="text-sm text-muted-foreground">
                  Allow agents to use this skill
                </p>
              </div>
              <Switch checked={enabled} onCheckedChange={setEnabled} />
            </div>
          </CardContent>
        </Card>

        {/* Parameters */}
        <Card className="border-border/50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Parameters</CardTitle>
                <CardDescription>Define input parameters</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={handleAddParameter}>
                <Plus className="mr-2 h-4 w-4" />
                Add
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {parameters.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No parameters defined. Click "Add" to create one.
              </p>
            ) : (
              parameters.map((param, index) => (
                <div
                  key={index}
                  className="space-y-3 rounded-lg border border-border/50 p-4"
                >
                  <div className="flex items-center justify-between">
                    <Badge variant="outline">Param {index + 1}</Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveParameter(index)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                  <div className="grid gap-3">
                    <Input
                      placeholder="Parameter name"
                      value={param.name}
                      onChange={(e) =>
                        handleParamChange(index, "name", e.target.value)
                      }
                    />
                    <Select
                      value={param.type}
                      onValueChange={(v) =>
                        handleParamChange(index, "type", v)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="string">String</SelectItem>
                        <SelectItem value="number">Number</SelectItem>
                        <SelectItem value="boolean">Boolean</SelectItem>
                        <SelectItem value="object">Object</SelectItem>
                        <SelectItem value="array">Array</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      placeholder="Description"
                      value={param.description}
                      onChange={(e) =>
                        handleParamChange(index, "description", e.target.value)
                      }
                    />
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={param.required}
                        onCheckedChange={(v) =>
                          handleParamChange(index, "required", v)
                        }
                        id={`required-${index}`}
                      />
                      <Label htmlFor={`required-${index}`}>Required</Label>
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Returns */}
        <Card className="border-border/50 lg:col-span-2">
          <CardHeader>
            <CardTitle>Return Value</CardTitle>
            <CardDescription>Define the output type</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Return Type</Label>
              <Select value={returnType} onValueChange={setReturnType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="string">String</SelectItem>
                  <SelectItem value="number">Number</SelectItem>
                  <SelectItem value="boolean">Boolean</SelectItem>
                  <SelectItem value="object">Object</SelectItem>
                  <SelectItem value="array">Array</SelectItem>
                  <SelectItem value="void">Void</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                placeholder="What does this skill return?"
                value={returnDesc}
                onChange={(e) => setReturnDesc(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-4">
        <Button
          variant="outline"
          onClick={() => router.push("/agents/skills")}
        >
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={!isValid || createMutation.isPending}>
          {createMutation.isPending ? "Creating..." : "Create Skill"}
        </Button>
      </div>
    </div>
  );
}
