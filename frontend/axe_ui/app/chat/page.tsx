"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Loader2, Paperclip, Camera, X } from "lucide-react";
import { getDefaultModel } from "@/lib/config";
import { postAxeChat, uploadAxeAttachment } from "@/lib/api";
import type { AxeChatRequest } from "@/lib/contracts";
import { AdvancedCameraCapture } from "@/components/chat/AdvancedCameraCapture";
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

// Format time safely (avoids hydration mismatch)
function formatTime(date: Date): string {
  if (typeof window === 'undefined') return '';
  return date.toLocaleTimeString();
}

// Detect mobile device
function isMobileDevice() {
  if (typeof window === 'undefined') return false;
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
}

function generateSessionId(): string {
  return `axe_session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

function ComposerActions({ context }: { context: PluginContext }) {
  const renderers = pluginRegistry.renderUiSlot("composer.actions");
  if (renderers.length === 0) return null;
  return (
    <div className="flex gap-2 mb-2">
      {renderers.map((Renderer, idx) => (
        <Renderer key={idx} context={context} />
      ))}
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isClient, setIsClient] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState(() => generateSessionId());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pluginContext, setPluginContext] = useState<PluginContext | null>(null);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [uploadLock, setUploadLock] = useState(false);

  const hasUploadingAttachments = attachments.some((item) => item.status === "uploading");
  const hasFailedAttachments = attachments.some((item) => item.status === "error");

  useEffect(() => {
    const ctx: PluginContext = {
      appId: "axe-chat",
      sessionId,
      backendUrl: typeof window !== "undefined" ? window.location.origin : "",
      locale: "de",
    };
    setPluginContext(ctx);
    pluginRegistry.register(slashCommandsPlugin);
    initializePlugins(ctx).catch((err) => console.error("Plugin init failed:", err));
    return () => {
      destroyPlugins().catch((err) => console.error("Plugin destroy failed:", err));
    };
  }, [sessionId]);

  useEffect(() => {
    setIsClient(true);
    setMessages([
      {
        id: 1,
        role: "assistant",
        content: "Hello! I'm the AXE (Auxiliary Execution Engine) agent. I can help you execute commands, analyze logs, and monitor system status. How can I assist you today?",
        timestamp: new Date(),
      },
    ]);
  }, []);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || loading || hasUploadingAttachments || uploadLock) return;

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

    try {
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
          setLoading(false);
          return;
        }
      }

      const apiMessages = updatedMessages
        .map(m => ({
          role: m.role as "user" | "assistant",
          content: m.content
        }));

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

      const requestBody: AxeChatRequest = {
        messages: apiMessages,
        model: DEFAULT_MODEL,
        temperature: 0.7,
        attachments: attachments
          .filter((item) => item.status === "ready" && item.attachmentId)
          .map((item) => item.attachmentId as string),
      };

      const data = await postAxeChat(requestBody);

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
      setAttachments([]);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error occurred";
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
    if (!files || files.length === 0) return;
    if (uploadLock) return;

    setUploadLock(true);

    const fileArray = Array.from(files);
    try {
      for (const file of fileArray) {
        const localId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        setAttachments((prev) => [
          ...prev,
          {
            localId,
            name: file.name,
            status: "uploading",
          },
        ]);

        try {
          const uploaded = await uploadAxeAttachment(file);
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
            prev.map((item) =>
              item.localId === localId
                ? {
                    ...item,
                    status: "error",
                    error: message,
                  }
                : item
            )
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    // Desktop: Enter to send, Shift+Enter for new line
    // Mobile: Always allow new lines (no keyboard shortcuts)
    if (e.key === "Enter" && !e.shiftKey && !isMobileDevice()) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Mobile Header (visible when sidebar hidden) */}
      <header className="lg:hidden flex items-center justify-center p-4 border-b border-slate-800 bg-slate-900">
        <div className="ml-14"> {/* Offset for hamburger button */}
          <h1 className="text-lg font-bold text-white">AXE Chat</h1>
        </div>
      </header>

      {/* Desktop Header */}
      <div className="hidden lg:block mb-6">
        <h1 className="text-3xl font-bold text-white">AXE Chat</h1>
        <p className="text-slate-400 mt-2">
          Conversational interface with the Auxiliary Execution Engine
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
          ⚠️ Error: {error}
        </div>
      )}

      {/* Chat Container */}
      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-3 sm:space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-2 sm:gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {/* Avatar - Hidden on very small screens */}
              {message.role === "assistant" && (
                <div className="hidden sm:block shrink-0">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                    <span className="text-sm">🤖</span>
                  </div>
                </div>
              )}

              {/* Message Bubble - Mobile optimized width */}
              <div
                className={`rounded-lg p-3 sm:p-4 max-w-[85%] sm:max-w-[70%] break-words ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-800 text-slate-100 border border-slate-700"
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                <p className="text-xs opacity-70 mt-2" suppressHydrationWarning>
                  {isClient ? formatTime(message.timestamp) : ''}
                </p>
              </div>

              {/* User Avatar - Hidden on very small screens */}
              {message.role === "user" && (
                <div className="hidden sm:block shrink-0">
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
                    <span className="text-sm">👤</span>
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-slate-500 animate-bounce"></div>
                    <div
                      className="w-2 h-2 rounded-full bg-slate-500 animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    ></div>
                    <div
                      className="w-2 h-2 rounded-full bg-slate-500 animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                  </div>
                  <span className="text-sm text-slate-400">AXE is thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input - Mobile optimized */}
        <div className="border-t border-slate-800 p-3 sm:p-4 bg-slate-900">
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
                  className="text-xs text-red-300 hover:text-red-200 underline"
                >
                  Clear failed uploads
                </button>
              )}
            </div>
          )}

          {pluginContext && <ComposerActions context={pluginContext} />}
          <div className="flex gap-2 items-end">
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
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading || hasUploadingAttachments || uploadLock}
              className="shrink-0 h-11 w-11 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700 disabled:opacity-60 text-white rounded-lg transition-colors flex items-center justify-center border border-slate-700"
              aria-label="Datei hochladen"
              title="Datei hochladen"
            >
              <Paperclip className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={() => setCameraOpen(true)}
              disabled={loading || hasUploadingAttachments || uploadLock}
              className="shrink-0 h-11 w-11 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700 disabled:opacity-60 text-white rounded-lg transition-colors flex items-center justify-center border border-slate-700"
              aria-label="Foto machen"
              title="Foto machen"
            >
              <Camera className="h-5 w-5" />
            </button>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Type your message..."
              disabled={loading}
              rows={1}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 sm:px-4 py-2 sm:py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 resize-none min-h-[44px] max-h-[200px] text-sm sm:text-base"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading || hasUploadingAttachments || uploadLock}
              className="shrink-0 h-11 w-11 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center"
              aria-label="Send message"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Quick Commands - Hidden on very small screens */}
      <div className="hidden sm:block mt-4 p-4 bg-slate-900 border border-slate-800 rounded-lg">
        <p className="text-sm text-slate-400 mb-2">Quick commands:</p>
        <div className="flex flex-wrap gap-2">
          {["Check system status", "List active agents", "Show recent logs", "Get mission queue"].map(
            (cmd) => (
              <button
                key={cmd}
                onClick={() => setInput(cmd)}
                className="px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
              >
                {cmd}
              </button>
            )
          )}
        </div>
      </div>

      <AdvancedCameraCapture
        open={cameraOpen}
        onClose={() => setCameraOpen(false)}
        onCapture={async (file) => {
          await uploadFiles([file]);
        }}
      />
    </div>
  );
}
