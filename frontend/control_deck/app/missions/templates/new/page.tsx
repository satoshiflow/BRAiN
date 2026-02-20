"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useCreateTemplate } from "@/hooks/useMissionTemplates";
import type { TemplateStep, TemplateVariable } from "@/lib/missionTemplatesApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Switch } from "@/components/ui/switch";
import {
  Plus,
  Trash2,
  GripVertical,
  ArrowUp,
  ArrowDown,
  Save,
  X,
} from "lucide-react";

export default function NewTemplatePage() {
  const router = useRouter();
  const createMutation = useCreateTemplate();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("general");
  const [steps, setSteps] = useState<TemplateStep[]>([
    { order: 1, action: "", config: {} },
  ]);
  const [variables, setVariables] = useState<
    { name: string; def: TemplateVariable }[]
  >([]);

  const handleAddStep = () => {
    setSteps([
      ...steps,
      { order: steps.length + 1, action: "", config: {} },
    ]);
  };

  const handleRemoveStep = (index: number) => {
    const newSteps = steps.filter((_, i) => i !== index);
    // Reorder remaining steps
    setSteps(
      newSteps.map((step, i) => ({ ...step, order: i + 1 }))
    );
  };

  const handleMoveStep = (index: number, direction: "up" | "down") => {
    if (direction === "up" && index === 0) return;
    if (direction === "down" && index === steps.length - 1) return;

    const newSteps = [...steps];
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    [newSteps[index], newSteps[targetIndex]] = [
      newSteps[targetIndex],
      newSteps[index],
    ];

    setSteps(newSteps.map((step, i) => ({ ...step, order: i + 1 })));
  };

  const handleUpdateStep = (
    index: number,
    field: keyof TemplateStep,
    value: string | Record<string, unknown>
  ) => {
    const newSteps = [...steps];
    newSteps[index] = { ...newSteps[index], [field]: value };
    setSteps(newSteps);
  };

  const handleAddVariable = () => {
    setVariables([
      ...variables,
      {
        name: "",
        def: { type: "string", required: true, description: "" },
      },
    ]);
  };

  const handleRemoveVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
  };

  const handleUpdateVariable = (
    index: number,
    field: string,
    value: unknown
  ) => {
    const newVariables = [...variables];
    if (field === "name") {
      newVariables[index].name = value as string;
    } else {
      newVariables[index].def = {
        ...newVariables[index].def,
        [field]: value,
      };
    }
    setVariables(newVariables);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Convert variables array to object
    const variablesObject = variables.reduce(
      (acc, { name, def: varDef }) => {
        if (name) acc[name] = varDef;
        return acc;
      },
      {} as Record<string, TemplateVariable>
    );

    await createMutation.mutateAsync({
      name,
      description,
      category,
      steps: steps.filter((s) => s.action.trim()),
      variables: variablesObject,
    });

    router.push("/missions/templates");
  };

  const isSubmitDisabled =
    !name.trim() || steps.every((s) => !s.action.trim());

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">New Template</h1>
          <p className="mt-1 text-sm text-neutral-400">
            Create a reusable mission template
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => router.push("/missions/templates")}
            className="border-neutral-700 bg-transparent text-neutral-300 hover:bg-neutral-800"
          >
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitDisabled || createMutation.isPending}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <Save className="mr-2 h-4 w-4" />
            {createMutation.isPending ? "Creating..." : "Create Template"}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        {/* Basic Info */}
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader>
            <CardTitle className="text-base text-white">Basic Information</CardTitle>
            <CardDescription className="text-neutral-400">
              Template name, description, and category
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-neutral-300">
                Name <span className="text-red-400">*</span>
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Data Sync Template"
                className="border-neutral-700 bg-neutral-950 text-neutral-100"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description" className="text-neutral-300">
                Description
              </Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What does this template do?"
                className="border-neutral-700 bg-neutral-950 text-neutral-100 min-h-[80px]"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category" className="text-neutral-300">
                Category
              </Label>
              <Input
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="e.g., data, automation, integration"
                className="border-neutral-700 bg-neutral-950 text-neutral-100"
              />
            </div>
          </CardContent>
        </Card>

        {/* Steps Builder */}
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base text-white">Steps</CardTitle>
              <CardDescription className="text-neutral-400">
                Define the execution steps for this template
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddStep}
              className="border-neutral-700 bg-transparent text-neutral-300 hover:bg-neutral-800"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Step
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {steps.map((step, index) => (
              <div
                key={index}
                className="flex items-start gap-3 rounded-xl border border-neutral-800 bg-neutral-950/50 p-3"
              >
                <div className="flex flex-col gap-1 pt-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-neutral-500 hover:text-neutral-300"
                    onClick={() => handleMoveStep(index, "up")}
                    disabled={index === 0}
                  >
                    <ArrowUp className="h-3 w-3" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-neutral-500 hover:text-neutral-300"
                    onClick={() => handleMoveStep(index, "down")}
                    disabled={index === steps.length - 1}
                  >
                    <ArrowDown className="h-3 w-3" />
                  </Button>
                </div>
                <div className="flex flex-1 gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-800 text-xs font-medium text-neutral-400">
                    {index + 1}
                  </div>
                  <div className="flex flex-1 flex-col gap-2">
                    <Input
                      value={step.action}
                      onChange={(e) =>
                        handleUpdateStep(index, "action", e.target.value)
                      }
                      placeholder="Action name (e.g., validate_source)"
                      className="border-neutral-700 bg-neutral-900 text-sm text-neutral-100"
                    />
                    <Textarea
                      value={
                        typeof step.config === "string"
                          ? step.config
                          : JSON.stringify(step.config, null, 2)
                      }
                      onChange={(e) => {
                        try {
                          const config = JSON.parse(e.target.value);
                          handleUpdateStep(index, "config", config);
                        } catch {
                          // Allow invalid JSON while typing
                          handleUpdateStep(index, "config", e.target.value);
                        }
                      }}
                      placeholder='{"key": "value"} - JSON configuration'
                      className="border-neutral-700 bg-neutral-900 text-xs text-neutral-100 font-mono min-h-[60px]"
                    />
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveStep(index)}
                  className="text-neutral-500 hover:text-red-400"
                  disabled={steps.length === 1}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Variables Builder */}
        <Card className="border-neutral-800 bg-neutral-900/70">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base text-white">Variables</CardTitle>
              <CardDescription className="text-neutral-400">
                Define configurable variables for this template
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddVariable}
              className="border-neutral-700 bg-transparent text-neutral-300 hover:bg-neutral-800"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Variable
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {variables.length === 0 ? (
              <p className="text-sm text-neutral-500">
                No variables defined. Templates work fine without variables too.
              </p>
            ) : (
              variables.map((variable, index) => (
                <div
                  key={index}
                  className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-3"
                >
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                    <Input
                      value={variable.name}
                      onChange={(e) =>
                        handleUpdateVariable(index, "name", e.target.value)
                      }
                      placeholder="Variable name"
                      className="border-neutral-700 bg-neutral-900 text-sm text-neutral-100"
                    />
                    <Select
                      value={variable.def.type}
                      onValueChange={(v) =>
                        handleUpdateVariable(index, "type", v)
                      }
                    >
                      <SelectTrigger className="border-neutral-700 bg-neutral-900 text-neutral-100">
                        <SelectValue placeholder="Type" />
                      </SelectTrigger>
                      <SelectContent className="border-neutral-700 bg-neutral-900">
                        <SelectItem value="string">String</SelectItem>
                        <SelectItem value="number">Number</SelectItem>
                        <SelectItem value="boolean">Boolean</SelectItem>
                        <SelectItem value="object">Object</SelectItem>
                        <SelectItem value="array">Array</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      value={variable.def.description || ""}
                      onChange={(e) =>
                        handleUpdateVariable(index, "description", e.target.value)
                      }
                      placeholder="Description"
                      className="border-neutral-700 bg-neutral-900 text-sm text-neutral-100"
                    />
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={variable.def.required}
                          onCheckedChange={(v) =>
                            handleUpdateVariable(index, "required", v)
                          }
                        />
                        <Label className="text-sm text-neutral-400">
                          Required
                        </Label>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveVariable(index)}
                        className="ml-auto text-neutral-500 hover:text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
