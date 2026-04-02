"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { HelpHint } from "@/components/help/help-hint";
import { DecisionDialog } from "@/components/operator/decision-dialog";
import { ApiError } from "@/lib/api/client";
import { externalAppsApi, type PaperclipActionRequestItem } from "@/lib/api/external-apps";
import { getControlDeckHelpTopic } from "@/lib/help/topics";
import {
  runtimeControlApi,
  type ResolverResponse,
  type RuntimeControlTimelineEvent,
  type RuntimeDecisionContext,
} from "@/lib/api/runtime-control";
import { supervisorApi, type DomainEscalationItem } from "@/lib/api/supervisor";
import { taskApi, type TaskRecord, type TaskStatus } from "@/lib/api/tasks";
import { cn, formatRelativeTime } from "@/lib/utils";

type ExecutorType = "openclaw" | "paperclip";

const executorContexts: Record<ExecutorType, RuntimeDecisionContext> = {
  openclaw: {
    environment: "local",
    mission_type: "connector.openclaw",
    skill_type: "openclaw.worker_bridge",
    agent_role: "operator",
    risk_score: 0.3,
    budget_state: {},
    system_health: {},
    feature_context: {},
  },
  paperclip: {
    environment: "local",
    mission_type: "connector.paperclip",
    skill_type: "paperclip.handoff",
    agent_role: "operator",
    risk_score: 0.2,
    budget_state: {},
    system_health: {},
    feature_context: {},
  },
};

const taskStatusTone: Record<TaskStatus, string> = {
  pending: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
  scheduled: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
  claimed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  running: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  cancelled: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  timeout: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  retrying: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
};

function timelineTone(eventType: string): string {
  if (eventType.endsWith("exchange_failed.v1")) {
    return "border-red-200 bg-red-50/70 dark:border-red-900/40 dark:bg-red-950/20";
  }
  if (eventType.endsWith("opened.v1") || eventType.endsWith("approved.v1")) {
    return "border-green-200 bg-green-50/70 dark:border-green-900/40 dark:bg-green-950/20";
  }
  if (eventType.endsWith("created.v1")) {
    return "border-blue-200 bg-blue-50/70 dark:border-blue-900/40 dark:bg-blue-950/20";
  }
  return "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800";
}

function timelineContext(item: RuntimeControlTimelineEvent): string {
  const payload = item.payload ?? {};
  const targetType = typeof payload.target_type === "string" ? payload.target_type : null;
  const targetRef = typeof payload.target_ref === "string" ? payload.target_ref : null;
  const skillRunId = typeof payload.skill_run_id === "string" ? payload.skill_run_id : null;
  const decisionId = typeof payload.decision_id === "string" ? payload.decision_id : null;
  const reason = typeof payload.reason === "string" ? payload.reason : null;
  const executionResult = typeof payload.execution_result === "object" && payload.execution_result ? payload.execution_result as Record<string, unknown> : null;
  const newTaskId = typeof executionResult?.new_task_id === "string" ? executionResult.new_task_id : null;
  const escalationId = typeof executionResult?.supervisor_escalation_id === "string" ? executionResult.supervisor_escalation_id : null;

  const parts = [
    targetType && targetRef ? `${targetType}:${targetRef}` : null,
    skillRunId ? `skillRun:${skillRunId}` : null,
    decisionId ? `decision:${decisionId}` : null,
    newTaskId ? `newTask:${newTaskId}` : null,
    escalationId ? `supervisor:${escalationId}` : null,
    reason ? `reason:${reason}` : null,
  ].filter(Boolean);

  return parts.length > 0 ? parts.join(" | ") : `${item.entity_type}:${item.entity_id}`;
}

