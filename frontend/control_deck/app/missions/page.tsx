"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import React, { useMemo, useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMissions, useCreateMission, useUpdateMission } from "@/hooks/useMissions";
import { useMissionWebSocket } from "@/hooks/useMissionWebSocket";
import { useTemplates, useInstantiateTemplate } from "@/hooks/useMissionTemplates";
import type { Mission, MissionStatus } from "@/lib/missionsApi";
import type { MissionTemplate } from "@/lib/missionTemplatesApi";
import { PageSkeleton } from "@/components/skeletons/PageSkeleton";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Plus, FileText, Rocket, LayoutGrid } from "lucide-react";

type FormState = {
  name: string;
  description: string;
};

const STATUS_ORDER: MissionStatus[] = [
  "RUNNING",
  "PENDING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
];

// Wrapper component to handle suspense for useSearchParams
export default function MissionsPageWrapper() {
  return (
    <Suspense fallback={<PageSkeleton variant="dashboard" />}>
      <MissionsOverviewPage />
    </Suspense>
  );
}

function MissionsOverviewPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const templateIdFromUrl = searchParams?.get("template") || null;

  const [formState, setFormState] = useState<FormState>({
    name: "",
    description: "",
  });

  // Template dialog state
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [templateVariables, setTemplateVariables] = useState<Record<string, unknown>>({});
  const [missionName, setMissionName] = useState("");

  // Data fetching
  const { data: rawMissions, isLoading, error } = useMissions();
  const { data: templatesData } = useTemplates();
  const createMissionMutation = useCreateMission();
  const instantiateTemplateMutation = useInstantiateTemplate();
  const updateMissionMutation = useUpdateMission();

  // WebSocket for real-time mission updates
  const { isConnected: wsConnected } = useMissionWebSocket();

  const templates = templatesData?.items || [];
  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  // Open dialog if template ID is in URL
  useEffect(() => {
    if (templateIdFromUrl) {
      setShowTemplateDialog(true);
      setSelectedTemplateId(templateIdFromUrl);
    }
  }, [templateIdFromUrl]);

  // Sort missions by status priority, then by created_at
  const sortedMissions = useMemo(() => {
    if (!rawMissions) return [];
    const missions = [...rawMissions];
    missions.sort((a, b) => {
      const ai = STATUS_ORDER.indexOf(a.status);
      const bi = STATUS_ORDER.indexOf(b.status);
      const ascore = ai === -1 ? STATUS_ORDER.length : ai;
      const bscore = bi === -1 ? STATUS_ORDER.length : bi;
      if (ascore !== bscore) return ascore - bscore;
      const at = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bt = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bt - at;
    });
    return missions;
  }, [rawMissions]);

  function handleCreateMission(e: React.FormEvent) {
    e.preventDefault();
    if (!formState.name.trim()) return;

    createMissionMutation.mutate(
      {
        name: formState.name.trim(),
        description: formState.description.trim() || undefined,
      },
      {
        onSuccess: () => {
          setFormState({ name: "", description: "" });
        },
      }
    );
  }

  function handleStatusChange(id: string, status: MissionStatus) {
    updateMissionMutation.mutate({
      id,
      payload: { status },
    });
  }

  function handleTemplateSelect(templateId: string) {
    setSelectedTemplateId(templateId);
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setMissionName(template.name);
      // Initialize variables with defaults
      const defaults: Record<string, unknown> = {};
      Object.entries(template.variables || {}).forEach(([key, def]) => {
        if (def.default !== undefined) {
          defaults[key] = def.default;
        }
      });
      setTemplateVariables(defaults);
    }
  }

  async function handleCreateFromTemplate(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedTemplateId) return;

    await instantiateTemplateMutation.mutateAsync({
      id: selectedTemplateId,
      payload: {
        variables: templateVariables,
        mission_name: missionName || undefined,
      },
    });

    setShowTemplateDialog(false);
    setSelectedTemplateId("");
    setTemplateVariables({});
    setMissionName("");
  }

  function handleVariableChange(key: string, value: unknown) {
    setTemplateVariables((prev) => ({ ...prev, [key]: value }));
  }

  const stats = useMemo(() => {
    const list = sortedMissions ?? [];
    const byStatus: Record<string, number> = {};
    for (const m of list) {
      const key = m.status ?? "UNKNOWN";
      byStatus[key] = (byStatus[key] ?? 0) + 1;
    }
    return {
      total: list.length,
      running: byStatus.RUNNING ?? 0,
      pending: byStatus.PENDING ?? 0,
      completed: byStatus.COMPLETED ?? 0,
      failed: byStatus.FAILED ?? 0,
      cancelled: byStatus.CANCELLED ?? 0,
    };
  }, [sortedMissions]);

  if (isLoading) {
    return <PageSkeleton variant="list" />;
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">Missions Overview</h1>
            <p className="text-sm text-neutral-400">
              Überblick über alle aktiven und historischen BRAiN-Missionen.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setShowTemplateDialog(true)}
              className="border-emerald-700 bg-transparent text-emerald-400 hover:bg-emerald-950/50"
            >
              <FileText className="mr-2 h-4 w-4" />
              From Template
            </Button>
            <Button
              onClick={() => router.push("/missions/templates")}
              variant="outline"
              className="border-neutral-700 bg-transparent text-neutral-300 hover:bg-neutral-800"
            >
              <LayoutGrid className="mr-2 h-4 w-4" />
              Templates
            </Button>
          </div>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <DashboardCard label="Total" value={stats.total} />
        <DashboardCard label="Running" value={stats.running} tone="info" />
        <DashboardCard label="Pending" value={stats.pending} />
        <DashboardCard label="Completed" value={stats.completed} tone="success" />
        <DashboardCard label="Failed" value={stats.failed} tone="danger" />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
          <h2 className="text-sm font-semibold text-white">
            Neue Mission anlegen
          </h2>
          <p className="mt-1 text-xs text-neutral-400">
            Name und optional eine kurze Beschreibung eingeben, um eine neue Mission
            zu starten.
          </p>

          <form onSubmit={handleCreateMission} className="mt-4 flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-neutral-300">Name</label>
              <input
                className="h-9 rounded-xl border border-neutral-700 bg-neutral-900 px-3 text-sm text-neutral-100 outline-none focus:border-emerald-500"
                value={formState.name}
                onChange={(e) =>
                  setFormState((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="z.B. Demo Mission"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-neutral-300">Beschreibung</label>
              <textarea
                className="min-h-[80px] rounded-xl border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-emerald-500"
                value={formState.description}
                onChange={(e) =>
                  setFormState((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
                placeholder="optional"
              />
            </div>

            {createMissionMutation.error && (
              <div className="text-xs text-red-400">
                {createMissionMutation.error.message}
              </div>
            )}

            <button
              type="submit"
              disabled={createMissionMutation.isPending || !formState.name.trim()}
              className="mt-1 inline-flex h-9 items-center justify-center rounded-full bg-emerald-600 px-4 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createMissionMutation.isPending ? "Wird angelegt…" : "Mission anlegen"}
            </button>
          </form>
        </div>

        <div className="lg:col-span-2 rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Live Missions</h2>
            {isLoading && (
              <span className="text-xs text-neutral-500">Lade…</span>
            )}
          </div>

          {error && (
            <div className="text-xs text-red-400">
              Missionen konnten nicht geladen werden:
              <br />
              {error.message}
            </div>
          )}

          {!isLoading && sortedMissions.length === 0 && (
            <div className="text-xs text-neutral-500">
              Noch keine Missionen angelegt.
            </div>
          )}

          <div className="flex flex-col gap-2">
            {sortedMissions.map((mission) => (
              <MissionRow
                key={mission.id}
                mission={mission}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Create from Template Dialog */}
      <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
        <DialogContent className="border-neutral-800 bg-neutral-900 max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <FileText className="h-5 w-5 text-emerald-400" />
              Create Mission from Template
            </DialogTitle>
            <DialogDescription className="text-neutral-400">
              Select a template and configure variables to create a new mission.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateFromTemplate} className="space-y-4">
            {/* Template Selection */}
            <div className="space-y-2">
              <Label className="text-neutral-300">Template</Label>
              <Select
                value={selectedTemplateId}
                onValueChange={handleTemplateSelect}
              >
                <SelectTrigger className="border-neutral-700 bg-neutral-950 text-neutral-100">
                  <SelectValue placeholder="Select a template" />
                </SelectTrigger>
                <SelectContent className="border-neutral-700 bg-neutral-900">
                  {templates.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      <span className="text-neutral-100">{template.name}</span>
                      <span className="ml-2 text-neutral-500">({template.category})</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Mission Name Override */}
            {selectedTemplate && (
              <div className="space-y-2">
                <Label className="text-neutral-300">Mission Name</Label>
                <Input
                  value={missionName}
                  onChange={(e) => setMissionName(e.target.value)}
                  placeholder={selectedTemplate.name}
                  className="border-neutral-700 bg-neutral-950 text-neutral-100"
                />
              </div>
            )}

            {/* Variables Section */}
            {selectedTemplate && Object.keys(selectedTemplate.variables || {}).length > 0 && (
              <div className="space-y-3">
                <Label className="text-neutral-300">Variables</Label>
                <div className="space-y-3">
                  {Object.entries(selectedTemplate.variables || {}).map(([key, def]) => (
                    <div key={key} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm text-neutral-400">
                          {key}
                          {def.required && <span className="ml-1 text-red-400">*</span>}
                        </Label>
                        <span className="text-xs text-neutral-500">{def.type}</span>
                      </div>
                      {def.description && (
                        <p className="text-xs text-neutral-500">{def.description}</p>
                      )}
                      <VariableInput
                        type={def.type}
                        value={templateVariables[key]}
                        placeholder={def.default !== undefined ? String(def.default) : ""}
                        onChange={(value) => handleVariableChange(key, value)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Template Info */}
            {selectedTemplate && (
              <div className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-3">
                <p className="text-xs text-neutral-400">
                  <span className="text-neutral-500">Steps:</span>{" "}
                  {selectedTemplate.steps?.length || 0} steps will be executed
                </p>
                {selectedTemplate.description && (
                  <p className="mt-1 text-xs text-neutral-500">
                    {selectedTemplate.description}
                  </p>
                )}
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowTemplateDialog(false)}
                className="border-neutral-700 bg-transparent text-neutral-300 hover:bg-neutral-800"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!selectedTemplateId || instantiateTemplateMutation.isPending}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                <Rocket className="mr-2 h-4 w-4" />
                {instantiateTemplateMutation.isPending
                  ? "Creating..."
                  : "Create Mission"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function VariableInput({
  type,
  value,
  placeholder,
  onChange,
}: {
  type: string;
  value: unknown;
  placeholder?: string;
  onChange: (value: unknown) => void;
}) {
  if (type === "boolean") {
    return (
      <Select
        value={value === undefined ? "" : String(value)}
        onValueChange={(v) => onChange(v === "true")}
      >
        <SelectTrigger className="border-neutral-700 bg-neutral-950 text-neutral-100">
          <SelectValue placeholder="Select..." />
        </SelectTrigger>
        <SelectContent className="border-neutral-700 bg-neutral-900">
          <SelectItem value="true">True</SelectItem>
          <SelectItem value="false">False</SelectItem>
        </SelectContent>
      </Select>
    );
  }

  if (type === "number") {
    return (
      <Input
        type="number"
        value={value === undefined ? "" : String(value)}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
        className="border-neutral-700 bg-neutral-950 text-neutral-100"
      />
    );
  }

  if (type === "object" || type === "array") {
    return (
      <Textarea
        value={value === undefined ? "" : JSON.stringify(value, null, 2)}
        placeholder={placeholder || '{"key": "value"}'}
        onChange={(e) => {
          try {
            onChange(JSON.parse(e.target.value));
          } catch {
            onChange(e.target.value);
          }
        }}
        className="border-neutral-700 bg-neutral-950 text-neutral-100 font-mono text-xs min-h-[80px]"
      />
    );
  }

  return (
    <Input
      type="text"
      value={value === undefined ? "" : String(value)}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="border-neutral-700 bg-neutral-950 text-neutral-100"
    />
  );
}

function DashboardCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "success" | "danger" | "info";
}) {
  const color =
    tone === "success"
      ? "text-emerald-400"
      : tone === "danger"
        ? "text-red-400"
        : tone === "info"
          ? "text-sky-400"
          : "text-neutral-100";

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 px-4 py-3">
      <div className="text-xs text-neutral-400">{label}</div>
      <div className={`mt-1 text-xl font-semibold ${color}`}>{value}</div>
    </div>
  );
}

function MissionRow({
  mission,
  onStatusChange,
}: {
  mission: Mission;
  onStatusChange: (id: string, status: MissionStatus) => void;
}) {
  const created =
    mission.created_at && !Number.isNaN(Date.parse(mission.created_at))
      ? new Date(mission.created_at)
      : undefined;

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-950/80 px-4 py-3 text-sm">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col">
          <span className="font-medium text-neutral-100">{mission.name}</span>
          {mission.description && (
            <span className="text-xs text-neutral-400">
              {mission.description}
            </span>
          )}
          {created && (
            <span className="mt-1 text-[11px] text-neutral-500">
              Angelegt am {created.toLocaleDateString()}{" "}
              {created.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <StatusBadge status={mission.status} />
          <select
            className="h-7 rounded-full border border-neutral-700 bg-neutral-900 px-2 text-[11px] text-neutral-100 outline-none"
            value={mission.status}
            onChange={(e) =>
              onStatusChange(mission.id, e.target.value as MissionStatus)
            }
          >
            {STATUS_ORDER.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: MissionStatus }) {
  let cls = "bg-neutral-800 text-neutral-200";
  if (status === "RUNNING") cls = "bg-sky-900/60 text-sky-300";
  else if (status === "PENDING") cls = "bg-amber-900/60 text-amber-300";
  else if (status === "COMPLETED") cls = "bg-emerald-900/60 text-emerald-300";
  else if (status === "FAILED") cls = "bg-red-900/60 text-red-300";
  else if (status === "CANCELLED") cls = "bg-neutral-900/80 text-neutral-400";

  return (
    <span
      className={`inline-flex min-w-[88px] justify-center rounded-full px-3 py-1 text-[11px] font-medium ${cls}`}
    >
      {status}
    </span>
  );
}
