"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Copy, Check, Code, ExternalLink } from "lucide-react";

export default function AxeWidgetPage() {
  const router = useRouter();
  const [copied, setCopied] = useState(false);
  const [config, setConfig] = useState({
    projectId: "my-project",
    position: "bottom-right",
    theme: "dark",
    primaryColor: "#3b82f6",
    greeting: "👋 Hi! I'm AXE. How can I help you?",
  });

  const embedCode = `<script src="${typeof window !== 'undefined' ? window.location.origin : ''}/widget/axe.js"></script>
<script>
  AxeWidget.init({
    projectId: "${config.projectId}",
    apiKey: "YOUR_API_KEY",
    position: "${config.position}",
    theme: "${config.theme}",
    primaryColor: "${config.primaryColor}",
    greeting: "${config.greeting}"
  });
</script>`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="outline" size="icon" onClick={() => router.push("/dashboard")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AXE Widget</h1>
          <p className="text-sm text-muted-foreground">
            Floating chat widget for your web projects
          </p>
        </div>
      </div>

      <Tabs defaultValue="setup" className="space-y-4">
        <TabsList>
          <TabsTrigger value="setup">Setup</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="setup" className="space-y-4">
          {/* Embed Code Card */}
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                Embed Code
              </CardTitle>
              <CardDescription>
                Add this code to any website to embed the AXE widget
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative">
                <pre className="bg-muted p-4 rounded-lg text-sm overflow-x-auto">
                  <code>{embedCode}</code>
                </pre>
                <Button
                  size="sm"
                  variant="secondary"
                  className="absolute top-2 right-2"
                  onClick={copyToClipboard}
                >
                  {copied ? (
                    <Check className="h-4 w-4 mr-2" />
                  ) : (
                    <Copy className="h-4 w-4 mr-2" />
                  )}
                  {copied ? "Copied!" : "Copy"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Configuration */}
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Project ID</Label>
                  <Input
                    value={config.projectId}
                    onChange={(e) => setConfig({ ...config, projectId: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Position</Label>
                  <select
                    className="w-full h-10 px-3 rounded-md border border-input bg-background"
                    value={config.position}
                    onChange={(e) => setConfig({ ...config, position: e.target.value })}
                  >
                    <option value="bottom-right">Bottom Right</option>
                    <option value="bottom-left">Bottom Left</option>
                    <option value="top-right">Top Right</option>
                    <option value="top-left">Top Left</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label>Theme</Label>
                  <select
                    className="w-full h-10 px-3 rounded-md border border-input bg-background"
                    value={config.theme}
                    onChange={(e) => setConfig({ ...config, theme: e.target.value })}
                  >
                    <option value="dark">Dark</option>
                    <option value="light">Light</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label>Primary Color</Label>
                  <div className="flex gap-2">
                    <Input
                      type="color"
                      value={config.primaryColor}
                      onChange={(e) => setConfig({ ...config, primaryColor: e.target.value })}
                      className="w-16"
                    />
                    <Input
                      value={config.primaryColor}
                      onChange={(e) => setConfig({ ...config, primaryColor: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Greeting Message</Label>
                <Input
                  value={config.greeting}
                  onChange={(e) => setConfig({ ...config, greeting: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preview">
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Live Preview</CardTitle>
              <CardDescription>
                This is how the widget will appear on your website
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="relative h-96 bg-muted rounded-lg overflow-hidden">
                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                  <p>Website content would appear here</p>
                </div>
                
                {/* Mock Widget */}
                <div 
                  className="absolute bottom-4 right-4"
                  style={{ 
                    position: 'absolute',
                    [config.position.includes('bottom') ? 'bottom' : 'top']: '20px',
                    [config.position.includes('right') ? 'right' : 'left']: '20px'
                  }}
                >
                  <div 
                    className="w-14 h-14 rounded-full flex items-center justify-center text-white shadow-lg cursor-pointer"
                    style={{ backgroundColor: config.primaryColor }}
                  >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          <Card className="border-border/50">
            <CardHeader>
              <CardTitle>Widget Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">0</div>
                  <p className="text-xs text-muted-foreground">Active Sessions</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">0</div>
                  <p className="text-xs text-muted-foreground">Total Messages</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">0</div>
                  <p className="text-xs text-muted-foreground">Issues Reported</p>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">0</div>
                  <p className="text-xs text-muted-foreground">Avg Response Time</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Documentation */}
      <Card className="border-border/50 bg-secondary/30">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Documentation</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            The AXE Widget provides a floating chat interface that can be embedded in any website.
            It connects to BRAiN's AXE Core for intelligent responses and can escalate to human support.
          </p>
          <ul className="list-disc list-inside space-y-1">
            <li>Customizable position, colors, and greeting</li>
            <li>Automatic session management</li>
            <li>Message history and context preservation</li>
            <li>Seamless integration with BRAiN's ticket system</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
