"use client";

import { useState, useEffect } from "react";

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

// Format time safely (avoids hydration mismatch)
function formatTime(date: Date): string {
  if (typeof window === 'undefined') return '';
  return date.toLocaleTimeString();
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    // Initialize first message on client only (avoids hydration mismatch)
    setMessages([
      {
        id: 1,
        role: "assistant",
        content: "Hello! I'm the AXE (Auxiliary Execution Engine) agent. I can help you execute commands, analyze logs, and monitor system status. How can I assist you today?",
        timestamp: new Date(),
      },
    ]);
  }, []);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: messages.length + 1,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/axe/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage.content }),
      });

      const data = await response.json();

      const assistantMessage: Message = {
        id: messages.length + 2,
        role: "assistant",
        content: data.response || "I received your message.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: messages.length + 2,
        role: "assistant",
        content: "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">AXE Chat</h1>
        <p className="text-slate-400 mt-2">
          Conversational interface with the Auxiliary Execution Engine
        </p>
      </div>

      {/* Chat Container */}
      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg flex flex-col overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-800 text-slate-100 border border-slate-700"
                }`}
              >
                <div className="flex items-start gap-3">
                  {message.role === "assistant" && (
                    <span className="text-2xl">🤖</span>
                  )}
                  <div className="flex-1">
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <p className="text-xs opacity-70 mt-2" suppressHydrationWarning>
                      {isClient ? formatTime(message.timestamp) : ''}
                    </p>
                  </div>
                </div>
              </div>
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
        </div>

        {/* Input */}
        <div className="border-t border-slate-800 p-4">
          <div className="flex gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={loading}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
            >
              {loading ? "Sending..." : "Send"}
            </button>
          </div>
        </div>
      </div>

      {/* Quick Commands */}
      <div className="mt-4 p-4 bg-slate-900 border border-slate-800 rounded-lg">
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
    </div>
  );
}
