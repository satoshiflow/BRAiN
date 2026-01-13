/**
 * Constitutional Agents Dashboard
 *
 * DSGVO and EU AI Act compliant agent system with risk-based supervision
 * and human-in-the-loop workflows.
 */

"use client";

import React, { useState } from 'react';
import {
  useAgentsInfo,
  useSupervisorMetrics,
  useSuperviseAction,
  useGenerateCode,
  useDeployApplication,
  useReviewArchitecture,
  useChatWithAXE,
  type RiskLevel,
} from '@/hooks/useConstitutionalAgents';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Shield, Code, Server, Building2, MessageSquare, CheckCircle2, XCircle, AlertTriangle, TrendingUp } from 'lucide-react';

export default function ConstitutionalAgentsPage() {
  const { data: agentsInfo, isLoading: infoLoading, error: infoError } = useAgentsInfo();
  const { data: metrics, isLoading: metricsLoading } = useSupervisorMetrics();

  if (infoLoading || metricsLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (infoError) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold">Constitutional Agents</h1>
          <p className="text-muted-foreground">
            DSGVO and EU AI Act compliant agent system
          </p>
        </div>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load agents info: {infoError.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Constitutional Agents</h1>
        <p className="text-muted-foreground">
          DSGVO and EU AI Act compliant agent system with risk-based supervision
        </p>
      </div>

      {/* System Overview */}
      {agentsInfo && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Agents</CardTitle>
              <Shield className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{agentsInfo.agents.length}</div>
              <p className="text-xs text-muted-foreground">
                Constitutional framework
              </p>
            </CardContent>
          </Card>

          {metrics && (
            <>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Supervision Requests</CardTitle>
                  <TrendingUp className="h-4 w-4 text-green-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.total_supervision_requests}</div>
                  <p className="text-xs text-muted-foreground">
                    {metrics.approved_actions} approved, {metrics.denied_actions} denied
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Approval Rate</CardTitle>
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{(metrics.approval_rate * 100).toFixed(1)}%</div>
                  <p className="text-xs text-muted-foreground">
                    Automatic approval rate
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Pending Human Review</CardTitle>
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics.human_approvals_pending}</div>
                  <p className="text-xs text-muted-foreground">
                    HIGH/CRITICAL risk actions
                  </p>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}

      {/* Compliance Frameworks */}
      {agentsInfo && (
        <Card>
          <CardHeader>
            <CardTitle>Compliance Frameworks</CardTitle>
            <CardDescription>
              Active legal and regulatory compliance standards
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              {agentsInfo.compliance_frameworks.map((framework) => (
                <Badge key={framework} variant="secondary">
                  {framework}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agent Interfaces */}
      <Tabs defaultValue="supervisor" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="supervisor">
            <Shield className="h-4 w-4 mr-2" />
            Supervisor
          </TabsTrigger>
          <TabsTrigger value="coder">
            <Code className="h-4 w-4 mr-2" />
            Coder
          </TabsTrigger>
          <TabsTrigger value="ops">
            <Server className="h-4 w-4 mr-2" />
            Ops
          </TabsTrigger>
          <TabsTrigger value="architect">
            <Building2 className="h-4 w-4 mr-2" />
            Architect
          </TabsTrigger>
          <TabsTrigger value="axe">
            <MessageSquare className="h-4 w-4 mr-2" />
            AXE
          </TabsTrigger>
        </TabsList>

        <TabsContent value="supervisor">
          <SupervisorInterface />
        </TabsContent>

        <TabsContent value="coder">
          <CoderInterface />
        </TabsContent>

        <TabsContent value="ops">
          <OpsInterface />
        </TabsContent>

        <TabsContent value="architect">
          <ArchitectInterface />
        </TabsContent>

        <TabsContent value="axe">
          <AXEInterface />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================================
// SupervisorAgent Interface
// ============================================================================

function SupervisorInterface() {
  const [requestingAgent, setRequestingAgent] = useState('');
  const [action, setAction] = useState('');
  const [riskLevel, setRiskLevel] = useState<RiskLevel>('medium');
  const superviseMutation = useSuperviseAction();

  const handleSupervise = () => {
    if (!requestingAgent.trim() || !action.trim()) return;

    superviseMutation.mutate({
      requesting_agent: requestingAgent,
      action,
      context: {},
      risk_level: riskLevel,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>SupervisorAgent - Constitutional Guardian</CardTitle>
        <CardDescription>
          Risk-based supervision with 4-tier system (LOW/MEDIUM/HIGH/CRITICAL)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Requesting Agent</Label>
            <Input
              placeholder="e.g., CoderAgent"
              value={requestingAgent}
              onChange={(e) => setRequestingAgent(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Action</Label>
            <Input
              placeholder="e.g., deploy_application"
              value={action}
              onChange={(e) => setAction(e.target.value)}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Risk Level</Label>
          <div className="flex gap-2">
            {(['low', 'medium', 'high', 'critical'] as RiskLevel[]).map((level) => (
              <Badge
                key={level}
                variant={riskLevel === level ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setRiskLevel(level)}
              >
                {level.toUpperCase()}
              </Badge>
            ))}
          </div>
        </div>

        <Button
          onClick={handleSupervise}
          disabled={superviseMutation.isPending || !requestingAgent.trim() || !action.trim()}
          className="w-full"
        >
          {superviseMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Requesting Supervision...
            </>
          ) : (
            'Request Supervision'
          )}
        </Button>

        {superviseMutation.data && (
          <Alert variant={superviseMutation.data.approved ? 'default' : 'destructive'}>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                {superviseMutation.data.approved ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500" />
                )}
                <span className="font-semibold">
                  {superviseMutation.data.approved ? 'Approved' : 'Denied'}
                </span>
              </div>
              <AlertDescription>
                <p>{superviseMutation.data.reason}</p>
                {superviseMutation.data.human_oversight_required && (
                  <p className="mt-2 text-amber-600">
                    Human oversight required: {superviseMutation.data.human_oversight_token}
                  </p>
                )}
                <p className="mt-2 text-xs text-muted-foreground">
                  Audit ID: {superviseMutation.data.audit_id}
                </p>
              </AlertDescription>
            </div>
          </Alert>
        )}

        {superviseMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{superviseMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// CoderAgent Interface
// ============================================================================

function CoderInterface() {
  const [codeSpec, setCodeSpec] = useState('');
  const generateMutation = useGenerateCode();

  const handleGenerate = () => {
    if (!codeSpec.trim()) return;
    generateMutation.mutate({ spec: codeSpec, risk_level: 'low' });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>CoderAgent - Secure Code Generation</CardTitle>
        <CardDescription>
          Code generation with DSGVO compliance and personal data detection
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Code Specification</Label>
          <Textarea
            placeholder="Describe the code you want to generate..."
            value={codeSpec}
            onChange={(e) => setCodeSpec(e.target.value)}
            rows={5}
          />
        </div>

        <Button
          onClick={handleGenerate}
          disabled={generateMutation.isPending || !codeSpec.trim()}
          className="w-full"
        >
          {generateMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating Code...
            </>
          ) : (
            'Generate Code'
          )}
        </Button>

        {generateMutation.data && (
          <div className="space-y-2">
            <Alert>
              <AlertDescription>
                <p className="font-semibold mb-2">Explanation:</p>
                <p>{generateMutation.data.explanation}</p>
              </AlertDescription>
            </Alert>
            <div className="bg-slate-950 p-4 rounded-lg overflow-x-auto">
              <pre className="text-sm text-slate-100">{generateMutation.data.code}</pre>
            </div>
          </div>
        )}

        {generateMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{generateMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// OpsAgent Interface
// ============================================================================

function OpsInterface() {
  const [appName, setAppName] = useState('');
  const [version, setVersion] = useState('');
  const [environment, setEnvironment] = useState<'development' | 'staging' | 'production'>('development');
  const deployMutation = useDeployApplication();

  const handleDeploy = () => {
    if (!appName.trim() || !version.trim()) return;
    deployMutation.mutate({ app_name: appName, version, environment });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>OpsAgent - Safe Operations</CardTitle>
        <CardDescription>
          Deployment with automatic rollback and pre-deployment checks
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Application Name</Label>
            <Input
              placeholder="e.g., brain-backend"
              value={appName}
              onChange={(e) => setAppName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Version</Label>
            <Input
              placeholder="e.g., 1.2.3"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Environment</Label>
          <div className="flex gap-2">
            {(['development', 'staging', 'production'] as const).map((env) => (
              <Badge
                key={env}
                variant={environment === env ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setEnvironment(env)}
              >
                {env.toUpperCase()}
              </Badge>
            ))}
          </div>
          {environment === 'production' && (
            <p className="text-xs text-amber-600">
              ⚠️ Production deployment requires human approval (CRITICAL risk)
            </p>
          )}
        </div>

        <Button
          onClick={handleDeploy}
          disabled={deployMutation.isPending || !appName.trim() || !version.trim()}
          className="w-full"
        >
          {deployMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Deploying...
            </>
          ) : (
            'Deploy Application'
          )}
        </Button>

        {deployMutation.data && (
          <Alert variant={deployMutation.data.success ? 'default' : 'destructive'}>
            <AlertDescription>{deployMutation.data.message}</AlertDescription>
          </Alert>
        )}

        {deployMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{deployMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// ArchitectAgent Interface
// ============================================================================

function ArchitectInterface() {
  const [systemName, setSystemName] = useState('');
  const [usesAI, setUsesAI] = useState(false);
  const [processesPersonalData, setProcessesPersonalData] = useState(false);
  const reviewMutation = useReviewArchitecture();

  const handleReview = () => {
    if (!systemName.trim()) return;
    reviewMutation.mutate({
      system_name: systemName,
      architecture_spec: {
        uses_ai: usesAI,
        processes_personal_data: processesPersonalData,
        international_transfers: false,
      },
      high_risk_ai: false,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>ArchitectAgent - EU Compliance Auditor</CardTitle>
        <CardDescription>
          Architecture review with EU AI Act and DSGVO compliance checks
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>System Name</Label>
          <Input
            placeholder="e.g., Customer Analytics Platform"
            value={systemName}
            onChange={(e) => setSystemName(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="uses-ai"
              checked={usesAI}
              onChange={(e) => setUsesAI(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="uses-ai" className="text-sm">Uses AI</label>
          </div>
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="personal-data"
              checked={processesPersonalData}
              onChange={(e) => setProcessesPersonalData(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="personal-data" className="text-sm">Processes Personal Data</label>
          </div>
        </div>

        <Button
          onClick={handleReview}
          disabled={reviewMutation.isPending || !systemName.trim()}
          className="w-full"
        >
          {reviewMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Reviewing Architecture...
            </>
          ) : (
            'Review Architecture'
          )}
        </Button>

        {reviewMutation.data && (
          <div className="space-y-2">
            <div className="grid gap-2 md:grid-cols-2">
              <div className="border rounded p-2">
                <p className="text-xs text-muted-foreground">Compliance Score</p>
                <p className="text-2xl font-bold">{reviewMutation.data.compliance_score}%</p>
              </div>
              <div className="border rounded p-2">
                <p className="text-xs text-muted-foreground">Scalability</p>
                <p className="text-2xl font-bold capitalize">{reviewMutation.data.scalability_rating}</p>
              </div>
            </div>
            <Alert>
              <AlertDescription>
                <div className="space-y-2">
                  <p>EU AI Act: {reviewMutation.data.eu_ai_act_compliant ? '✅ Compliant' : '❌ Non-compliant'}</p>
                  <p>DSGVO: {reviewMutation.data.dsgvo_compliant ? '✅ Compliant' : '❌ Non-compliant'}</p>
                  {reviewMutation.data.recommendations.length > 0 && (
                    <div>
                      <p className="font-semibold mt-2">Recommendations:</p>
                      <ul className="list-disc list-inside">
                        {reviewMutation.data.recommendations.map((rec, idx) => (
                          <li key={idx} className="text-sm">{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          </div>
        )}

        {reviewMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{reviewMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// AXEAgent Interface
// ============================================================================

function AXEInterface() {
  const [message, setMessage] = useState('');
  const chatMutation = useChatWithAXE();

  const handleChat = () => {
    if (!message.trim()) return;
    chatMutation.mutate({ message, include_history: true });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>AXEAgent - Conversational Assistant</CardTitle>
        <CardDescription>
          Context-aware chat with system monitoring and command execution
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Message</Label>
          <Textarea
            placeholder="Ask about system status, request actions..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
          />
        </div>

        <Button
          onClick={handleChat}
          disabled={chatMutation.isPending || !message.trim()}
          className="w-full"
        >
          {chatMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Chatting...
            </>
          ) : (
            'Send Message'
          )}
        </Button>

        {chatMutation.data && (
          <Alert>
            <AlertDescription>
              <p className="whitespace-pre-wrap">{chatMutation.data.response}</p>
              <p className="text-xs text-muted-foreground mt-2">
                {new Date(chatMutation.data.timestamp).toLocaleString()}
              </p>
            </AlertDescription>
          </Alert>
        )}

        {chatMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>{chatMutation.error.message}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
