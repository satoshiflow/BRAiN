"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAXE, type ChatRequest } from "@/hooks/useAgents";
import { MessageSquare, Trash2, Activity, Send, User, Bot } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export function AXEChatInterface() {
  const { chat, getSystemStatus, clearHistory, isChatting } = useAXE();

  const [message, setMessage] = useState("");
  const [chatHistory, setChatHistory] = useState<Message[]>([]);

  const systemStatus = getSystemStatus.data;

  const handleSendMessage = () => {
    if (!message.trim()) return;

    // Add user message to history
    const userMessage: Message = {
      role: "user",
      content: message,
      timestamp: new Date(),
    };
    setChatHistory((prev) => [...prev, userMessage]);

    // Send to backend
    const request: ChatRequest = {
      message,
      include_history: true,
    };

    chat.mutate(request, {
      onSuccess: (data) => {
        // Add assistant response to history
        const assistantMessage: Message = {
          role: "assistant",
          content: data?.response || JSON.stringify(data),
          timestamp: new Date(),
        };
        setChatHistory((prev) => [...prev, assistantMessage]);
      },
    });

    // Clear input
    setMessage("");
  };

  const handleClearHistory = () => {
    clearHistory.mutate(undefined, {
      onSuccess: () => {
        setChatHistory([]);
      },
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="brain-card border-green-500/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-green-500/10">
              <MessageSquare className="w-6 h-6 text-green-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg mb-2">AXE - Auxiliary Execution Engine</h3>
              <p className="text-sm text-muted-foreground">
                Conversational AI assistant for system monitoring, log analysis, and safe command execution.
                Context-aware with conversation history.
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                <Badge variant="outline" className="text-xs">
                  <Activity className="w-3 h-3 mr-1" />
                  System Status: {systemStatus?.status || "Unknown"}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  <MessageSquare className="w-3 h-3 mr-1" />
                  Conversational AI
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Status */}
      {systemStatus && (
        <Card className="brain-card">
          <CardHeader className="brain-card-header">
            <CardTitle className="brain-card-title">System Status</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto">
              {JSON.stringify(systemStatus, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Chat Interface */}
      <Card className="brain-card">
        <CardHeader className="brain-card-header">
          <div className="flex items-center justify-between">
            <CardTitle className="brain-card-title">Chat</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearHistory}
              disabled={chatHistory.length === 0}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear History
            </Button>
          </div>
          <CardDescription>
            Ask AXE about system status, logs, or request safe operations
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Chat History */}
          <ScrollArea className="h-[400px] w-full rounded-lg border border-white/5 bg-black/20 p-4">
            {chatHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
                <MessageSquare className="w-12 h-12 mb-4 opacity-20" />
                <p className="text-sm">No messages yet</p>
                <p className="text-xs mt-1">Start a conversation with AXE</p>
              </div>
            ) : (
              <div className="space-y-4">
                {chatHistory.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex items-start gap-3 ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {msg.role === "assistant" && (
                      <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                        <Bot className="w-4 h-4 text-green-500" />
                      </div>
                    )}
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                        msg.role === "user"
                          ? "bg-brain-gold/20 text-white"
                          : "bg-white/5 text-slate-200"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      <p className="text-[0.65rem] text-muted-foreground mt-2">
                        {msg.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                    {msg.role === "user" && (
                      <div className="w-8 h-8 rounded-full bg-brain-gold/20 flex items-center justify-center">
                        <User className="w-4 h-4 text-brain-gold" />
                      </div>
                    )}
                  </div>
                ))}

                {/* Loading indicator */}
                {isChatting && (
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-green-500 animate-pulse" />
                    </div>
                    <div className="bg-white/5 rounded-2xl px-4 py-3">
                      <p className="text-sm text-muted-foreground">AXE is thinking...</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </ScrollArea>

          {/* Error Display */}
          {chat.error && (
            <Alert className="border-red-500/50">
              <AlertDescription>
                <p className="text-red-500 font-semibold">Error</p>
                <p className="text-sm">{chat.error.message}</p>
              </AlertDescription>
            </Alert>
          )}

          {/* Input Area */}
          <div className="space-y-2">
            <Label htmlFor="message">Message</Label>
            <div className="flex gap-2">
              <Textarea
                id="message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                rows={3}
                disabled={isChatting}
              />
              <Button
                onClick={handleSendMessage}
                disabled={isChatting || !message.trim()}
                size="icon"
                className="h-auto"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Example queries: "What's the system status?", "Show me recent errors", "Check agent health"
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Capabilities Info */}
      <Card className="brain-card">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title">AXE Capabilities</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 text-sm">
            <div className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <div>
                <p className="font-semibold">System Monitoring</p>
                <p className="text-xs text-muted-foreground">
                  Query agent status, mission queue, resource usage
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <div>
                <p className="font-semibold">Log Analysis</p>
                <p className="text-xs text-muted-foreground">
                  Search logs, identify errors, analyze patterns
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <div>
                <p className="font-semibold">Safe Command Execution</p>
                <p className="text-xs text-muted-foreground">
                  Execute read-only commands, supervisor-approved operations
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <div>
                <p className="font-semibold">Conversation History</p>
                <p className="text-xs text-muted-foreground">
                  Context-aware responses based on chat history
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
