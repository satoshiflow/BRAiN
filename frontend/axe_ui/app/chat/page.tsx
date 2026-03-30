"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Camera, Loader2, Paperclip, Send, X } from "lucide-react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { AdvancedCameraCapture } from "@/components/chat/AdvancedCameraCapture";
import { WorkerRunCard } from "@/components/chat/WorkerRunCard";
import { HelpHint } from "@/components/help/HelpHint";
import {
  appendAxeSessionMessage,
  getAxeWorkerRun,
  listPurposeEvaluations,
  listRoutingDecisions,
  postAxeChat,
  uploadAxeAttachment,
} from "@/lib/api";
import { getControlDeckBase, getDefaultModel } from "@/lib/config";
import type {
  AxeChatRequest,
  AxeSessionMessage,
  AxeSessionMessageRole,
  AxeWorkerUpdate,
  PurposeEvaluationRecord,
  RoutingDecisionRecord,
} from "@/lib/contracts";
import { useAuthSession } from "@/hooks/useAuthSession";
import { useChatSessions } from "@/hooks/useChatSessions";
import { pluginRegistry, initializePlugins, destroyPlugins, type PluginContext } from "../../src/plugins";
import slashCommandsPlugin from "../../src/plugins/slashCommands";
import { getAxeHelpTopic } from "@/lib/help/topics";

