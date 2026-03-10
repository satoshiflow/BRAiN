"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { X, Send, MessageCircle, Minimize2, Paperclip, Camera, Maximize2 } from "lucide-react";
import type { FloatingAxeConfig, FloatingAxeInstance, AXEWidgetEvent } from "@/lib/embedConfig";
import type { PluginHook, PluginHookHandler } from "@/src/plugins/types";
import {
  validateConfig,
  validateOrigin,
  normalizeOriginAllowlist,
  generateSessionId,
  createEmbeddingError,
  isEmbeddingError,
} from "@/lib/embedConfig";
import { pluginRegistry, initializePlugins, destroyPlugins, type PluginContext } from "@/src/plugins";
import slashCommandsPlugin from "@/src/plugins/slashCommands";
import { registerDynamicPlugin, unregisterDynamicPlugin } from "@/src/plugins/dynamicRegistry";
import { BrandingSystem } from "@/src/branding/brandingSystem";
import { AnalyticsMiddleware } from "@/src/analytics/analyticsMiddleware";
import { WebhookSystem, createWebhookPayload } from "@/src/webhooks/webhookSystem";
import { OfflineManager, registerOfflineSW, type StoredMessage, type SyncState } from "@/src/offline/offlineManager";
import { postAxeChat, uploadAxeAttachment } from "@/lib/api";
import type { AxeChatRequest } from "@/lib/contracts";
import { getDefaultModel } from "@/lib/config";
import { CodeEditor } from "@/src/components/CodeEditor";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface UploadedAttachment {
  id: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
}

interface EventListener {
  event: AXEWidgetEvent;
  callback: (...args: unknown[]) => void;
}

const DEFAULT_MODEL = getDefaultModel();

/**
 * FloatingAxe Widget Component
 * 
 * A mobile-first, floating chat interface that can be embedded on external websites.
 * Provides:
 * - Chat interface with plugin support
 * - Origin validation for security
 * - Event bus for plugin communication
 * - Session management
 */
