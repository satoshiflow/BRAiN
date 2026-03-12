"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Camera, Loader2, Paperclip, Send, X } from "lucide-react";
import { AuthGate } from "@/components/auth/AuthGate";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { AdvancedCameraCapture } from "@/components/chat/AdvancedCameraCapture";
import { appendAxeSessionMessage, postAxeChat, uploadAxeAttachment } from "@/lib/api";
import { getDefaultModel } from "@/lib/config";
import type { AxeChatRequest, AxeSessionMessageRole } from "@/lib/contracts";
import { useAuthSession } from "@/hooks/useAuthSession";
import { useChatSessions } from "@/hooks/useChatSessions";
import { pluginRegistry, initializePlugins, destroyPlugins, type PluginContext } from "../../src/plugins";
import slashCommandsPlugin from "../../src/plugins/slashCommands";

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
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

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraFallbackInputRef = useRef<HTMLInputElement>(null);

  const hasUploadingAttachments = attachments.some((item) => item.status === "uploading");
  const hasFailedAttachments = attachments.some((item) => item.status === "error");

  const pluginSessionId = activeSessionId ?? pluginFallbackSessionId;

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
  ) => {
    await withAuthRetry((token) =>
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

  const ensureActiveSessionId = async (): Promise<string | null> => {
    if (activeSessionId) {
      return activeSessionId;
    }
    const created = await createSession();
    return created?.id ?? null;
  };

  const handleSend = async () => {
    if (!input.trim() || loading || hasUploadingAttachments || uploadLock) return;

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
      await persistMessage(currentSessionId, "user", trimmedInput, readyAttachmentIds);

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

      const failedCount = attachments.filter((item) => item.status === "error").length;
      if (failedCount > 0) {
        const proceed = window.confirm(
          `${failedCount} attachment upload(s) failed. Send message without failed attachments?`
        );
        if (!proceed) {
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
      };

      const data = await withAuthRetry((token) =>
        postAxeChat(requestBody, { Authorization: `Bearer ${token}` })
      );

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

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex min-h-0 flex-1 gap-4">
        <ChatSidebar
          groupedSessions={groupedSessions}
          activeSessionId={activeSessionId}
          loading={sessionsLoading}
          onSelectSession={selectSession}
          onRenameSession={async (sessionId, title) => {
            await renameSession(sessionId, title);
            await selectSession(sessionId);
          }}
          onDeleteSession={async (sessionId) => {
            await removeSession(sessionId);
            await loadSessions();
          }}
          onCreateSession={async () => {
            const created = await createSession();
            if (created) {
              await selectSession(created.id);
            }
          }}
        />

        <div className="flex min-h-0 flex-1 flex-col">
          <header className="lg:hidden flex items-center justify-center border-b border-slate-800 bg-slate-900 p-4">
            <div className="ml-14">
              <h1 className="text-lg font-bold text-white">AXE Chat</h1>
            </div>
          </header>

          <div className="mb-6 hidden lg:block">
            <h1 className="text-3xl font-bold text-white">AXE Chat</h1>
            <p className="mt-2 text-slate-400">Conversational interface with the Auxiliary Execution Engine</p>
          </div>

          {headerError && (
            <div className="mb-4 rounded-lg border border-red-700 bg-red-900/50 p-3 text-sm text-red-200">
              ⚠️ Error: {headerError}
            </div>
          )}

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
            <div className="flex-1 space-y-3 overflow-y-auto p-3 sm:space-y-4 sm:p-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-2 sm:gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {message.role === "assistant" && (
                    <div className="hidden shrink-0 sm:block">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600">
                        <span className="text-sm">🤖</span>
                      </div>
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] break-words rounded-lg p-3 sm:max-w-[70%] sm:p-4 ${
                      message.role === "user"
                        ? "bg-blue-600 text-white"
                        : "border border-slate-700 bg-slate-800 text-slate-100"
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                    <p className="mt-2 text-xs opacity-70" suppressHydrationWarning>
                      {isClient ? formatTime(message.timestamp) : ""}
                    </p>
                  </div>

                  {message.role === "user" && (
                    <div className="hidden shrink-0 sm:block">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-700">
                        <span className="text-sm">👤</span>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="h-2 w-2 animate-bounce rounded-full bg-slate-500" />
                        <div className="h-2 w-2 animate-bounce rounded-full bg-slate-500" style={{ animationDelay: "0.1s" }} />
                        <div className="h-2 w-2 animate-bounce rounded-full bg-slate-500" style={{ animationDelay: "0.2s" }} />
                      </div>
                      <span className="text-sm text-slate-400">AXE is thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-slate-800 bg-slate-900 p-3 sm:p-4">
              {attachments.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                  {attachments.map((attachment) => (
                    <div
                      key={attachment.localId}
                      className="inline-flex items-center gap-2 rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-200"
                    >
                      <span className="max-w-[140px] truncate">{attachment.name}</span>
                      <span
                        className={
                          attachment.status === "ready"
                            ? "text-emerald-400"
                            : attachment.status === "error"
                              ? "text-red-400"
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
                      className="text-xs text-red-300 underline hover:text-red-200"
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
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-slate-700 bg-slate-800 text-white transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:opacity-60"
                  aria-label="Datei hochladen"
                  title="Datei hochladen"
                >
                  <Paperclip className="h-5 w-5" />
                </button>

                <button
                  type="button"
                  onClick={() => void handleOpenCamera()}
                  disabled={loading || hasUploadingAttachments || uploadLock}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-slate-700 bg-slate-800 text-white transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:opacity-60"
                  aria-label="Foto machen"
                  title="Foto machen"
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
                  className="min-h-[44px] max-h-[200px] flex-1 resize-none rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 sm:px-4 sm:py-3 sm:text-base"
                />

                <button
                  onClick={() => void handleSend()}
                  disabled={!input.trim() || loading || hasUploadingAttachments || uploadLock}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-700"
                  aria-label="Send message"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </button>
              </div>
            </div>
          </div>

          <div className="mt-4 hidden rounded-lg border border-slate-800 bg-slate-900 p-4 sm:block">
            <p className="mb-2 text-sm text-slate-400">Quick commands:</p>
            <div className="flex flex-wrap gap-2">
              {["Check system status", "List active agents", "Show recent logs", "Get mission queue"].map((cmd) => (
                <button
                  key={cmd}
                  onClick={() => setInput(cmd)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-300 transition-colors hover:bg-slate-700"
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
  return (
    <AuthGate>
      <ChatPageContent />
    </AuthGate>
  );
}