interface Message {
  id: number;
  sessionMessageId?: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface WorkerRunAnchor {
  workerRunId: string;
  sessionId: string;
  messageId?: string;
  localMessageId: number;
}

interface PendingAttachment {
  localId: string;
  name: string;
  attachmentId?: string;
  status: "uploading" | "ready" | "error";
  error?: string;
}

const DEFAULT_MODEL = getDefaultModel();

function formatTime(date: Date): string {
  if (typeof window === "undefined") return "";
  return date.toLocaleTimeString();
}

function isMobileDevice() {
  if (typeof window === "undefined") return false;
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
}

function fallbackSessionId(): string {
  return `axe_session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

function ComposerActions({ context }: { context: PluginContext }) {
  const renderers = pluginRegistry.renderUiSlot("composer.actions");
  if (renderers.length === 0) return null;
  return (
    <div className="mb-2 flex gap-2">
      {renderers.map((Renderer, idx) => (
        <Renderer key={idx} context={context} />
      ))}
    </div>
  );
}

function ChatPageContent() {
  const { accessToken, withAuthRetry } = useAuthSession();
  const authHeaders = useMemo(
    () => (accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined),
    [accessToken]
  );

  const {
    groupedSessions,
    activeSessionId,
    activeSession,
    loading: sessionsLoading,
    error: sessionsError,
    loadSessions,
    createSession,
    selectSession,
    renameSession,
    removeSession,
  } = useChatSessions({ headers: authHeaders, withAuthRetry });

  const [messages, setMessages] = useState<Message[]>([]);
  const [isClient, setIsClient] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pluginFallbackSessionId] = useState(() => fallbackSessionId());
  const [pluginContext, setPluginContext] = useState<PluginContext | null>(null);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [uploadLock, setUploadLock] = useState(false);
  const [workerUpdates, setWorkerUpdates] = useState<Record<string, AxeWorkerUpdate>>({});
  const [workerAnchors, setWorkerAnchors] = useState<Record<string, WorkerRunAnchor>>({});
  const [purposeTrace, setPurposeTrace] = useState<PurposeEvaluationRecord[]>([]);
  const [routingTrace, setRoutingTrace] = useState<RoutingDecisionRecord[]>([]);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceError, setTraceError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraFallbackInputRef = useRef<HTMLInputElement>(null);

  const hasUploadingAttachments = attachments.some((item) => item.status === "uploading");
  const hasFailedAttachments = attachments.some((item) => item.status === "error");

  const pluginSessionId = activeSessionId ?? pluginFallbackSessionId;
  const controlDeckProviderUrl = useMemo(() => `${getControlDeckBase()}/settings/llm-providers`, []);
  const activePollingAnchors = useMemo(
    () =>
      Object.values(workerAnchors).filter((anchor) => {
        if (anchor.sessionId !== activeSessionId) {
          return false;
        }
        const status = workerUpdates[anchor.workerRunId]?.status ?? "queued";
        return ["queued", "running", "waiting_input"].includes(status);
      }),
    [activeSessionId, workerAnchors, workerUpdates]
  );
  const workerUpdatesByMessage = useMemo(() => {
    const messageMap: Record<string, AxeWorkerUpdate[]> = {};

    Object.values(workerAnchors).forEach((anchor) => {
      if (anchor.sessionId !== activeSessionId) {
        return;
      }

      const update = workerUpdates[anchor.workerRunId];
      if (!update) {
        return;
      }

      const keys = [
        anchor.localMessageId ? `local:${anchor.localMessageId}` : null,
        anchor.messageId ? `session:${anchor.messageId}` : null,
      ].filter((value): value is string => Boolean(value));

      keys.forEach((key) => {
        if (!messageMap[key]) {
          messageMap[key] = [];
        }
        messageMap[key].push(update);
      });
    });

    return messageMap;
  }, [activeSessionId, workerAnchors, workerUpdates]);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    const bootstrap = async () => {
      await loadSessions();
    };
    void bootstrap();
  }, [loadSessions]);

  useEffect(() => {
    if (sessionsLoading || activeSessionId) {
      return;
    }

    const ensureSession = async () => {
      await createSession();
    };
    void ensureSession();
  }, [activeSessionId, createSession, sessionsLoading]);

  useEffect(() => {
    const ctx: PluginContext = {
      appId: "axe-chat",
      sessionId: pluginSessionId,
      backendUrl: typeof window !== "undefined" ? window.location.origin : "",
      locale: "de",
    };
    setPluginContext(ctx);
    pluginRegistry.register(slashCommandsPlugin);
    initializePlugins(ctx).catch((pluginError) => console.error("Plugin init failed:", pluginError));

    return () => {
      destroyPlugins().catch((pluginError) => console.error("Plugin destroy failed:", pluginError));
    };
  }, [pluginSessionId]);

  useEffect(() => {
    if (!activeSession) {
      setMessages([
        {
          id: 1,
          role: "assistant",
          content:
            "Hello! I'm the AXE (Auxiliary Execution Engine) agent. I can help you execute commands, analyze logs, and monitor system status. How can I assist you today?",
          timestamp: new Date(),
        },
      ]);
      return;
    }

    const loaded = activeSession.messages.map((message, index) => ({
      id: index + 1,
      sessionMessageId: message.id,
      role: message.role,
      content: message.content,
      timestamp: new Date(message.created_at),
    }));

    setMessages(
      loaded.length > 0
        ? loaded
        : [
            {
              id: 1,
              role: "assistant",
              content:
                "Hello! I'm the AXE (Auxiliary Execution Engine) agent. I can help you execute commands, analyze logs, and monitor system status. How can I assist you today?",
              timestamp: new Date(),
            },
          ]
    );
  }, [activeSession]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const persistMessage = async (
    sessionId: string,
    role: AxeSessionMessageRole,
    content: string,
    attachmentIds: string[] = []
  ): Promise<AxeSessionMessage> => {
    return withAuthRetry((token) =>
      appendAxeSessionMessage(
        sessionId,
        {
          role,
          content,
          attachments: attachmentIds,
        },
        { Authorization: `Bearer ${token}` }
      )
    );
  };

  useEffect(() => {
    if (activePollingAnchors.length === 0) {
      return;
    }

    const interval = window.setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState !== "visible") {
        return;
      }

      void withAuthRetry(async (token) => {
        const updates = await Promise.all(
          activePollingAnchors.map(async (anchor) => {
            try {
              const update = await getAxeWorkerRun(anchor.workerRunId, { Authorization: `Bearer ${token}` });
              return [anchor.workerRunId, update] as const;
            } catch {
              return null;
            }
          })
        );

        const nextEntries = updates.filter((entry): entry is readonly [string, AxeWorkerUpdate] => entry !== null);
        if (nextEntries.length === 0) {
          return;
        }

        setWorkerUpdates((prev) => {
          const merged = { ...prev };
          nextEntries.forEach(([workerRunId, update]) => {
            merged[workerRunId] = update;
          });
          return merged;
        });
      });
    }, 4000);

    return () => window.clearInterval(interval);
  }, [activePollingAnchors, withAuthRetry]);

  useEffect(() => {
    const loadTrace = async () => {
      try {
        if (typeof document !== "undefined" && document.visibilityState !== "visible") {
          return;
        }
        setTraceLoading(true);
        setTraceError(null);
        const [purposeData, routingData] = await withAuthRetry((token) =>
          Promise.all([
            listPurposeEvaluations(5, { Authorization: `Bearer ${token}` }),
            listRoutingDecisions(5, { Authorization: `Bearer ${token}` }),
          ])
        );
        setPurposeTrace(purposeData.items);
        setRoutingTrace(routingData.items);
      } catch (traceLoadError) {
        setTraceError(traceLoadError instanceof Error ? traceLoadError.message : "Unable to load governance trace");
      } finally {
        setTraceLoading(false);
      }
    };
    void loadTrace();
  }, [withAuthRetry]);

  const ensureActiveSessionId = async (): Promise<string | null> => {
    if (activeSessionId) {
      return activeSessionId;
    }
    const created = await createSession();
    return created?.id ?? null;
  };

  const handleSend = async () => {
    if (!input.trim() || loading || hasUploadingAttachments || uploadLock) return;

    const failedCount = attachments.filter((item) => item.status === "error").length;
    if (failedCount > 0) {
      const proceed = window.confirm(
        `${failedCount} attachment upload(s) failed. Send message without failed attachments?`
      );
      if (!proceed) {
        return;
      }
    }

    const currentSessionId = await ensureActiveSessionId();
    if (!currentSessionId) {
      setError("Unable to create a chat session.");
      return;
    }

    const trimmedInput = input.trim();
    const isSlashCommand = trimmedInput.startsWith("/");
    const userMessage: Message = {
      id: messages.length + 1,
      role: "user",
      content: trimmedInput,
      timestamp: new Date(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);
    setError(null);

    const readyAttachmentIds = attachments
      .filter((item) => item.status === "ready" && item.attachmentId)
      .map((item) => item.attachmentId as string);

    try {
      const persistedUserMessage = await persistMessage(currentSessionId, "user", trimmedInput, readyAttachmentIds);
      const userMessageId = persistedUserMessage.id;

      if (isSlashCommand && pluginContext) {
        const command = trimmedInput.slice(1).split(" ")[0];
        const result = await pluginRegistry.handleCommand(command, { args: trimmedInput });
        if (result && typeof result === "string") {
          const assistantMessage: Message = {
            id: messages.length + 2,
            role: "assistant",
            content: result,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
          await persistMessage(currentSessionId, "assistant", result);
          await selectSession(currentSessionId);
          setAttachments([]);
          setLoading(false);
          return;
        }
      }

      const apiMessages = updatedMessages.map((message) => ({
        role: message.role,
        content: message.content,
      }));

      const requestBody: AxeChatRequest = {
        messages: apiMessages,
        model: DEFAULT_MODEL,
        temperature: 0.7,
        attachments: readyAttachmentIds,
        session_id: currentSessionId || undefined,
      };

      const data = await withAuthRetry((token) =>
        postAxeChat(requestBody, { Authorization: `Bearer ${token}` })
      );

      if (data.worker_run_id) {
        const initialUpdate: AxeWorkerUpdate = {
          worker_run_id: data.worker_run_id,
          session_id: data.session_id ?? currentSessionId,
          message_id: data.message_id ?? userMessageId,
          status: "queued",
          label: "OpenCode worker queued",
          detail: "BRAiN delegated this request to a worker. Awaiting status updates.",
          updated_at: new Date().toISOString(),
          artifacts: [],
        };
        setWorkerUpdates((prev) => ({ ...prev, [data.worker_run_id as string]: initialUpdate }));
        setWorkerAnchors((prev) => ({
          ...prev,
          [data.worker_run_id as string]: {
            workerRunId: data.worker_run_id as string,
            sessionId: data.session_id ?? currentSessionId,
            messageId: data.message_id ?? userMessageId,
            localMessageId: userMessage.id,
          },
        }));
      }

      if (!data.text) {
        throw new Error("Invalid response: missing 'text' field");
      }

      const assistantMessage: Message = {
        id: messages.length + 2,
        role: "assistant",
        content: data.text,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      await persistMessage(currentSessionId, "assistant", data.text);
      await selectSession(currentSessionId);
      setAttachments([]);
    } catch (sendError) {
      const errorMsg = sendError instanceof Error ? sendError.message : "Unknown error occurred";
      setError(errorMsg);
      const errorMessage: Message = {
        id: messages.length + 2,
        role: "assistant",
        content: `Sorry, I encountered an error: ${errorMsg}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const uploadFiles = async (files: FileList | File[] | null) => {
    if (!files || files.length === 0 || uploadLock) return;

    setUploadLock(true);
    const fileArray = Array.from(files);

    try {
      for (const file of fileArray) {
        const localId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        setAttachments((prev) => [...prev, { localId, name: file.name, status: "uploading" }]);

        try {
          const uploaded = await withAuthRetry((token) =>
            uploadAxeAttachment(file, { Authorization: `Bearer ${token}` })
          );
          setAttachments((prev) =>
            prev.map((item) =>
              item.localId === localId
                ? {
                    ...item,
                    status: "ready",
                    attachmentId: uploaded.attachment_id,
                    name: uploaded.filename,
                  }
                : item
            )
          );
        } catch (uploadError) {
          const message = uploadError instanceof Error ? uploadError.message : "Upload failed";
          setAttachments((prev) =>
            prev.map((item) => (item.localId === localId ? { ...item, status: "error", error: message } : item))
          );
        }
      }
    } finally {
      setUploadLock(false);
    }
  };

  const removeAttachment = (localId: string) => {
    setAttachments((prev) => prev.filter((item) => item.localId !== localId));
  };

  const clearFailedAttachments = () => {
    setAttachments((prev) => prev.filter((item) => item.status !== "error"));
  };

  const openImageFallbackPicker = () => {
    cameraFallbackInputRef.current?.click();
  };

  const handleOpenCamera = async () => {
    if (typeof window === "undefined") return;

    if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
      setError("Camera API not available in this browser. Please upload an image instead.");
      openImageFallbackPicker();
      return;
    }

    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cameraDevices = devices.filter((device) => device.kind === "videoinput");
      if (cameraDevices.length === 0) {
        setError("No physical camera detected on this system. Switched to image picker.");
        openImageFallbackPicker();
        return;
      }
    } catch {
      // getUserMedia provides a more explicit stream error.
    }

