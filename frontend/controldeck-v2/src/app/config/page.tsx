"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@ui-core/components/card";
import { Button } from "@ui-core/components/button";
import { Badge } from "@ui-core/components/badge";
import { Input, Label } from "@ui-core/components/input";
import { Switch } from "@ui-core/components/switch";
import { Alert, AlertDescription } from "@ui-core/components/alert";
import {
  Dialog,
  
  
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@ui-core/components/dialog";
import { 
  Cpu,
  Plus,
  Save,
  Trash2,
  RefreshCw,
  CheckCircle,
  Lock,
  Globe,
  Database,
  Key,
  FileJson,
  Type,
  Hash,
  ToggleLeft
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de";

interface ConfigEntry {
  id: string;
  key: string;
  value: any;
  type: string;
  environment: string;
  is_secret: boolean;
  description?: string;
  version: number;
}

export default function ConfigPage() {
  const [configs, setConfigs] = useState<ConfigEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ConfigEntry | null>(null);
  const [message, setMessage] = useState("");
  const [filter, setFilter] = useState("");
  const [newConfig, setNewConfig] = useState({
    key: "",
    value: "",
    type: "string",
    environment: "default",
    is_secret: false,
    description: "",
  });

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config`);
      if (res.ok) {
        const data = await res.json();
        setConfigs(data.items || []);
      }
    } catch (e) {
      console.error("Failed to fetch configs");
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      let parsedValue: any = newConfig.value;
      if (newConfig.type === "json") {
        parsedValue = JSON.parse(newConfig.value);
      } else if (newConfig.type === "number") {
        parsedValue = Number(newConfig.value);
      } else if (newConfig.type === "boolean") {
        parsedValue = newConfig.value === "true";
      }

      const res = await fetch(`${API_BASE}/api/config/${newConfig.key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...newConfig,
          value: parsedValue,
        }),
      });
      
      if (res.ok) {
        setShowDialog(false);
        setNewConfig({ key: "", value: "", type: "string", environment: "default", is_secret: false, description: "" });
        fetchConfigs();
        setMessage("Config saved!");
        setTimeout(() => setMessage(""), 3000);
      }
    } catch (e) {
      setMessage("Failed to save config");
    }
  };

  const deleteConfig = async (key: string) => {
    if (!confirm(`Delete config "${key}"?`)) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/config/${key}`, {
        method: "DELETE",
      });
      
      if (res.ok) {
        fetchConfigs();
        setMessage("Config deleted");
        setTimeout(() => setMessage(""), 3000);
      }
    } catch (e) {
      setMessage("Failed to delete config");
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "string":
        return <Type className="h-4 w-4" />;
      case "number":
        return <Hash className="h-4 w-4" />;
      case "boolean":
        return <ToggleLeft className="h-4 w-4" />;
      case "json":
        return <FileJson className="h-4 w-4" />;
      default:
        return <Database className="h-4 w-4" />;
    }
  };

  const filteredConfigs = configs.filter(c => 
    c.key.toLowerCase().includes(filter.toLowerCase()) ||
    c.description?.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <DashboardLayout title="Configuration" subtitle="Manage system configuration">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Configs</p>
                  <p className="text-2xl font-bold">{configs.length}</p>
                </div>
                <Database className="h-8 w-8 text-primary" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Secrets</p>
                  <p className="text-2xl font-bold text-orange-500">
                    {configs.filter(c => c.is_secret).length}
                  </p>
                </div>
                <Lock className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Environments</p>
                  <p className="text-2xl font-bold text-blue-500">
                    {new Set(configs.map(c => c.environment)).size}
                  </p>
                </div>
                <Globe className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">JSON Configs</p>
                  <p className="text-2xl font-bold text-green-500">
                    {configs.filter(c => c.type === "json").length}
                  </p>
                </div>
                <FileJson className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Actions */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Input
              placeholder="Filter configs..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-64"
            />
            {message && (
              <Alert className="bg-green-500/10 border-green-500/20 w-fit">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <AlertDescription className="text-green-700">{message}</AlertDescription>
              </Alert>
            )}
          </div>
          <Button onClick={() => setShowDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Config
          </Button>
        </div>

        {/* Configs Grid */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              Configuration Entries
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : filteredConfigs.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No configuration entries</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredConfigs.map((config) => (
                  <Card key={config.id} className="border-l-4 border-l-primary">
                    <CardContent className="pt-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          {getTypeIcon(config.type)}
                          <span className="font-mono text-sm">{config.key}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {config.is_secret && (
                            <Badge variant="outline" className="bg-orange-500/10 text-orange-500">
                              <Lock className="h-3 w-3 mr-1" />
                              Secret
                            </Badge>
                          )}
                          <Badge variant="muted" className="text-xs">
                            v{config.version}
                          </Badge>
                        </div>
                      </div>

                      <div className="mt-3">
                        <div className="p-2 bg-muted rounded-md font-mono text-xs overflow-hidden">
                          {config.is_secret ? (
                            <span className="text-muted-foreground">••••••••</span>
                          ) : (
                            <span className="truncate">
                              {typeof config.value === "object" 
                                ? JSON.stringify(config.value).slice(0, 50) + "..."
                                : String(config.value).slice(0, 50)
                              }
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                        <div className="flex items-center gap-2">
                          <Globe className="h-3 w-3" />
                          <span>{config.environment}</span>
                          <span className="capitalize">({config.type})</span>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setEditingConfig(config);
                              setNewConfig({
                                key: config.key,
                                value: typeof config.value === "object" 
                                  ? JSON.stringify(config.value, null, 2)
                                  : String(config.value),
                                type: config.type,
                                environment: config.environment,
                                is_secret: config.is_secret,
                                description: config.description || "",
                              });
                              setShowDialog(true);
                            }}
                          >
                            <Key className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive"
                            onClick={() => deleteConfig(config.key)}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Add/Edit Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          
            <DialogHeader>
              <DialogTitle>{editingConfig ? "Edit Config" : "Add Config"}</DialogTitle>
              <DialogDescription>
                {editingConfig ? "Update configuration value" : "Create new configuration entry"}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Key</Label>
                <Input
                  value={newConfig.key}
                  onChange={(e) => setNewConfig({...newConfig, key: e.target.value})}
                  placeholder="config.key.name"
                  disabled={!!editingConfig}
                />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <select
                  value={newConfig.type}
                  onChange={(e) => setNewConfig({...newConfig, type: e.target.value})}
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                >
                  <option value="string">String</option>
                  <option value="number">Number</option>
                  <option value="boolean">Boolean</option>
                  <option value="json">JSON</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Value</Label>
                <textarea
                  value={newConfig.value}
                  onChange={(e) => setNewConfig({...newConfig, value: e.target.value})}
                  className="w-full h-24 p-2 rounded-md border border-input bg-background font-mono text-sm"
                  placeholder={newConfig.type === "json" ? '{"key": "value"}' : "Enter value..."}
                />
              </div>
              <div className="space-y-2">
                <Label>Environment</Label>
                <Input
                  value={newConfig.environment}
                  onChange={(e) => setNewConfig({...newConfig, environment: e.target.value})}
                  placeholder="default, prod, staging..."
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  value={newConfig.description}
                  onChange={(e) => setNewConfig({...newConfig, description: e.target.value})}
                  placeholder="What is this config for?"
                />
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={newConfig.is_secret}
                  onCheckedChange={(checked) => setNewConfig({...newConfig, is_secret: checked})}
                />
                <Label>Secret (value will be hidden)</Label>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => {
                setShowDialog(false);
                setEditingConfig(null);
              }}>Cancel</Button>
              <Button onClick={saveConfig}>
                <Save className="h-4 w-4 mr-2" />
                Save
              </Button>
            </DialogFooter>
          
        </Dialog>
      </div>
    </DashboardLayout>
  );
}