function ExecutorStateCard({
  executor,
  decision,
  taskSummary,
}: {
  executor: ExecutorType;
  decision: ResolverResponse | null;
  taskSummary: { total: number; byStatus: Record<string, number> };
}) {
  const effectiveConfig = (decision?.effective_config ?? {}) as Record<string, unknown>;
  const workers = (typeof effectiveConfig.workers === "object" && effectiveConfig.workers
    ? effectiveConfig.workers
    : {}) as Record<string, unknown>;
  const external = (typeof workers.external === "object" && workers.external
    ? workers.external
    : {}) as Record<string, unknown>;
  const connectorConfig = (typeof external[executor] === "object" && external[executor]
    ? external[executor]
    : {}) as Record<string, unknown>;
  const enabled = connectorConfig.enabled !== false;
  const security = (typeof effectiveConfig.security === "object" && effectiveConfig.security
    ? effectiveConfig.security
    : {}) as Record<string, unknown>;
  const allowedConnectors = Array.isArray(security.allowed_connectors) ? security.allowed_connectors.map(String) : [];
  const connectorAllowed = allowedConnectors.length === 0 || allowedConnectors.includes(executor);
  const label = executor === "paperclip" ? "Paperclip" : "OpenClaw";

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-medium text-slate-900 dark:text-slate-100">{label}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Bounded external executor under BRAiN governance</p>
        </div>
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
            enabled && connectorAllowed
              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
              : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
          )}
        >
          {enabled && connectorAllowed ? "Enabled" : "Blocked"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 p-3">
          <p className="text-slate-500 dark:text-slate-400">Executor policy</p>
          <p className="font-medium text-slate-900 dark:text-slate-100">{enabled ? "allowed" : "disabled"}</p>
        </div>
        <div className="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 p-3">
          <p className="text-slate-500 dark:text-slate-400">Connector policy</p>
          <p className="font-medium text-slate-900 dark:text-slate-100">{connectorAllowed ? "allowed" : "blocked"}</p>
        </div>
        <div className="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 p-3">
          <p className="text-slate-500 dark:text-slate-400">Selected route</p>
          <p className="font-medium text-slate-900 dark:text-slate-100">{decision?.selected_route ?? "-"}</p>
        </div>
        <div className="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 p-3">
          <p className="text-slate-500 dark:text-slate-400">Recent tasks</p>
          <p className="font-medium text-slate-900 dark:text-slate-100">{taskSummary.total}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.entries(taskSummary.byStatus).map(([status, count]) => (
          <span
            key={`${executor}-${status}`}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700 dark:bg-slate-700 dark:text-slate-200"
          >
            <span>{status}</span>
            <strong>{count}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

function TaskTable({
  executor,
  tasks,
  isLaunching,
  onOpenInPaperclip,
}: {
  executor: ExecutorType;
  tasks: TaskRecord[];
  isLaunching: string | null;
  onOpenInPaperclip: (task: TaskRecord) => Promise<void>;
}) {
  const label = executor === "paperclip" ? "Paperclip" : "OpenClaw";

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="font-medium text-slate-900 dark:text-slate-100">{label} TaskLeases</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Recent external execution tasks tracked through SkillRun / TaskLease</p>
        </div>
      </div>

      {tasks.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Keine Tasks gefunden.</p>
      ) : (
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                <th className="py-2 pr-4 font-medium">Task</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">SkillRun</th>
                <th className="py-2 pr-4 font-medium">Updated</th>
                <th className="py-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const actionDisabled = executor !== "paperclip" || !task.skill_run_id;
                return (
                  <tr key={task.task_id} className="border-b border-slate-100 dark:border-slate-800 align-top">
                    <td className="py-3 pr-4">
                      <p className="font-medium text-slate-900 dark:text-slate-100">{task.task_id}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{task.name}</p>
                      {task.error_message ? (
                        <p className="mt-1 text-xs text-red-600 dark:text-red-300">{task.error_message}</p>
                      ) : null}
                    </td>
                    <td className="py-3 pr-4">
                      <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-medium", taskStatusTone[task.status])}>
                        {task.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-slate-600 dark:text-slate-300">{task.skill_run_id ?? "-"}</td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{formatRelativeTime(task.updated_at)}</td>
                    <td className="py-3">
                      {executor === "paperclip" ? (
                        <button
                          type="button"
                          disabled={actionDisabled || isLaunching === task.task_id}
                          onClick={() => onOpenInPaperclip(task)}
                          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isLaunching === task.task_id ? "Opening..." : "Open in Paperclip"}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-500 dark:text-slate-400">Managed via AXE/CD3</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ActionRequestInbox({
  items,
  actingRequestId,
  onApprove,
  onReject,
}: {
  items: PaperclipActionRequestItem[];
  actingRequestId: string | null;
  onApprove: (item: PaperclipActionRequestItem) => Promise<void>;
  onReject: (item: PaperclipActionRequestItem) => Promise<void>;
}) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
      <div>
        <h3 className="font-medium text-slate-900 dark:text-slate-100">Action Request Inbox</h3>
        <p className="text-xs text-slate-500 dark:text-slate-400">Governed requests coming back from the Paperclip MissionCenter.</p>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Keine offenen Requests.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.request_id} className="rounded-md border border-slate-200 dark:border-slate-700 p-3 space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-900 dark:text-slate-100">{item.action}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{item.request_id} · {item.target_ref}</p>
                </div>
                <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                  {item.status}
                </span>
              </div>
              <p className="text-sm text-slate-700 dark:text-slate-300">{item.reason}</p>
              <div className="text-xs text-slate-500 dark:text-slate-400 space-y-1">
                <p>principal: {item.principal_id}</p>
                <p>skillRun: {item.skill_run_id ?? "-"}</p>
                <p>updated: {formatRelativeTime(item.updated_at)}</p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={actingRequestId === item.request_id}
                  onClick={() => onApprove(item)}
                  className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {actingRequestId === item.request_id ? "Working..." : "Approve"}
                </button>
                <button
                  type="button"
                  disabled={actingRequestId === item.request_id}
                  onClick={() => onReject(item)}
                  className="rounded-md bg-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SupervisorEscalationPanel({ items }: { items: DomainEscalationItem[] }) {
  const noteValue = (item: DomainEscalationItem, key: string): string | null => {
    const value = item.notes?.[key];
    return typeof value === "string" && value.length > 0 ? value : null;
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Supervisor Inbox</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Escalations already materialized into the supervisor workflow.</p>
        </div>
        <Link
          href="/supervisor?scope=paperclip"
          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          Open inbox
        </Link>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Noch keine Supervisor-Eskalationen aus Paperclip.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.escalation_id} className="rounded-md border border-slate-200 dark:border-slate-700 p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-900 dark:text-slate-100">{item.escalation_id}</p>
                  <p className="text-xs font-mono text-slate-500 dark:text-slate-400">{item.domain_key}</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    {noteValue(item, "action_request_id") ? (
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                        action request: {noteValue(item, "action_request_id")}
                      </span>
                    ) : null}
                    {noteValue(item, "target_ref") ? (
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                        target: {noteValue(item, "target_ref")}
                      </span>
                    ) : null}
                  </div>
                </div>
                <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 dark:bg-slate-700 dark:text-slate-200">
                  {item.status}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
                <span>{formatRelativeTime(item.received_at)}</span>
                <Link href={`/supervisor/${encodeURIComponent(item.escalation_id)}`} className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300">
                  Open detail
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ExternalOperationsPage() {
  const externalOpsTopic = getControlDeckHelpTopic("external-operations.paperclip-governance");
  const supervisorHandoffsTopic = getControlDeckHelpTopic("external-operations.supervisor-handoffs");
  const [paperclipDecision, setPaperclipDecision] = useState<ResolverResponse | null>(null);
  const [openclawDecision, setOpenclawDecision] = useState<ResolverResponse | null>(null);
  const [paperclipTasks, setPaperclipTasks] = useState<TaskRecord[]>([]);
  const [openclawTasks, setOpenclawTasks] = useState<TaskRecord[]>([]);
  const [timeline, setTimeline] = useState<RuntimeControlTimelineEvent[]>([]);
  const [actionRequests, setActionRequests] = useState<PaperclipActionRequestItem[]>([]);
  const [supervisorEscalations, setSupervisorEscalations] = useState<DomainEscalationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [launchingTaskId, setLaunchingTaskId] = useState<string | null>(null);
  const [actingRequestId, setActingRequestId] = useState<string | null>(null);
  const [pendingDecision, setPendingDecision] = useState<{
    mode: "approve" | "reject";
    item: PaperclipActionRequestItem;
  } | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [paperclipResolve, openclawResolve, paperclipTaskPayload, openclawTaskPayload, timelinePayload, actionRequestPayload, supervisorPayload] = await Promise.all([
        runtimeControlApi.resolve(executorContexts.paperclip),
        runtimeControlApi.resolve(executorContexts.openclaw),
        taskApi.list("paperclip_work", 20),
        taskApi.list("openclaw_work", 20),
        runtimeControlApi.listTimeline(120),
        externalAppsApi.listPaperclipActionRequests(),
        supervisorApi.listDomainEscalations(20),
      ]);

      setPaperclipDecision(paperclipResolve);
      setOpenclawDecision(openclawResolve);
      setPaperclipTasks(paperclipTaskPayload.items);
      setOpenclawTasks(openclawTaskPayload.items);
      setActionRequests(actionRequestPayload.items.filter((item) => item.status === "pending"));
      setSupervisorEscalations(
        supervisorPayload.items.filter((item) => item.domain_key.startsWith("external_apps.paperclip"))
      );
      setTimeline(
        timelinePayload.items.filter((item) =>
          item.event_type.startsWith("external.handoff.paperclip") ||
          item.event_type.startsWith("external.action_request.paperclip") ||
          item.event_type.includes("runtime.override.request")
        )
      );
      setError(null);
    } catch (err) {
      console.error("Failed to load external operations", err);
      setError("Konnte External-Operations-Daten nicht laden.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const paperclipSummary = useMemo(
    () => ({ total: paperclipTasks.length, byStatus: paperclipTasks.reduce<Record<string, number>>((acc, item) => {
      acc[item.status] = (acc[item.status] ?? 0) + 1;
      return acc;
    }, {}) }),
    [paperclipTasks]
  );
  const openclawSummary = useMemo(
    () => ({ total: openclawTasks.length, byStatus: openclawTasks.reduce<Record<string, number>>((acc, item) => {
      acc[item.status] = (acc[item.status] ?? 0) + 1;
      return acc;
    }, {}) }),
    [openclawTasks]
  );

  const handleOpenInPaperclip = useCallback(async (task: TaskRecord) => {
    if (!task.skill_run_id) {
      setError("Kein SkillRun fuer diesen Task vorhanden.");
      return;
    }
    setLaunchingTaskId(task.task_id);
    try {
      const response = await externalAppsApi.createPaperclipHandoff({
        target_type: "execution",
        target_ref: task.task_id,
        skill_run_id: task.skill_run_id,
        mission_id: task.mission_id ?? undefined,
        correlation_id: task.correlation_id ?? undefined,
        permissions: ["view", "request_approval", "request_retry", "request_escalation"],
      });
      window.open(response.handoff_url, "_blank", "noopener,noreferrer");
      setError(null);
      await loadData();
    } catch (err) {
      console.error("Failed to create Paperclip handoff", err);
      if (err instanceof ApiError) {
        setError(`Paperclip handoff fehlgeschlagen (${err.status}).`);
      } else {
        setError("Paperclip handoff fehlgeschlagen.");
      }
    } finally {
      setLaunchingTaskId(null);
    }
  }, [loadData]);

  const handleApproveRequest = useCallback(async (item: PaperclipActionRequestItem, reason: string) => {
    setActingRequestId(item.request_id);
    try {
      await externalAppsApi.approvePaperclipActionRequest(item.request_id, reason);
      setError(null);
      setPendingDecision(null);
      await loadData();
    } catch (err) {
      console.error("Failed to approve action request", err);
      if (err instanceof ApiError) {
        setError(`Action request approval failed (${err.status}).`);
      } else {
        setError("Action request approval failed.");
      }
    } finally {
      setActingRequestId(null);
    }
  }, [loadData]);

  const handleRejectRequest = useCallback(async (item: PaperclipActionRequestItem, reason: string) => {
    setActingRequestId(item.request_id);
    try {
      await externalAppsApi.rejectPaperclipActionRequest(item.request_id, reason);
      setError(null);
      setPendingDecision(null);
      await loadData();
    } catch (err) {
      console.error("Failed to reject action request", err);
      if (err instanceof ApiError) {
        setError(`Action request rejection failed (${err.status}).`);
      } else {
        setError("Action request rejection failed.");
      }
    } finally {
      setActingRequestId(null);
    }
  }, [loadData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100">External Operations</h2>
            <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
              Read-only visibility for bounded external executors. Governance remains in BRAiN / Runtime Control.
            </p>
          </div>
          <div className="flex gap-2">
            {externalOpsTopic ? <HelpHint topic={externalOpsTopic} /> : null}
            {supervisorHandoffsTopic ? <HelpHint topic={supervisorHandoffsTopic} /> : null}
          </div>
        </div>
      </div>

      {error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <ExecutorStateCard executor="openclaw" decision={openclawDecision} taskSummary={openclawSummary} />
        <ExecutorStateCard executor="paperclip" decision={paperclipDecision} taskSummary={paperclipSummary} />
      </div>

      <div className="grid grid-cols-1 gap-6">
        <ActionRequestInbox
          items={actionRequests}
          actingRequestId={actingRequestId}
          onApprove={async (item) => setPendingDecision({ mode: "approve", item })}
          onReject={async (item) => setPendingDecision({ mode: "reject", item })}
        />
        <SupervisorEscalationPanel items={supervisorEscalations} />
        <TaskTable executor="paperclip" tasks={paperclipTasks} isLaunching={launchingTaskId} onOpenInPaperclip={handleOpenInPaperclip} />
        <TaskTable executor="openclaw" tasks={openclawTasks} isLaunching={launchingTaskId} onOpenInPaperclip={handleOpenInPaperclip} />
      </div>

      <DecisionDialog
        open={pendingDecision !== null}
        title={pendingDecision?.mode === "approve" ? "Approve action request" : "Reject action request"}
        description={pendingDecision ? `${pendingDecision.item.action} for ${pendingDecision.item.target_ref}` : ""}
        confirmLabel={pendingDecision?.mode === "approve" ? "Approve request" : "Reject request"}
        initialReason={pendingDecision ? `${pendingDecision.mode === "approve" ? "Approved" : "Rejected"} via ControlDeck for ${pendingDecision.item.action}` : ""}
        busy={pendingDecision !== null && actingRequestId === pendingDecision.item.request_id}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDecision(null);
          }
        }}
        onConfirm={async (reason) => {
          if (!pendingDecision) {
            return;
          }
          if (pendingDecision.mode === "approve") {
            await handleApproveRequest(pendingDecision.item, reason);
            return;
          }
          await handleRejectRequest(pendingDecision.item, reason);
        }}
      />

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-slate-900 dark:text-slate-100">Governance Timeline</h3>
          <button
            type="button"
            onClick={loadData}
            className="rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
          >
            Refresh
          </button>
        </div>
        {timeline.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">Noch keine relevanten Handoff- oder Override-Events.</p>
        ) : (
          <div className="space-y-2 max-h-[360px] overflow-auto">
            {timeline.map((item) => (
              <div
                key={item.event_id}
                className={cn("rounded-md border p-3", timelineTone(item.event_type))}
              >
                <p className="text-xs font-mono text-slate-500 dark:text-slate-400">{item.created_at}</p>
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{item.event_type}</p>
                <p className="text-xs text-slate-600 dark:text-slate-300">{timelineContext(item)}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">actor: {item.actor_id ?? "system"}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