export const FloatingAxe = React.forwardRef<FloatingAxeInstance, FloatingAxeConfig>(
  (config, forwardedRef) => {
    // State management
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isInitialized, setIsInitialized] = useState(false);
    const [isCanvasOpen, setIsCanvasOpen] = useState(false);
    const [editorValue, setEditorValue] = useState("// AXE Canvas\n// Paste or draft code here\n");
    const [attachments, setAttachments] = useState<UploadedAttachment[]>([]);
    const [isUploadingAttachment, setIsUploadingAttachment] = useState(false);
    const [syncState, setSyncState] = useState<SyncState>("synced");
    const [pendingSyncCount, setPendingSyncCount] = useState(0);
    const [sessionId] = useState(() => config.sessionId || generateSessionId());

    // Refs
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const eventListenersRef = useRef<EventListener[]>([]);
    const pluginContextRef = useRef<PluginContext | null>(null);
    const widgetRef = useRef<FloatingAxeInstance | null>(null);
    const analyticsRef = useRef<AnalyticsMiddleware | null>(null);
    const webhookRef = useRef<WebhookSystem | null>(null);
    const offlineRef = useRef<OfflineManager | null>(null);
    const brandingRef = useRef<BrandingSystem | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const cameraInputRef = useRef<HTMLInputElement>(null);

    // Debug logging
    const log = useCallback(
      (level: string, message: string, data?: unknown) => {
        if (config.debug) {
          console.log(`[FloatingAxe:${level}]`, message, data || "");
        }
      },
      [config.debug]
    );

    // Event emission
    const emit = useCallback((event: AXEWidgetEvent | string, ...args: unknown[]) => {
      log("debug", `Emitting event: ${event}`, args);
      eventListenersRef.current.forEach((listener) => {
        if (listener.event === event) {
          listener.callback(...args);
        }
      });
    }, [log]);

    // Event subscription
    const on = useCallback((event: AXEWidgetEvent, callback: (...args: unknown[]) => void) => {
      const listener: EventListener = { event, callback };
      eventListenersRef.current.push(listener);
      // Return unsubscribe function
      return () => {
        eventListenersRef.current = eventListenersRef.current.filter((l) => l !== listener);
      };
    }, []);

    // Initialize widget
    useEffect(() => {
      const handleSyncState = (event: Event) => {
        const customEvent = event as CustomEvent<{ sessionId: string; state: SyncState; pending: number }>;
        if (customEvent.detail?.sessionId !== sessionId) {
          return;
        }
        setSyncState(customEvent.detail.state);
        setPendingSyncCount(customEvent.detail.pending);
      };

      const initializeWidget = async () => {
        try {
          log("info", "Initializing FloatingAxe widget");

          // Validate config
          const configValidation = validateConfig(config);
          if (!configValidation.valid) {
            throw createEmbeddingError("CONFIG_INVALID", configValidation.error || "Invalid config");
          }

          // Validate origin
          const allowlist = normalizeOriginAllowlist(config.originAllowlist);
          const originValidation = validateOrigin(allowlist);
          if (!originValidation.valid) {
            throw createEmbeddingError("ORIGIN_MISMATCH", originValidation.error || "Origin not allowed");
          }

          // Set up plugin context
          const pluginCtx: PluginContext = {
            appId: config.appId,
            sessionId,
            backendUrl: config.backendUrl,
            locale: typeof navigator !== "undefined" ? navigator.language : "en",
          };
          pluginContextRef.current = pluginCtx;

          brandingRef.current = new BrandingSystem({
            appId: config.appId,
            theme: {
              primaryColor: config.branding?.primaryColor,
              secondaryColor: config.branding?.secondaryColor,
            },
            assets: {
              logo: config.branding?.logoUrl,
            },
            text: {
              headerTitle: config.branding?.headerTitle,
            },
          });
          brandingRef.current.applyToDOM();

          analyticsRef.current = new AnalyticsMiddleware({
            webhookUrl: config.analytics?.webhookUrl,
            webhookSecret: config.analytics?.webhookSecret || config.webhookSecret,
            batchSize: config.analytics?.batchSize,
            batchInterval: config.analytics?.batchInterval,
            debug: config.debug,
          });

          if (config.webhookUrl) {
            webhookRef.current = new WebhookSystem({
              url: config.webhookUrl,
              secret: config.webhookSecret,
              debug: config.debug,
            });
          }

          offlineRef.current = new OfflineManager(sessionId);
          setSyncState(offlineRef.current.getSyncState());
          setPendingSyncCount(offlineRef.current.getPendingSyncCount());
          await registerOfflineSW();

          // Register built-in plugin
          try {
            pluginRegistry.register(slashCommandsPlugin);
          } catch (pluginErr) {
            log("error", "Built-in plugin registration failed", pluginErr);
            emit(
              "error",
              createEmbeddingError("PLUGIN_LOAD_FAILED", "Built-in plugin registration failed", {
                pluginId: slashCommandsPlugin.manifest.id,
              })
            );
          }

          // Register user-provided plugins
          if (config.plugins && config.plugins.length > 0) {
            log("debug", `Registering ${config.plugins.length} user plugins`);
            for (const manifest of config.plugins) {
              const registration = await registerDynamicPlugin({
                manifest,
                hooks: {},
              });
              if (!registration.success) {
                log("warn", `Plugin registration failed: ${manifest.id}`, registration.error);
                emit(
                  "error",
                  createEmbeddingError(
                    "PLUGIN_LOAD_FAILED",
                    registration.error || `Plugin registration failed for ${manifest.id}`,
                    { pluginId: manifest.id }
                  )
                );
              }
            }
          }

          // Initialize all plugins
          await initializePlugins(pluginCtx);

          setIsInitialized(true);
          emit("ready");
          analyticsRef.current?.track({
            eventName: "widget.ready",
            appId: config.appId,
            sessionId,
            timestamp: new Date().toISOString(),
          });
          webhookRef.current?.send(
            createWebhookPayload("widget.ready", config.appId, sessionId, {
              backendUrl: config.backendUrl,
            })
          );
          config.onReady?.(widgetRef.current!);

          log("info", "FloatingAxe widget initialized successfully");
        } catch (err) {
          const embedError = isEmbeddingError(err)
            ? err
            : err instanceof Error
              ? createEmbeddingError("UNKNOWN", err.message)
              : createEmbeddingError("UNKNOWN", "Initialization failed");

          log("error", embedError.message, embedError.details);
          emit("error", embedError);
          config.onError?.(embedError);
        }
      };

      initializeWidget();

      if (typeof window !== "undefined") {
        window.addEventListener("axe-sync-state", handleSyncState);
      }

      // Cleanup on unmount
      return () => {
        if (typeof window !== "undefined") {
          window.removeEventListener("axe-sync-state", handleSyncState);
        }
        destroyPlugins().catch((err) => log("error", "Plugin cleanup failed", err));
        analyticsRef.current?.destroy().catch((err) => log("error", "Analytics cleanup failed", err));
        webhookRef.current?.destroy();
        offlineRef.current?.destroy();
      };
    }, [config, sessionId, log, emit]);

    const replayOfflineQueue = useCallback(async () => {
      if (!offlineRef.current || !offlineRef.current.isOnlineNow()) {
        return;
      }

      await offlineRef.current.replayQueue(async (storedMessage: StoredMessage) => {
        if (storedMessage.role !== "user") {
          return;
        }

        const replayRequest: AxeChatRequest = {
          model: DEFAULT_MODEL,
          messages: [
            {
              role: "user",
              content: storedMessage.content,
            },
          ],
          temperature: 0.7,
        };

        await postAxeChat(replayRequest, {
          "X-App-Id": config.appId,
          "X-Session-Id": sessionId,
        });
      });
    }, [config.appId, sessionId]);

    useEffect(() => {
      const handleReplayTrigger = () => {
        replayOfflineQueue().catch((syncError) => {
          log("warn", "Offline replay failed", syncError);
        });
      };

      if (typeof window !== "undefined") {
        window.addEventListener("axe-sync", handleReplayTrigger);
      }

      return () => {
        if (typeof window !== "undefined") {
          window.removeEventListener("axe-sync", handleReplayTrigger);
        }
      };
    }, [replayOfflineQueue, log]);

    const handleFileSelection = useCallback(
      async (file: File | null) => {
        if (!file) {
          return;
        }
        if (!(offlineRef.current?.isOnlineNow() ?? true)) {
          setError("Attachments require an online connection.");
          return;
        }

        try {
          setIsUploadingAttachment(true);
          setError(null);
          const uploaded = await uploadAxeAttachment(file, {
            "X-App-Id": config.appId,
            "X-Session-Id": sessionId,
          });
          setAttachments((prev) => [
            ...prev,
            {
              id: uploaded.attachment_id,
              filename: uploaded.filename,
              mimeType: uploaded.mime_type,
              sizeBytes: uploaded.size_bytes,
            },
          ]);
        } catch (uploadError) {
          const uploadMessage = uploadError instanceof Error ? uploadError.message : "Attachment upload failed";
          setError(uploadMessage);
          log("error", uploadMessage, uploadError);
        } finally {
          setIsUploadingAttachment(false);
        }
      },
      [config.appId, sessionId, log]
    );

    // Handle sending messages
    const handleSendMessage = useCallback(
      async (content: string) => {
        if (!content.trim() || loading) return;

        try {
          const online = offlineRef.current?.isOnlineNow() ?? true;
          const currentAttachments = attachments;
          setError(null);
          const newMessage: Message = {
            id: `user_${Date.now()}`,
            role: "user",
            content,
            timestamp: new Date(),
          };

          setMessages((prev) => [...prev, newMessage]);
          setInput("");
          offlineRef.current?.saveMessage({
            id: newMessage.id,
            role: newMessage.role,
            content: newMessage.content,
            timestamp: newMessage.timestamp.getTime(),
            synced: online,
          });
          analyticsRef.current?.track({
            eventName: "message.sent",
            appId: config.appId,
            sessionId,
            timestamp: new Date().toISOString(),
            data: { contentLength: content.length },
          });
          webhookRef.current?.send(
            createWebhookPayload("message.sent", config.appId, sessionId, {
              content,
            })
          );

          // Check for slash commands
          if (content.startsWith("/")) {
            const [cmd, ...args] = content.slice(1).split(" ");
            log("debug", "Handling slash command", { cmd, args });

            const commandResult = await pluginRegistry.handleCommand(cmd, args);
            if (typeof commandResult === "string") {
              const commandMessage: Message = {
                id: `assistant_cmd_${Date.now()}`,
                role: "assistant",
                content: commandResult,
                timestamp: new Date(),
              };
              setMessages((prev) => [...prev, commandMessage]);
            }

            return;
          }

          if (!online) {
            setError("Offline: message queued and will sync automatically when connection is restored.");
            emit("message-sent", newMessage);
            return;
          }

          setLoading(true);
          const request: AxeChatRequest = {
            model: DEFAULT_MODEL,
            messages: messages
              .concat(newMessage)
              .map((m) => ({
                role: m.role,
                content: m.content,
              })),
            temperature: 0.7,
            attachments: currentAttachments.map((attachment) => attachment.id),
          };

          if (currentAttachments.length > 0) {
            request.messages[request.messages.length - 1].content = `${request.messages[request.messages.length - 1].content}\n\nAttachments:\n${currentAttachments
              .map((attachment) => `- ${attachment.filename} (${attachment.mimeType}) [${attachment.id}]`)
              .join("\n")}`;
          }

          const response = await postAxeChat(request, {
            "X-App-Id": config.appId,
            "X-Session-Id": sessionId,
          });

          const assistantMessage: Message = {
            id: `assistant_${Date.now()}`,
            role: "assistant",
            content: response.text,
            timestamp: new Date(),
          };

          setMessages((prev) => [...prev, assistantMessage]);
          setAttachments([]);
          offlineRef.current?.saveMessage({
            id: assistantMessage.id,
            role: assistantMessage.role,
            content: assistantMessage.content,
            timestamp: assistantMessage.timestamp.getTime(),
            synced: true,
          });
          analyticsRef.current?.track({
            eventName: "message.received",
            appId: config.appId,
            sessionId,
            timestamp: new Date().toISOString(),
            data: { contentLength: response.text.length },
          });
          webhookRef.current?.send(
            createWebhookPayload("message.received", config.appId, sessionId, {
              contentLength: response.text.length,
            })
          );
          emit("message-received", assistantMessage);
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : "Failed to send message";
          log("error", errorMessage);
          setError(errorMessage);
          webhookRef.current?.send(
            createWebhookPayload("error.occurred", config.appId, sessionId, {
              message: errorMessage,
            })
          );
        } finally {
          setLoading(false);
        }
      },
      [loading, config.appId, sessionId, messages, attachments, log, emit]
    );

    // Auto-scroll to bottom
    useEffect(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    useEffect(() => {
      if (!isInitialized) return;
      if (isOpen) {
        emit("open");
      } else {
        emit("close");
      }
    }, [isOpen, isInitialized, emit]);

    // Auto-resize textarea
    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
      }
    }, [input]);

    // Create widget instance for ref
    useEffect(() => {
      const instance: FloatingAxeInstance = {
        initialize: async () => {
          log("info", "Widget.initialize() called");
        },

        destroy: async () => {
          log("info", "Widget.destroy() called");
          setIsOpen(false);
          await destroyPlugins();
        },

        open: () => {
          setIsOpen(true);
          emit("open");
          analyticsRef.current?.track({
            eventName: "widget.opened",
            appId: config.appId,
            sessionId,
            timestamp: new Date().toISOString(),
          });
          webhookRef.current?.send(createWebhookPayload("widget.opened", config.appId, sessionId));
        },

        close: () => {
          setIsOpen(false);
          emit("close");
          analyticsRef.current?.track({
            eventName: "widget.closed",
            appId: config.appId,
            sessionId,
            timestamp: new Date().toISOString(),
          });
          webhookRef.current?.send(createWebhookPayload("widget.closed", config.appId, sessionId));
        },

        isOpen: () => isOpen,

        registerPlugin: async (manifest, hooks: Partial<Record<PluginHook, PluginHookHandler<unknown, unknown>>> = {}) => {
          log("debug", "registerPlugin() called", { pluginId: manifest.id });
          const result = await registerDynamicPlugin({
            manifest,
            hooks,
          });
          if (!result.success) {
            throw new Error(result.error || `Failed to register plugin ${manifest.id}`);
          }
          emit("plugin-registered", manifest.id);
          webhookRef.current?.send(
            createWebhookPayload("plugin.registered", config.appId, sessionId, {
              pluginId: manifest.id,
            })
          );
        },

        unregisterPlugin: (pluginId) => {
          log("debug", "unregisterPlugin() called", { pluginId });
          const result = unregisterDynamicPlugin(pluginId);
          if (!result.success) {
            log("warn", `Plugin unregistration failed: ${result.error}`);
          }
          emit("plugin-unregistered", pluginId);
          webhookRef.current?.send(
            createWebhookPayload("plugin.unregistered", config.appId, sessionId, {
              pluginId,
            })
          );
        },

        sendMessage: async (content) => {
          await handleSendMessage(content);
          emit("message-sent", content);
        },

        clearChat: () => {
          setMessages([]);
          log("debug", "Chat cleared");
        },

        getSessionId: () => sessionId,

        on,

        emit,
      };

      widgetRef.current = instance;
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      if (forwardedRef) {
        if (typeof forwardedRef === "function") {
          forwardedRef(instance);
        } else {
          forwardedRef.current = instance;
        }
      }
    }, [isOpen, log, on, emit, sessionId, handleSendMessage, forwardedRef, config.appId]);

    if (!isInitialized) {
      return null; // Widget not ready yet
    }

    const positionClasses = {
      "bottom-right": "bottom-4 right-4",
      "bottom-left": "bottom-4 left-4",
      "top-right": "top-4 right-4",
      "top-left": "top-4 left-4",
    };

    const position = config.position || "bottom-right";
    const theme = config.theme || "light";
    const headerTitle = config.branding?.headerTitle || "AXE Chat";
    const logoUrl = config.branding?.logoUrl;
    const uploadEnabled = config.features?.enableUpload === true;
    const cameraEnabled = config.features?.enableCamera === true;
    const canvasEnabled = config.features?.enableCanvas === true;
    const buttonStyle = config.branding?.primaryColor
      ? { background: `linear-gradient(135deg, ${config.branding.primaryColor}, ${config.branding.secondaryColor || config.branding.primaryColor})` }
      : undefined;
    const syncBadge = {
      offline: { label: "offline", className: "bg-amber-100 text-amber-700" },
      retrying: {
        label: `retrying${pendingSyncCount > 0 ? ` (${pendingSyncCount})` : ""}`,
        className: "bg-blue-100 text-blue-700",
      },
      synced: { label: "synced", className: "bg-emerald-100 text-emerald-700" },
    }[syncState];

    return (
      <div className={`fixed ${positionClasses[position]} z-50 font-sans`}>
        {/* Floating Button */}
        {!isOpen && (
          <button
            onClick={() => setIsOpen(true)}
            className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg hover:shadow-xl transition-shadow flex items-center justify-center"
            style={buttonStyle}
            aria-label="Open AXE chat"
            title="Chat with AXE"
          >
            {logoUrl ? (
              <span
                aria-label="AXE"
                className="h-6 w-6 rounded-full bg-cover bg-center"
                style={{ backgroundImage: `url(${logoUrl})` }}
              />
            ) : (
              <MessageCircle size={24} />
            )}
          </button>
        )}

        {/* Chat Panel */}
        {isOpen && (
          <div
            className={`flex flex-col w-80 h-96 rounded-lg shadow-2xl overflow-hidden ${
              theme === "dark" ? "bg-gray-900 text-white" : "bg-white text-gray-900"
            }`}
          >
            {/* Header */}
            <div className={`flex items-center justify-between p-4 ${
              theme === "dark" ? "bg-gray-800 border-gray-700" : "bg-blue-50 border-blue-100"
            } border-b`}>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-sm">{headerTitle}</h2>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${syncBadge.className}`}>
                  {syncBadge.label}
                </span>
              </div>
              <div className="flex gap-2">
                {canvasEnabled && (
                  <button
                    onClick={() => setIsCanvasOpen((prev) => !prev)}
                    className={`p-1 rounded hover:opacity-70 transition-opacity ${
                      theme === "dark" ? "hover:bg-gray-700" : "hover:bg-blue-100"
                    }`}
                    aria-label="Toggle canvas"
                    title="Toggle Canvas"
                  >
                    <Maximize2 size={16} />
                  </button>
                )}
                <button
                  onClick={() => setIsOpen(false)}
                  className={`p-1 rounded hover:opacity-70 transition-opacity ${
                    theme === "dark" ? "hover:bg-gray-700" : "hover:bg-blue-100"
                  }`}
                  aria-label="Minimize chat"
                >
                  <Minimize2 size={16} />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className={`p-1 rounded hover:opacity-70 transition-opacity ${
                    theme === "dark" ? "hover:bg-gray-700" : "hover:bg-blue-100"
                  }`}
                  aria-label="Close chat"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.length === 0 && (
                <div className={`text-center text-sm ${theme === "dark" ? "text-gray-400" : "text-gray-500"}`}>
                  <p>Start a conversation with AXE</p>
                </div>
              )}
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-xs px-3 py-2 rounded-lg text-sm ${
                      msg.role === "user"
                        ? `${
                            theme === "dark"
                              ? "bg-blue-600 text-white"
                              : "bg-blue-500 text-white"
                          }`
                        : `${
                            theme === "dark"
                              ? "bg-gray-700 text-gray-100"
                              : "bg-gray-100 text-gray-900"
                          }`
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className={`px-3 py-2 rounded-lg text-sm ${
                    theme === "dark" ? "bg-gray-700 text-gray-100" : "bg-gray-100 text-gray-900"
                  }`}>
                    <div className="flex gap-1">
                      <div className="w-2 h-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "0ms" }} />
                      <div className="w-2 h-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "150ms" }} />
                      <div className="w-2 h-2 rounded-full bg-current animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {canvasEnabled && isCanvasOpen && (
              <div
                data-testid="axe-canvas-panel"
                className={`h-56 border-t ${theme === "dark" ? "border-gray-700" : "border-gray-200"}`}
              >
                <CodeEditor
                  language="typescript"
                  value={editorValue}
                  onChange={setEditorValue}
                  theme={theme === "dark" ? "vs-dark" : "light"}
                  height="100%"
                />
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="px-4 py-2 bg-red-50 border-t border-red-200 text-red-700 text-xs">
                {error}
              </div>
            )}

            {/* Input Area */}
            <div className={`flex gap-2 p-3 ${
              theme === "dark" ? "bg-gray-800 border-gray-700" : "bg-gray-50 border-gray-200"
            } border-t`}>
              {(uploadEnabled || cameraEnabled) && (
                <div className="flex flex-col gap-2">
                  <div className="flex gap-1">
                    {uploadEnabled && (
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploadingAttachment || loading}
                        className="w-8 h-8 rounded bg-gray-200 text-gray-700 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                        aria-label="Attach file"
                        title="Attach file"
                      >
                        <Paperclip size={14} />
                      </button>
                    )}
                    {cameraEnabled && (
                      <button
                        onClick={() => cameraInputRef.current?.click()}
                        disabled={isUploadingAttachment || loading}
                        className="w-8 h-8 rounded bg-gray-200 text-gray-700 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                        aria-label="Take photo"
                        title="Take photo"
                      >
                        <Camera size={14} />
                      </button>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={(event) => {
                      const file = event.target.files?.[0] || null;
                      handleFileSelection(file).finally(() => {
                        event.target.value = "";
                      });
                    }}
                  />
                  <input
                    ref={cameraInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(event) => {
                      const file = event.target.files?.[0] || null;
                      handleFileSelection(file).finally(() => {
                        event.target.value = "";
                      });
                    }}
                  />
                </div>
              )}
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(input);
                  }
                }}
                placeholder="Type a message..."
                disabled={loading}
                rows={1}
                className={`flex-1 px-3 py-2 rounded border text-sm outline-none resize-none ${
                  theme === "dark"
                    ? "bg-gray-700 border-gray-600 text-white placeholder-gray-400"
                    : "bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                } disabled:opacity-50`}
              />
              <button
                onClick={() => handleSendMessage(input)}
                disabled={loading || !input.trim() || isUploadingAttachment}
                className="w-8 h-8 rounded bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
                aria-label="Send message"
              >
                <Send size={16} />
              </button>
            </div>
            {attachments.length > 0 && (
              <div className={`px-3 pb-3 ${theme === "dark" ? "bg-gray-800" : "bg-gray-50"}`}>
                <div className="flex flex-wrap gap-1">
                  {attachments.map((attachment) => (
                    <button
                      key={attachment.id}
                      onClick={() => setAttachments((prev) => prev.filter((item) => item.id !== attachment.id))}
                      className="rounded-full px-2 py-1 text-[11px] bg-blue-100 text-blue-700 hover:bg-blue-200"
                      title="Remove attachment"
                    >
                      {attachment.filename}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
);

FloatingAxe.displayName = "FloatingAxe";

export default FloatingAxe;
