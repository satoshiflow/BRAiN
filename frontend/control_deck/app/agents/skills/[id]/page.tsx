"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import React, { useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useSkill, useExecuteSkill } from "@/hooks/useSkills";
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
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  Play,
  Edit,
  Globe,
  FileText,
  MessageSquare,
  Brain,
  Zap,
  Clock,
  CheckCircle,
  XCircle,
  Terminal,
} from "lucide-react";
import { SkillCategory } from "@/lib/skillsApi";

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

export default function SkillDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const skillId = params.id as string;
  const shouldExecute = searchParams.get("execute") === "true";

  const { data: skill, isLoading } = useSkill(skillId);
  const executeMutation = useExecuteSkill();

  const [paramValues, setParamValues] = useState<Record<string, unknown>>({});
  const [showExecuteDialog, setShowExecuteDialog] = useState(shouldExecute);
  const [executionResult, setExecutionResult] = useState<{
    success: boolean;
    output?: unknown;
    error?: string;
    execution_time_ms: number;
  } | null>(null);

  if (isLoading) {
    return <PageSkeleton variant="detail" />;
  }

  if (!skill) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <h3 className="text-lg font-semibold">Skill not found</h3>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push("/agents/skills")}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Skills
        </Button>
      </div>
    );
  }

  const CategoryIcon = categoryIcons[skill.category];

  const handleExecute = async () => {
    try {
      const result = await executeMutation.mutateAsync({
        id: skillId,
        parameters: paramValues,
      });
      setExecutionResult(result);
    } catch (error) {
      setExecutionResult({
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        execution_time_ms: 0,
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => router.push("/agents/skills")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{skill.name}</h1>
              <Badge
                variant="outline"
                className={categoryColors[skill.category]}
              >
                <CategoryIcon className="mr-1 h-3 w-3" />
                {skill.category}
              </Badge>
              {skill.enabled ? (
                <Badge
                  variant="outline"
                  className="border-green-500/20 text-green-400"
                >
                  Enabled
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className="border-gray-500/20 text-gray-400"
                >
                  Disabled
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              {skill.handler_path}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => router.push(`/agents/skills/${skillId}/edit`)}
          >
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button onClick={() => setShowExecuteDialog(true)}>
            <Play className="mr-2 h-4 w-4" />
            Execute
          </Button>
        </div>
      </div>

      {/* Content */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="manifest">Manifest</TabsTrigger>
          <TabsTrigger value="execution">Execution History</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Description</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                {skill.description || "No description provided"}
              </p>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Parameters</CardTitle>
                <CardDescription>
                  Input parameters for this skill
                </CardDescription>
              </CardHeader>
              <CardContent>
                {skill.manifest?.parameters &&
                skill.manifest.parameters.length > 0 ? (
                  <div className="space-y-3">
                    {skill.manifest.parameters.map((param) => (
                      <div
                        key={param.name}
                        className="flex items-center justify-between rounded-lg border border-border/50 p-3"
                      >
                        <div>
                          <div className="font-medium">{param.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {param.description || "No description"}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{param.type}</Badge>
                          {param.required && (
                            <Badge className="bg-primary/10 text-primary">
                              Required
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No parameters defined
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="border-border/50">
              <CardHeader>
                <CardTitle>Returns</CardTitle>
                <CardDescription>Output type and description</CardDescription>
              </CardHeader>
              <CardContent>
                {skill.manifest?.returns ? (
                  <div className="space-y-2">
                    <Badge variant="outline">
                      {skill.manifest.returns.type}
                    </Badge>
                    <p className="text-sm text-muted-foreground">
                      {skill.manifest.returns.description ||
                        "No description provided"}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No return type defined
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="manifest">
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Skill Manifest</CardTitle>
              <CardDescription>
                Full manifest definition (JSON)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="rounded-lg bg-secondary/50 p-4 overflow-auto text-xs">
                {JSON.stringify(skill.manifest, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="execution">
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Execution History</CardTitle>
              <CardDescription>
                Recent executions of this skill
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Execution history tracking coming soon...
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Execute Dialog */}
      <Dialog open={showExecuteDialog} onOpenChange={setShowExecuteDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Execute Skill: {skill.name}</DialogTitle>
            <DialogDescription>
              Provide parameters and run the skill
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="max-h-[400px]">
            <div className="space-y-4 pr-4">
              {skill.manifest?.parameters &&
              skill.manifest.parameters.length > 0 ? (
                skill.manifest.parameters.map((param) => (
                  <div key={param.name} className="space-y-2">
                    <Label htmlFor={param.name}>
                      {param.name}
                      {param.required && (
                        <span className="text-destructive">*</span>
                      )}
                    </Label>
                    <Input
                      id={param.name}
                      placeholder={param.description || `Enter ${param.name}`}
                      value={(paramValues[param.name] as string) || ""}
                      onChange={(e) =>
                        setParamValues((prev) => ({
                          ...prev,
                          [param.name]: e.target.value,
                        }))
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Type: {param.type}
                      {param.default !== undefined &&
                        ` (default: ${JSON.stringify(param.default)})`}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  No parameters required
                </p>
              )}

              {executionResult && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {executionResult.success ? (
                        <CheckCircle className="h-5 w-5 text-green-400" />
                      ) : (
                        <XCircle className="h-5 w-5 text-destructive" />
                      )}
                      <span
                        className={
                          executionResult.success
                            ? "text-green-400"
                            : "text-destructive"
                        }
                      >
                        {executionResult.success ? "Success" : "Failed"}
                      </span>
                      <span className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {executionResult.execution_time_ms}ms
                      </span>
                    </div>
                    {executionResult.error ? (
                      <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                        {executionResult.error}
                      </div>
                    ) : (
                      <pre className="rounded-lg bg-secondary/50 p-3 text-xs overflow-auto max-h-[200px]">
                        {JSON.stringify(executionResult.output, null, 2)}
                      </pre>
                    )}
                  </div>
                </>
              )}
            </div>
          </ScrollArea>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowExecuteDialog(false);
                setExecutionResult(null);
              }}
            >
              Close
            </Button>
            <Button
              onClick={handleExecute}
              disabled={executeMutation.isPending}
            >
              {executeMutation.isPending ? (
                <>
                  <Terminal className="mr-2 h-4 w-4 animate-pulse" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Execute
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
