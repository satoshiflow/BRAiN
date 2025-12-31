"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCoder, type RiskLevel, type CodeGenerationRequest, type OdooModuleRequest } from "@/hooks/useAgents";
import { Code, FileCode, Shield, CheckCircle2, AlertTriangle } from "lucide-react";

export function CoderInterface() {
  const { generateCode, generateOdooModule, isGenerating } = useCoder();

  // Code Generation State
  const [codeSpec, setCodeSpec] = useState("");
  const [codeRiskLevel, setCodeRiskLevel] = useState<RiskLevel>("low");

  // Odoo Module State
  const [moduleName, setModuleName] = useState("");
  const [modulePurpose, setModulePurpose] = useState("");
  const [dataTypes, setDataTypes] = useState("");
  const [models, setModels] = useState("");
  const [views, setViews] = useState("");

  const handleGenerateCode = () => {
    const request: CodeGenerationRequest = {
      spec: codeSpec,
      risk_level: codeRiskLevel,
    };
    generateCode.mutate(request);
  };

  const handleGenerateOdooModule = () => {
    const request: OdooModuleRequest = {
      name: moduleName,
      purpose: modulePurpose,
      data_types: dataTypes.split(",").map((s) => s.trim()).filter(Boolean),
      models: models.split(",").map((s) => s.trim()).filter(Boolean),
      views: views.split(",").map((s) => s.trim()).filter(Boolean),
    };
    generateOdooModule.mutate(request);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="brain-card border-purple-500/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-purple-500/10">
              <Code className="w-6 h-6 text-purple-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg mb-2">DSGVO-Compliant Code Generation</h3>
              <p className="text-sm text-muted-foreground">
                CoderAgent generates secure code with automatic DSGVO compliance checks.
                High-risk code (personal data handling) requires supervisor approval.
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                <Badge variant="outline" className="text-xs">
                  <Shield className="w-3 h-3 mr-1" />
                  Privacy by Design (Art. 25)
                </Badge>
                <Badge variant="outline" className="text-xs">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Code Validation
                </Badge>
                <Badge variant="outline" className="text-xs">
                  <FileCode className="w-3 h-3 mr-1" />
                  Odoo Modules
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs defaultValue="code" className="space-y-4">
        <TabsList className="bg-brain-panel border border-white/5">
          <TabsTrigger value="code" className="data-[state=active]:bg-brain-accent">
            <Code className="w-4 h-4 mr-2" />
            Generate Code
          </TabsTrigger>
          <TabsTrigger value="odoo" className="data-[state=active]:bg-brain-accent">
            <FileCode className="w-4 h-4 mr-2" />
            Odoo Module
          </TabsTrigger>
        </TabsList>

        {/* Code Generation Tab */}
        <TabsContent value="code">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <CardTitle className="brain-card-title">Code Generation</CardTitle>
              <CardDescription>
                Generate code from specifications with automatic validation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="codeSpec">Code Specification</Label>
                <Textarea
                  id="codeSpec"
                  value={codeSpec}
                  onChange={(e) => setCodeSpec(e.target.value)}
                  placeholder="Describe the code you want to generate...&#10;&#10;Example:&#10;Create a Python function that validates email addresses and checks if they're from allowed domains. The function should return a boolean."
                  rows={8}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="codeRisk">Risk Level</Label>
                <Select value={codeRiskLevel} onValueChange={(v) => setCodeRiskLevel(v as RiskLevel)}>
                  <SelectTrigger id="codeRisk">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">LOW - Utility functions, no personal data</SelectItem>
                    <SelectItem value="medium">MEDIUM - Business logic</SelectItem>
                    <SelectItem value="high">HIGH - Personal data processing</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  HIGH risk code requires supervisor approval before generation
                </p>
              </div>

              <Button
                onClick={handleGenerateCode}
                disabled={isGenerating || !codeSpec}
                className="w-full"
              >
                {isGenerating ? "Generating..." : "Generate Code"}
              </Button>

              {generateCode.data && (
                <Alert className="border-green-500/50">
                  <AlertDescription className="space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-green-500">
                      <CheckCircle2 className="w-4 h-4" />
                      Code Generated Successfully
                    </div>
                    <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto mt-2">
                      {JSON.stringify(generateCode.data, null, 2)}
                    </pre>
                  </AlertDescription>
                </Alert>
              )}

              {generateCode.error && (
                <Alert className="border-red-500/50">
                  <AlertDescription>
                    <p className="text-red-500 font-semibold">Error</p>
                    <p className="text-sm">{generateCode.error.message}</p>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Odoo Module Tab */}
        <TabsContent value="odoo">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <CardTitle className="brain-card-title">Generate Odoo Module</CardTitle>
              <CardDescription>
                Create DSGVO-compliant Odoo modules with automatic risk assessment
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert className="border-purple-500/50">
                <AlertDescription className="text-xs">
                  <p className="font-semibold mb-1">Automatic Risk Assessment</p>
                  <p>
                    Modules handling personal data (names, emails, addresses) are automatically
                    classified as HIGH risk and require supervisor approval.
                  </p>
                </AlertDescription>
              </Alert>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="moduleName">Module Name</Label>
                  <Input
                    id="moduleName"
                    value={moduleName}
                    onChange={(e) => setModuleName(e.target.value)}
                    placeholder="e.g., customer_portal"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="modulePurpose">Purpose</Label>
                  <Input
                    id="modulePurpose"
                    value={modulePurpose}
                    onChange={(e) => setModulePurpose(e.target.value)}
                    placeholder="e.g., Customer self-service portal"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dataTypes">Data Types (comma-separated)</Label>
                <Input
                  id="dataTypes"
                  value={dataTypes}
                  onChange={(e) => setDataTypes(e.target.value)}
                  placeholder="e.g., name, email, phone, address"
                />
                <p className="text-xs text-muted-foreground">
                  ⚠️ Personal data types will trigger HIGH risk assessment
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="models">Models (comma-separated)</Label>
                <Input
                  id="models"
                  value={models}
                  onChange={(e) => setModels(e.target.value)}
                  placeholder="e.g., res.partner, sale.order"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="views">Views (comma-separated)</Label>
                <Input
                  id="views"
                  value={views}
                  onChange={(e) => setViews(e.target.value)}
                  placeholder="e.g., form, tree, search"
                />
              </div>

              <Button
                onClick={handleGenerateOdooModule}
                disabled={isGenerating || !moduleName || !modulePurpose}
                className="w-full"
              >
                {isGenerating ? "Generating Module..." : "Generate Odoo Module"}
              </Button>

              {generateOdooModule.data && (
                <Alert className="border-green-500/50">
                  <AlertDescription className="space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-green-500">
                      <CheckCircle2 className="w-4 h-4" />
                      Odoo Module Generated
                    </div>
                    <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto mt-2">
                      {JSON.stringify(generateOdooModule.data, null, 2)}
                    </pre>
                  </AlertDescription>
                </Alert>
              )}

              {generateOdooModule.error && (
                <Alert className="border-red-500/50">
                  <AlertDescription>
                    <p className="text-red-500 font-semibold">Error</p>
                    <p className="text-sm">{generateOdooModule.error.message}</p>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Code Validation Info */}
      <Card className="brain-card">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title">Automatic Code Validation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 text-orange-500 mt-1" />
              <div>
                <p className="font-semibold">Forbidden Patterns</p>
                <p className="text-xs text-muted-foreground">
                  Detection of eval(), exec(), hardcoded passwords, and missing DSGVO comments
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="w-4 h-4 text-blue-500 mt-1" />
              <div>
                <p className="font-semibold">Privacy by Design (DSGVO Art. 25)</p>
                <p className="text-xs text-muted-foreground">
                  Automatic data minimization and privacy-enhancing defaults
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-green-500 mt-1" />
              <div>
                <p className="font-semibold">Supervisor Integration</p>
                <p className="text-xs text-muted-foreground">
                  HIGH risk code is reviewed by SupervisorAgent before generation
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