    try {
      if (navigator.permissions && typeof navigator.permissions.query === "function") {
        const permissionResult = await navigator.permissions.query({
          name: "camera" as PermissionName,
        });
        if (permissionResult.state === "denied") {
          setError("Camera permission denied. Please allow access or upload an image instead.");
          openImageFallbackPicker();
          return;
        }
      }
    } catch {
      // Ignore permission query errors and continue.
    }

    setCameraOpen(true);
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey && !isMobileDevice()) {
      event.preventDefault();
      void handleSend();
    }
  };

  const headerError = useMemo(() => sessionsError || error, [error, sessionsError]);
  const handleRenameSession = useCallback(async (sessionId: string, title: string) => {
    await renameSession(sessionId, title);
  }, [renameSession]);

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    await removeSession(sessionId);
    await loadSessions();
  }, [loadSessions, removeSession]);

  const handleCreateSession = useCallback(async () => {
    await createSession();
  }, [createSession]);

  const handleSelectSession = useCallback(async (sessionId: string) => {
    if (sessionId === activeSessionId) {
      return;
    }
    await selectSession(sessionId);
  }, [activeSessionId, selectSession]);

  const intentHelpTopic = getAxeHelpTopic("axe.chat.intent");

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex min-h-0 flex-1 gap-4">
        <ChatSidebar
          groupedSessions={groupedSessions}
          activeSessionId={activeSessionId}
          loading={sessionsLoading}
          showMobileTrigger={false}
          onSelectSession={handleSelectSession}
          onRenameSession={handleRenameSession}
          onDeleteSession={handleDeleteSession}
          onCreateSession={handleCreateSession}
        />

        <div className="flex min-h-0 flex-1 flex-col">
          <header className="lg:hidden flex items-center justify-between border-b border-cyan-500/10 bg-slate-950/70 p-4">
            <div className="ml-14">
              <h1 className="axe-surface-title text-lg font-bold text-white">AXE Surface</h1>
            </div>
            <ChatSidebar
              groupedSessions={groupedSessions}
              activeSessionId={activeSessionId}
              loading={sessionsLoading}
              showDesktopRail={false}
              onSelectSession={handleSelectSession}
              onRenameSession={handleRenameSession}
              onDeleteSession={handleDeleteSession}
              onCreateSession={handleCreateSession}
            />
          </header>

          <div className="mb-6 hidden lg:block">
            <div className="mb-2 flex items-center gap-2">
              <p className="text-[11px] uppercase tracking-[0.2em] text-cyan-300/70">Intent Surface</p>
              {intentHelpTopic ? <HelpHint topic={intentHelpTopic} /> : null}
            </div>
            <h1 className="axe-surface-title text-3xl font-bold text-white">AXE Cognitive Relay</h1>
            <p className="mt-2 max-w-2xl text-slate-400">
              Formulate operator intent. BRAiN coordinates execution across internal systems, external agents, and robotic handoffs.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <span className="axe-chip rounded-full px-3 py-1">Presence: linked</span>
              <span className="axe-chip rounded-full px-3 py-1">Memory: synchronized</span>
              <span className="axe-chip rounded-full px-3 py-1">Relay mode: orchestration</span>
            </div>
          </div>

          <div className="axe-panel mb-4 rounded-xl p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="axe-surface-title text-sm font-semibold text-white">Decision Trace</h2>
              <a
                href={controlDeckProviderUrl}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-cyan-300 underline hover:text-cyan-200"
              >
                Manage governance in ControlDeck
              </a>
            </div>
            {traceLoading && <p className="text-xs text-slate-500">Loading latest governance signals...</p>}
            {traceError && <p className="text-xs text-rose-300">{traceError}</p>}
            {!traceLoading && !traceError && (
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-slate-700/60 bg-slate-900/70 p-3">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-cyan-300/70">Purpose</p>
                  {purposeTrace.length === 0 && <p className="mt-2 text-xs text-slate-500">No recent purpose outcomes.</p>}
                  {purposeTrace.slice(0, 2).map((item) => (
                    <div key={item.id} className="mt-2 text-xs text-slate-300">
                      <p className="font-mono text-slate-400">{item.decision_context_id}</p>
                      <p>
                        outcome: <span className="text-cyan-200">{item.outcome}</span>
                      </p>
                      <p className="text-slate-500">mode: {String(item.governance_snapshot?.control_mode ?? "brain_first")}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg border border-slate-700/60 bg-slate-900/70 p-3">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-amber-300/70">Routing</p>
                  {routingTrace.length === 0 && <p className="mt-2 text-xs text-slate-500">No recent routing outcomes.</p>}
                  {routingTrace.slice(0, 2).map((item) => (
                    <div key={item.id} className="mt-2 text-xs text-slate-300">
                      <p className="font-mono text-slate-400">{item.task_profile_id}</p>
                      <p>
                        worker: <span className="text-cyan-200">{item.selected_worker ?? "unassigned"}</span>
                      </p>
                      <p className="text-slate-500">strategy: {item.strategy}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {headerError && (
            <div className="mb-4 rounded-lg border border-rose-500/50 bg-rose-950/45 p-3 text-sm text-rose-200">
              ⚠️ Error: {headerError}
            </div>
          )}

          <div className="axe-panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl">
            <div className="border-b border-cyan-500/10 px-4 py-3 text-xs text-slate-400 sm:px-6">
              Active Thread: <span className="text-cyan-200">{activeSession?.title ?? "New Intent Thread"}</span>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto p-3 sm:space-y-4 sm:p-6">
              {messages.map((message) => (
                <div key={message.id}>
                  <div className={`flex gap-2 sm:gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                    {message.role === "assistant" && (
                      <div className="hidden shrink-0 sm:block">
                        <div className="axe-ring flex h-8 w-8 items-center justify-center rounded-full border border-cyan-300/40 bg-cyan-500/15">
                          <span className="text-sm">🤖</span>
                        </div>
                      </div>
                    )}

                    <div
                      className={`max-w-[85%] break-words rounded-lg p-3 sm:max-w-[70%] sm:p-4 ${
                        message.role === "user"
                          ? "border border-cyan-300/35 bg-cyan-500/15 text-cyan-50"
                          : "border border-slate-700 bg-slate-900/80 text-slate-100"
                      }`}
                    >
                      <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                      <p className="mt-2 text-xs opacity-70" suppressHydrationWarning>
                        {isClient ? formatTime(message.timestamp) : ""}
                      </p>

                      {Array.from(
                        new Map(
                          (workerUpdatesByMessage[`local:${message.id}`] ?? [])
                            .concat(
                              message.sessionMessageId
                                ? workerUpdatesByMessage[`session:${message.sessionMessageId}`] ?? []
                                : []
                            )
                            .map((update) => [update.worker_run_id, update])
                        ).values()
                      ).map((update) => <WorkerRunCard key={update.worker_run_id} update={update} />)}
                    </div>

                    {message.role === "user" && (
                      <div className="hidden shrink-0 sm:block">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-amber-400/35 bg-amber-500/15">
                          <span className="text-sm">👤</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-lg border border-cyan-500/25 bg-slate-900/75 p-4">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="h-2 w-2 animate-bounce rounded-full bg-cyan-300" />
                        <div className="h-2 w-2 animate-bounce rounded-full bg-cyan-300" style={{ animationDelay: "0.1s" }} />
                        <div className="h-2 w-2 animate-bounce rounded-full bg-cyan-300" style={{ animationDelay: "0.2s" }} />
                      </div>
                      <span className="text-sm text-cyan-100/80">Synthesizing operator intent...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-cyan-500/10 bg-slate-950/55 p-3 sm:p-4">
              {attachments.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                  {attachments.map((attachment) => (
                    <div
                      key={attachment.localId}
                      className="inline-flex items-center gap-2 rounded-md border border-cyan-500/25 bg-slate-900/80 px-2 py-1 text-xs text-slate-200"
                    >
                      <span className="max-w-[140px] truncate">{attachment.name}</span>
                      <span
                        className={
                          attachment.status === "ready"
                            ? "text-emerald-400"
                            : attachment.status === "error"
                              ? "text-rose-400"
                              : "text-blue-300"
                        }
                      >
                        {attachment.status}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeAttachment(attachment.localId)}
                        className="text-slate-400 hover:text-slate-100"
                        aria-label="Remove attachment"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}

                  {hasFailedAttachments && (
                    <button
                      type="button"
                      onClick={clearFailedAttachments}
                      className="text-xs text-rose-300 underline hover:text-rose-200"
                    >
                      Clear failed uploads
                    </button>
                  )}
                </div>
              )}

              {pluginContext && <ComposerActions context={pluginContext} />}

              <div className="flex items-end gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept="image/jpeg,image/png,image/webp,application/pdf,text/plain"
                  multiple
                  onChange={(event) => {
                    void uploadFiles(event.target.files);
                    event.target.value = "";
                  }}
                />
                <input
                  ref={cameraFallbackInputRef}
                  type="file"
                  className="hidden"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) => {
                    void uploadFiles(event.target.files);
                    event.target.value = "";
                  }}
                />

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading || hasUploadingAttachments || uploadLock}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-cyan-500/30 bg-slate-900/80 text-cyan-100 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:opacity-60"
                  aria-label="Upload file"
                  title="Upload file"
                >
                  <Paperclip className="h-5 w-5" />
                </button>

                <button
                  type="button"
                  onClick={() => void handleOpenCamera()}
                  disabled={loading || hasUploadingAttachments || uploadLock}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-cyan-500/30 bg-slate-900/80 text-cyan-100 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:opacity-60"
                  aria-label="Take photo"
                  title="Take photo"
                >
                  <Camera className="h-5 w-5" />
                </button>

                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your message..."
                  disabled={loading}
                  rows={1}
                  className="min-h-[44px] max-h-[200px] flex-1 resize-none rounded-lg border border-cyan-500/25 bg-slate-900/80 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-400 disabled:opacity-50 sm:px-4 sm:py-3 sm:text-base"
                />

                <button
                  onClick={() => void handleSend()}
                  disabled={!input.trim() || loading || hasUploadingAttachments || uploadLock}
                  className="axe-ring flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-cyan-500/80 text-slate-950 transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
                  aria-label="Send message"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </button>
              </div>
            </div>
          </div>

          <div className="axe-panel mt-4 hidden rounded-xl p-4 sm:block">
            <p className="mb-2 text-sm text-slate-400">Mission shortcuts:</p>
            <div className="flex flex-wrap gap-2">
              {["Check system status", "List active agents", "Show recent logs", "Coordinate robot relay"].map((cmd) => (
                <button
                  key={cmd}
                  onClick={() => setInput(cmd)}
                  className="rounded-lg border border-cyan-400/20 bg-slate-900/70 px-3 py-1 text-xs text-cyan-100/90 transition-colors hover:bg-cyan-500/20"
                >
                  {cmd}
                </button>
              ))}
            </div>
          </div>

          <AdvancedCameraCapture
            open={cameraOpen}
            onClose={() => setCameraOpen(false)}
            onCapture={async (file) => {
              await uploadFiles([file]);
            }}
            onFallbackToFilePicker={openImageFallbackPicker}
          />
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return <ChatPageContent />;
}
