"use client";

import { useMemo, useRef, useState } from "react";
import { CodeEditor } from "@/src/components/CodeEditor";
import { AttachmentTray } from "@/src/components/chat/AttachmentTray";
import { AdvancedCameraCapture } from "@/src/components/chat/AdvancedCameraCapture";
import { ChatComposer } from "@/src/components/chat/ChatComposer";
import { MessageList, type ChatMessageItem } from "@/src/components/chat/MessageList";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/src/components/ui/resizable";
import { sendAxeChat } from "@/lib/api";
import { useAttachmentUpload } from "@/src/hooks/useAttachmentUpload";

type WorkspaceTab = "canvas" | "editor";

const AXE_MODEL = "qwen2.5:0.5b";

const quickCommands = [
  "Check system status",
  "List active agents",
  "Show recent logs",
  "Get mission queue",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessageItem[]>([
    {
      id: "assistant-init",
      role: "assistant",
      content:
        "Hello! I'm the AXE agent. You can upload files, capture photos, and work side-by-side with canvas/editor in split mode.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("canvas");
  const [cameraOpen, setCameraOpen] = useState(false);
  const [code, setCode] = useState("// AXE editor\n\nexport function run() {\n  return 'ready';\n}\n");

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawingRef = useRef(false);

  const {
    attachments,
    addFiles,
    removeAttachment,
    readyAttachmentIds,
    clearAttachments,
    isUploading,
  } = useAttachmentUpload();

  const canSend = useMemo(
    () => input.trim().length > 0 && !loading && !isUploading,
    [input, loading, isUploading]
  );

  const handleSend = async () => {
    if (!canSend) return;

    const userMessage: ChatMessageItem = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendAxeChat({
        model: AXE_MODEL,
        messages: [{ role: "user", content: userMessage.content }],
        temperature: 0.7,
        attachments: readyAttachmentIds.length > 0 ? readyAttachmentIds : undefined,
      });

      const assistantMessage: ChatMessageItem = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.text || "I received your message.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      clearAttachments();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Sorry, I encountered an error processing your request.";
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: `Request failed: ${message}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleStartDrawing = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    drawingRef.current = true;
    const rect = canvas.getBoundingClientRect();
    const context = canvas.getContext("2d");
    if (!context) return;
    context.lineWidth = 2;
    context.lineCap = "round";
    context.strokeStyle = "#38bdf8";
    context.beginPath();
    context.moveTo(event.clientX - rect.left, event.clientY - rect.top);
  };

  const handleDraw = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawingRef.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const context = canvas.getContext("2d");
    if (!context) return;
    context.lineTo(event.clientX - rect.left, event.clientY - rect.top);
    context.stroke();
  };

  const handleStopDrawing = () => {
    drawingRef.current = false;
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">AXE Chat</h1>
        <p className="text-slate-400 mt-2">
          Split workspace with upload, camera capture, canvas, and editor.
        </p>
      </div>

      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel defaultSize={48} minSize={35}>
            <div className="h-full flex flex-col">
              <MessageList messages={messages} loading={loading} />
              <AttachmentTray attachments={attachments} onRemove={removeAttachment} />
              <ChatComposer
                value={input}
                loading={loading}
                uploading={isUploading}
                onChange={setInput}
                onSend={() => void handleSend()}
                onFilesSelected={addFiles}
                onOpenCamera={() => setCameraOpen(true)}
              />
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel defaultSize={52} minSize={35}>
            <div className="h-full flex flex-col bg-slate-950">
              <div className="border-b border-slate-800 px-4 py-3 flex items-center justify-between">
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setWorkspaceTab("canvas")}
                    className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${
                      workspaceTab === "canvas"
                        ? "bg-blue-600 text-white border-blue-500"
                        : "bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800"
                    }`}
                  >
                    Canvas
                  </button>
                  <button
                    type="button"
                    onClick={() => setWorkspaceTab("editor")}
                    className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${
                      workspaceTab === "editor"
                        ? "bg-blue-600 text-white border-blue-500"
                        : "bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800"
                    }`}
                  >
                    Editor
                  </button>
                </div>
                {workspaceTab === "canvas" && (
                  <button
                    type="button"
                    onClick={clearCanvas}
                    className="px-3 py-1.5 rounded-md text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                  >
                    Clear canvas
                  </button>
                )}
              </div>

              <div className="flex-1 p-4">
                {workspaceTab === "canvas" ? (
                  <div className="h-full rounded-lg border border-slate-700 bg-slate-900 p-2">
                    <canvas
                      ref={canvasRef}
                      width={1200}
                      height={800}
                      onPointerDown={handleStartDrawing}
                      onPointerMove={handleDraw}
                      onPointerUp={handleStopDrawing}
                      onPointerLeave={handleStopDrawing}
                      className="w-full h-full rounded bg-slate-950 touch-none"
                    />
                  </div>
                ) : (
                  <div className="h-full rounded-lg overflow-hidden border border-slate-700">
                    <CodeEditor language="typescript" value={code} onChange={setCode} theme="vs-dark" />
                  </div>
                )}
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      <div className="mt-4 p-4 bg-slate-900 border border-slate-800 rounded-lg">
        <p className="text-sm text-slate-400 mb-2">Quick commands:</p>
        <div className="flex flex-wrap gap-2">
          {quickCommands.map((cmd) => (
            <button
              key={cmd}
              onClick={() => setInput(cmd)}
              className="px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
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
          await addFiles([file]);
        }}
      />
    </div>
  );
}
