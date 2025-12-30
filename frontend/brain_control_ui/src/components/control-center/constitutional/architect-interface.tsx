"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { useArchitect, type ArchitectureReviewRequest } from "@/hooks/useAgents";
import { Building2, Shield, CheckCircle2, AlertTriangle, Scale, Lock } from "lucide-react";

export function ArchitectInterface() {
  const { reviewArchitecture, checkCompliance, assessScalability, auditSecurity, isReviewing, isCheckingCompliance } = useArchitect();

  // Architecture Review State
  const [systemName, setSystemName] = useState("");
  const [architectureSpec, setArchitectureSpec] = useState("{}");
  const [highRiskAI, setHighRiskAI] = useState(false);

  // Quick Compliance Check State
  const [complianceSpec, setComplianceSpec] = useState("{}");

  // Scalability Assessment State
  const [scalabilitySpec, setScalabilitySpec] = useState("{}");

  // Security Audit State
  const [securitySpec, setSecuritySpec] = useState("{}");

  const handleArchitectureReview = () => {
    let parsedSpec = {};
    try {
      parsedSpec = JSON.parse(architectureSpec);
    } catch (e) {
      alert("Invalid JSON in architecture specification");
      return;
    }

    const request: ArchitectureReviewRequest = {
      system_name: systemName,
      architecture_spec: parsedSpec,
      high_risk_ai: highRiskAI,
    };
    reviewArchitecture.mutate(request);
  };

  const handleComplianceCheck = () => {
    let parsedSpec = {};
    try {
      parsedSpec = JSON.parse(complianceSpec);
    } catch (e) {
      alert("Invalid JSON");
      return;
    }
    checkCompliance.mutate(parsedSpec);
  };

  const handleScalabilityAssessment = () => {
    let parsedSpec = {};
    try {
      parsedSpec = JSON.parse(scalabilitySpec);
    } catch (e) {
      alert("Invalid JSON");
      return;
    }
    assessScalability.mutate(parsedSpec);
  };

  const handleSecurityAudit = () => {
    let parsedSpec = {};
    try {
      parsedSpec = JSON.parse(securitySpec);
    } catch (e) {
      alert("Invalid JSON");
      return;
    }
    auditSecurity.mutate(parsedSpec);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="brain-card border-cyan-500/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-cyan-500/10">
              <Building2 className="w-6 h-6 text-cyan-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg mb-2">Architecture & EU Compliance Auditor</h3>
              <p className="text-sm text-muted-foreground">
                ArchitectAgent performs comprehensive architecture reviews with EU AI Act and DSGVO
                compliance checking, scalability assessment, and security audits.
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                <Badge variant="outline" className="text-xs">
                  <Scale className="w-3 h-3 mr-1" />
                  EU AI Act
                </Badge>
                <Badge variant="outline" className="text-xs">
                  <Shield className="w-3 h-3 mr-1" />
                  DSGVO
                </Badge>
                <Badge variant="outline" className="text-xs">
                  <Lock className="w-3 h-3 mr-1" />
                  Security Audit
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs defaultValue="review" className="space-y-4">
        <TabsList className="bg-brain-panel border border-white/5">
          <TabsTrigger value="review" className="data-[state=active]:bg-brain-accent">
            <Building2 className="w-4 h-4 mr-2" />
            Full Review
          </TabsTrigger>
          <TabsTrigger value="compliance" className="data-[state=active]:bg-brain-accent">
            <Scale className="w-4 h-4 mr-2" />
            Compliance
          </TabsTrigger>
          <TabsTrigger value="scalability" className="data-[state=active]:bg-brain-accent">
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Scalability
          </TabsTrigger>
          <TabsTrigger value="security" className="data-[state=active]:bg-brain-accent">
            <Lock className="w-4 h-4 mr-2" />
            Security
          </TabsTrigger>
        </TabsList>

        {/* Full Architecture Review */}
        <TabsContent value="review">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <CardTitle className="brain-card-title">Comprehensive Architecture Review</CardTitle>
              <CardDescription>
                EU AI Act + DSGVO + Security + Scalability analysis
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert className="border-cyan-500/50">
                <AlertDescription className="text-xs">
                  <p className="font-semibold mb-1">High-Risk AI Systems</p>
                  <p>
                    Systems classified as high-risk under EU AI Act (biometric identification,
                    critical infrastructure, law enforcement) receive additional scrutiny.
                  </p>
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label htmlFor="systemName">System Name</Label>
                <Input
                  id="systemName"
                  value={systemName}
                  onChange={(e) => setSystemName(e.target.value)}
                  placeholder="e.g., Customer Data Platform"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="architectureSpec">Architecture Specification (JSON)</Label>
                <Textarea
                  id="architectureSpec"
                  value={architectureSpec}
                  onChange={(e) => setArchitectureSpec(e.target.value)}
                  placeholder={`{
  "uses_ai": true,
  "processes_personal_data": true,
  "data_types": ["names", "emails", "addresses"],
  "international_transfers": false,
  "components": ["api", "database", "ml_service"],
  "architecture_type": "microservices"
}`}
                  className="font-mono text-xs"
                  rows={10}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="highRiskAI"
                  checked={highRiskAI}
                  onCheckedChange={(checked) => setHighRiskAI(checked === true)}
                />
                <Label htmlFor="highRiskAI" className="text-sm cursor-pointer">
                  This is a high-risk AI system (EU AI Act)
                </Label>
              </div>
              <p className="text-xs text-muted-foreground">
                Check if system falls under EU AI Act high-risk categories (Art. 6)
              </p>

              <Button
                onClick={handleArchitectureReview}
                disabled={isReviewing || !systemName}
                className="w-full"
              >
                {isReviewing ? "Reviewing..." : "Start Architecture Review"}
              </Button>

              {reviewArchitecture.data && (
                <Alert className="border-green-500/50">
                  <AlertDescription className="space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-green-500">
                      <CheckCircle2 className="w-4 h-4" />
                      Architecture Review Completed
                    </div>
                    <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto mt-2 max-h-96">
                      {JSON.stringify(reviewArchitecture.data, null, 2)}
                    </pre>
                  </AlertDescription>
                </Alert>
              )}

              {reviewArchitecture.error && (
                <Alert className="border-red-500/50">
                  <AlertDescription>
                    <p className="text-red-500 font-semibold">Review Failed</p>
                    <p className="text-sm">{reviewArchitecture.error.message}</p>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* EU Compliance Check */}
        <TabsContent value="compliance">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <CardTitle className="brain-card-title">EU Compliance Check</CardTitle>
              <CardDescription>
                Quick EU AI Act + DSGVO compliance validation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="complianceSpec">System Specification (JSON)</Label>
                <Textarea
                  id="complianceSpec"
                  value={complianceSpec}
                  onChange={(e) => setComplianceSpec(e.target.value)}
                  placeholder={`{
  "uses_biometric_categorization": false,
  "uses_social_scoring": false,
  "manipulates_behavior": false,
  "processes_personal_data": true,
  "has_consent_mechanism": true,
  "has_privacy_policy": true
}`}
                  className="font-mono text-xs"
                  rows={8}
                />
              </div>

              <Button
                onClick={handleComplianceCheck}
                disabled={isCheckingCompliance}
                className="w-full"
              >
                {isCheckingCompliance ? "Checking..." : "Check Compliance"}
              </Button>

              {checkCompliance.data && (
                <Alert className="border-green-500/50">
                  <AlertDescription className="space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-green-500">
                      <CheckCircle2 className="w-4 h-4" />
                      Compliance Check Completed
                    </div>
                    <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto mt-2">
                      {JSON.stringify(checkCompliance.data, null, 2)}
                    </pre>
                  </AlertDescription>
                </Alert>
              )}

              {checkCompliance.error && (
                <Alert className="border-red-500/50">
                  <AlertDescription>
                    <p className="text-red-500 font-semibold">Check Failed</p>
                    <p className="text-sm">{checkCompliance.error.message}</p>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Scalability Assessment */}
        <TabsContent value="scalability">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <CardTitle className="brain-card-title">Scalability Assessment</CardTitle>
              <CardDescription>
                Analyze system scalability and performance characteristics
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="scalabilitySpec">System Specification (JSON)</Label>
                <Textarea
                  id="scalabilitySpec"
                  value={scalabilitySpec}
                  onChange={(e) => setScalabilitySpec(e.target.value)}
                  placeholder={`{
  "expected_users": 10000,
  "expected_requests_per_second": 1000,
  "data_volume_gb": 500,
  "architecture_type": "microservices",
  "uses_caching": true,
  "uses_load_balancing": true
}`}
                  className="font-mono text-xs"
                  rows={8}
                />
              </div>

              <Button
                onClick={handleScalabilityAssessment}
                disabled={assessScalability.isPending}
                className="w-full"
              >
                {assessScalability.isPending ? "Assessing..." : "Assess Scalability"}
              </Button>

              {assessScalability.data && (
                <Alert className="border-green-500/50">
                  <AlertDescription className="space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-green-500">
                      <CheckCircle2 className="w-4 h-4" />
                      Assessment Completed
                    </div>
                    <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto mt-2">
                      {JSON.stringify(assessScalability.data, null, 2)}
                    </pre>
                  </AlertDescription>
                </Alert>
              )}

              {assessScalability.error && (
                <Alert className="border-red-500/50">
                  <AlertDescription>
                    <p className="text-red-500 font-semibold">Assessment Failed</p>
                    <p className="text-sm">{assessScalability.error.message}</p>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Audit */}
        <TabsContent value="security">
          <Card className="brain-card">
            <CardHeader className="brain-card-header">
              <CardTitle className="brain-card-title">Security Audit</CardTitle>
              <CardDescription>
                Security architecture review and vulnerability assessment
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="securitySpec">System Specification (JSON)</Label>
                <Textarea
                  id="securitySpec"
                  value={securitySpec}
                  onChange={(e) => setSecuritySpec(e.target.value)}
                  placeholder={`{
  "authentication_method": "oauth2",
  "encryption_at_rest": true,
  "encryption_in_transit": true,
  "has_firewall": true,
  "has_intrusion_detection": false,
  "vulnerability_scanning": true
}`}
                  className="font-mono text-xs"
                  rows={8}
                />
              </div>

              <Button
                onClick={handleSecurityAudit}
                disabled={auditSecurity.isPending}
                className="w-full"
              >
                {auditSecurity.isPending ? "Auditing..." : "Start Security Audit"}
              </Button>

              {auditSecurity.data && (
                <Alert className="border-green-500/50">
                  <AlertDescription className="space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-green-500">
                      <CheckCircle2 className="w-4 h-4" />
                      Security Audit Completed
                    </div>
                    <pre className="text-xs bg-black/40 p-3 rounded-lg overflow-x-auto mt-2">
                      {JSON.stringify(auditSecurity.data, null, 2)}
                    </pre>
                  </AlertDescription>
                </Alert>
              )}

              {auditSecurity.error && (
                <Alert className="border-red-500/50">
                  <AlertDescription>
                    <p className="text-red-500 font-semibold">Audit Failed</p>
                    <p className="text-sm">{auditSecurity.error.message}</p>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Prohibited Practices Info */}
      <Card className="brain-card border-red-500/20">
        <CardHeader className="brain-card-header">
          <CardTitle className="brain-card-title flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            EU AI Act Prohibited Practices
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <p className="text-xs text-muted-foreground mb-3">
              ArchitectAgent automatically detects these prohibited AI practices (EU AI Act Art. 5):
            </p>
            <div className="grid gap-2 md:grid-cols-2">
              <div className="flex items-start gap-2">
                <span className="text-red-500">✗</span>
                <span className="text-xs">Social scoring systems</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-red-500">✗</span>
                <span className="text-xs">Subliminal manipulation</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-red-500">✗</span>
                <span className="text-xs">Biometric categorization</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-red-500">✗</span>
                <span className="text-xs">Exploiting vulnerabilities</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
