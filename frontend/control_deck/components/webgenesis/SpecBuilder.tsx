/**
 * SpecBuilder Component
 *
 * Multi-step wizard for building WebsiteSpec
 * Steps: 1) Basic Info, 2) Theme, 3) SEO, 4) Deployment, 5) Review & Deploy
 */

"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Check, Eye, Rocket, Loader2 } from "lucide-react";
import type { WebsiteSpec, DNSRecordType } from "@/types/webgenesis";
import { submitSpec, deployFullPipeline } from "@/lib/webgenesisApi";

type Step = 1 | 2 | 3 | 4 | 5;

export function SpecBuilder() {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [showPreview, setShowPreview] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState<any | null>(null);

  // Form state matching WebsiteSpec structure
  const [spec, setSpec] = useState<Partial<WebsiteSpec>>({
    spec_version: "1.0",
    name: "",
    domain: "",
    locale_default: "en",
    locales: ["en"],
    template: "static_html",
    pages: [],
    theme: {
      colors: {
        primary: "#3b82f6",
        secondary: "#8b5cf6",
        accent: "#10b981",
        background: "#ffffff",
        text: "#000000",
      },
      typography: {
        font_family: "Inter, sans-serif",
        base_size: "16px",
        heading_font: "Inter, sans-serif",
      },
    },
    seo: {
      title: "",
      description: "",
      keywords: [],
      twitter_card: "summary_large_image",
    },
    deploy: {
      target: "compose",
      ssl_enabled: false,
      healthcheck_path: "/",
      dns: {
        enable: false,
        zone: "",
        record_type: "A",
        name: "@",
        ttl: 3600,
      },
    },
  });

  const updateSpec = (updates: Partial<WebsiteSpec>) => {
    setSpec((prev) => ({ ...prev, ...updates }));
  };

  const updateThemeColors = (colors: Partial<typeof spec.theme.colors>) => {
    setSpec((prev) => ({
      ...prev,
      theme: {
        ...prev.theme!,
        colors: { ...prev.theme!.colors, ...colors },
      },
    }));
  };

  const updateSEO = (seo: Partial<typeof spec.seo>) => {
    setSpec((prev) => ({
      ...prev,
      seo: { ...prev.seo!, ...seo },
    }));
  };

  const updateDeploy = (deploy: Partial<typeof spec.deploy>) => {
    setSpec((prev) => ({
      ...prev,
      deploy: { ...prev.deploy!, ...deploy },
    }));
  };

  const updateDNS = (dns: Partial<typeof spec.deploy.dns>) => {
    setSpec((prev) => ({
      ...prev,
      deploy: {
        ...prev.deploy!,
        dns: { ...prev.deploy!.dns!, ...dns },
      },
    }));
  };

  async function handleDeploy() {
    setIsDeploying(true);
    setDeployResult(null);

    try {
      // Validate spec before deploying
      if (!spec.name || !spec.domain || !spec.seo?.title || !spec.seo?.description) {
        alert("Please fill in all required fields");
        setIsDeploying(false);
        return;
      }

      // Run full pipeline (spec → generate → build → deploy)
      const result = await deployFullPipeline(spec as WebsiteSpec, {
        forceGenerate: false,
        forceBuild: false,
        forceDeploy: false,
        onProgress: (stage, stageResult) => {
          console.log(`${stage}:`, stageResult);
        },
      });

      setDeployResult(result);
      alert(`Site deployed successfully! Site ID: ${result.spec.site_id}`);

      // Redirect to site detail page
      window.location.href = `/webgenesis/${result.spec.site_id}`;
    } catch (error) {
      console.error("Deployment failed:", error);
      alert(`Deployment failed: ${error}`);
      setDeployResult({ error: String(error) });
    } finally {
      setIsDeploying(false);
    }
  }

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return spec.name && spec.domain;
      case 2:
        return true; // Theme has defaults
      case 3:
        return spec.seo?.title && spec.seo?.description;
      case 4:
        return true; // Deploy has defaults
      case 5:
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Steps Progress */}
      <div className="flex items-center justify-between rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
        <StepIndicator step={1} current={currentStep} label="Basic Info" />
        <StepSeparator />
        <StepIndicator step={2} current={currentStep} label="Theme" />
        <StepSeparator />
        <StepIndicator step={3} current={currentStep} label="SEO" />
        <StepSeparator />
        <StepIndicator step={4} current={currentStep} label="Deployment" />
        <StepSeparator />
        <StepIndicator step={5} current={currentStep} label="Review" />
      </div>

      {/* Step Content */}
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-6">
        {currentStep === 1 && (
          <Step1BasicInfo spec={spec} updateSpec={updateSpec} />
        )}
        {currentStep === 2 && (
          <Step2Theme spec={spec} updateThemeColors={updateThemeColors} />
        )}
        {currentStep === 3 && (
          <Step3SEO spec={spec} updateSEO={updateSEO} />
        )}
        {currentStep === 4 && (
          <Step4Deployment
            spec={spec}
            updateDeploy={updateDeploy}
            updateDNS={updateDNS}
          />
        )}
        {currentStep === 5 && (
          <Step5Review spec={spec} />
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {currentStep > 1 && (
            <button
              onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1) as Step)}
              className="inline-flex items-center gap-2 rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-200 transition-colors hover:bg-neutral-700"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
          )}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="inline-flex items-center gap-2 rounded-lg border border-neutral-700 bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-300 transition-colors hover:bg-neutral-800"
          >
            <Eye className="h-4 w-4" />
            {showPreview ? "Hide" : "Show"} JSON
          </button>

          {currentStep < 5 ? (
            <button
              onClick={() => setCurrentStep((prev) => Math.min(5, prev + 1) as Step)}
              disabled={!canProceed()}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={handleDeploy}
              disabled={isDeploying || !canProceed()}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isDeploying ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Deploying...
                </>
              ) : (
                <>
                  <Rocket className="h-4 w-4" />
                  Deploy Now
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* JSON Preview */}
      {showPreview && (
        <div className="rounded-2xl border border-neutral-800 bg-neutral-950 p-4">
          <h3 className="mb-2 text-sm font-semibold text-white">JSON Preview</h3>
          <pre className="overflow-auto text-xs text-neutral-300">
            {JSON.stringify(spec, null, 2)}
          </pre>
        </div>
      )}

      {/* Deploy Result */}
      {deployResult && !deployResult.error && (
        <div className="rounded-2xl border border-emerald-800 bg-emerald-900/20 p-4">
          <h3 className="text-sm font-semibold text-emerald-500">Deployment Successful!</h3>
          <p className="mt-2 text-sm text-neutral-300">
            Site ID: <span className="font-mono">{deployResult.spec.site_id}</span>
          </p>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Step Indicator Component
// ============================================================================

interface StepIndicatorProps {
  step: number;
  current: number;
  label: string;
}

function StepIndicator({ step, current, label }: StepIndicatorProps) {
  const isActive = step === current;
  const isCompleted = step < current;

  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold transition-colors ${
          isCompleted
            ? "bg-emerald-900/60 text-emerald-300"
            : isActive
            ? "bg-blue-600 text-white"
            : "bg-neutral-800 text-neutral-400"
        }`}
      >
        {isCompleted ? <Check className="h-5 w-5" /> : step}
      </div>
      <span
        className={`text-xs ${
          isActive ? "text-white" : "text-neutral-400"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

function StepSeparator() {
  return <div className="h-px w-8 bg-neutral-800 md:w-16" />;
}

// ============================================================================
// Step 1: Basic Info
// ============================================================================

interface Step1Props {
  spec: Partial<WebsiteSpec>;
  updateSpec: (updates: Partial<WebsiteSpec>) => void;
}

function Step1BasicInfo({ spec, updateSpec }: Step1Props) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Basic Information</h2>
        <p className="text-sm text-neutral-400">
          Set up the fundamental details of your website
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <FormField label="Site Name" required>
          <input
            type="text"
            value={spec.name || ""}
            onChange={(e) => updateSpec({ name: e.target.value })}
            placeholder="My Awesome Site"
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none"
          />
        </FormField>

        <FormField label="Domain" required>
          <input
            type="text"
            value={spec.domain || ""}
            onChange={(e) => updateSpec({ domain: e.target.value })}
            placeholder="example.com"
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none"
          />
        </FormField>

        <FormField label="Template">
          <select
            value={spec.template || "static_html"}
            onChange={(e) => updateSpec({ template: e.target.value as any })}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="static_html">Static HTML</option>
            <option value="nextjs">Next.js</option>
            <option value="react">React</option>
          </select>
        </FormField>

        <FormField label="Default Locale">
          <select
            value={spec.locale_default || "en"}
            onChange={(e) => updateSpec({ locale_default: e.target.value, locales: [e.target.value] })}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="en">English (en)</option>
            <option value="de">German (de)</option>
            <option value="fr">French (fr)</option>
            <option value="es">Spanish (es)</option>
          </select>
        </FormField>
      </div>
    </div>
  );
}

// ============================================================================
// Step 2: Theme
// ============================================================================

interface Step2Props {
  spec: Partial<WebsiteSpec>;
  updateThemeColors: (colors: any) => void;
}

function Step2Theme({ spec, updateThemeColors }: Step2Props) {
  const colors = spec.theme?.colors || {};

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Theme Configuration</h2>
        <p className="text-sm text-neutral-400">
          Customize your website's visual appearance
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <ColorField
          label="Primary Color"
          value={colors.primary || "#3b82f6"}
          onChange={(value) => updateThemeColors({ primary: value })}
        />
        <ColorField
          label="Secondary Color"
          value={colors.secondary || "#8b5cf6"}
          onChange={(value) => updateThemeColors({ secondary: value })}
        />
        <ColorField
          label="Accent Color"
          value={colors.accent || "#10b981"}
          onChange={(value) => updateThemeColors({ accent: value })}
        />
        <ColorField
          label="Background"
          value={colors.background || "#ffffff"}
          onChange={(value) => updateThemeColors({ background: value })}
        />
        <ColorField
          label="Text Color"
          value={colors.text || "#000000"}
          onChange={(value) => updateThemeColors({ text: value })}
        />
      </div>
    </div>
  );
}

// ============================================================================
// Step 3: SEO
// ============================================================================

interface Step3Props {
  spec: Partial<WebsiteSpec>;
  updateSEO: (seo: any) => void;
}

function Step3SEO({ spec, updateSEO }: Step3Props) {
  const seo = spec.seo || {};

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-white">SEO Configuration</h2>
        <p className="text-sm text-neutral-400">
          Optimize your website for search engines
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <FormField label="Page Title" required>
          <input
            type="text"
            value={seo.title || ""}
            onChange={(e) => updateSEO({ title: e.target.value })}
            placeholder="My Awesome Website - Description"
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none"
          />
        </FormField>

        <FormField label="Meta Description" required>
          <textarea
            value={seo.description || ""}
            onChange={(e) => updateSEO({ description: e.target.value })}
            placeholder="A brief description of your website for search engines"
            rows={3}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none"
          />
        </FormField>

        <FormField label="Keywords (comma-separated)">
          <input
            type="text"
            value={seo.keywords?.join(", ") || ""}
            onChange={(e) =>
              updateSEO({
                keywords: e.target.value.split(",").map((k) => k.trim()),
              })
            }
            placeholder="keyword1, keyword2, keyword3"
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none"
          />
        </FormField>

        <FormField label="Twitter Card Type">
          <select
            value={seo.twitter_card || "summary_large_image"}
            onChange={(e) => updateSEO({ twitter_card: e.target.value })}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="summary">Summary</option>
            <option value="summary_large_image">Summary Large Image</option>
            <option value="app">App</option>
            <option value="player">Player</option>
          </select>
        </FormField>
      </div>
    </div>
  );
}

// ============================================================================
// Step 4: Deployment
// ============================================================================

interface Step4Props {
  spec: Partial<WebsiteSpec>;
  updateDeploy: (deploy: any) => void;
  updateDNS: (dns: any) => void;
}

function Step4Deployment({ spec, updateDeploy, updateDNS }: Step4Props) {
  const deploy = spec.deploy || {};
  const dns = deploy.dns || {};

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Deployment Configuration</h2>
        <p className="text-sm text-neutral-400">
          Configure how your site will be deployed
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <FormField label="Deployment Target">
          <select
            value={deploy.target || "compose"}
            onChange={(e) => updateDeploy({ target: e.target.value })}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="compose">Docker Compose</option>
            <option value="k8s">Kubernetes</option>
          </select>
        </FormField>

        <FormField label="Healthcheck Path">
          <input
            type="text"
            value={deploy.healthcheck_path || "/"}
            onChange={(e) => updateDeploy({ healthcheck_path: e.target.value })}
            placeholder="/"
            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none"
          />
        </FormField>
      </div>

      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id="ssl_enabled"
          checked={deploy.ssl_enabled || false}
          onChange={(e) => updateDeploy({ ssl_enabled: e.target.checked })}
          className="h-4 w-4 rounded border-neutral-700 bg-neutral-800 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="ssl_enabled" className="text-sm text-neutral-300">
          Enable SSL/TLS
        </label>
      </div>

      {/* DNS Configuration */}
      <div className="rounded-lg border border-neutral-700 bg-neutral-800/50 p-4">
        <div className="mb-3 flex items-center gap-3">
          <input
            type="checkbox"
            id="dns_enable"
            checked={dns.enable || false}
            onChange={(e) => updateDNS({ enable: e.target.checked })}
            className="h-4 w-4 rounded border-neutral-700 bg-neutral-800 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="dns_enable" className="text-sm font-semibold text-white">
            Configure DNS (Optional)
          </label>
        </div>

        {dns.enable && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <FormField label="DNS Zone">
              <input
                type="text"
                value={dns.zone || ""}
                onChange={(e) => updateDNS({ zone: e.target.value })}
                placeholder="example.com"
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none"
              />
            </FormField>

            <FormField label="Record Type">
              <select
                value={dns.record_type || "A"}
                onChange={(e) => updateDNS({ record_type: e.target.value })}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="A">A (IPv4)</option>
                <option value="AAAA">AAAA (IPv6)</option>
                <option value="CNAME">CNAME</option>
              </select>
            </FormField>

            <FormField label="Record Name">
              <input
                type="text"
                value={dns.name || "@"}
                onChange={(e) => updateDNS({ name: e.target.value })}
                placeholder="@ or subdomain"
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none"
              />
            </FormField>

            <FormField label="TTL (seconds)">
              <input
                type="number"
                value={dns.ttl || 3600}
                onChange={(e) => updateDNS({ ttl: parseInt(e.target.value, 10) })}
                min={60}
                max={86400}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none"
              />
            </FormField>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Step 5: Review
// ============================================================================

interface Step5Props {
  spec: Partial<WebsiteSpec>;
}

function Step5Review({ spec }: Step5Props) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Review & Deploy</h2>
        <p className="text-sm text-neutral-400">
          Review your configuration and deploy your website
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ReviewItem label="Site Name" value={spec.name || "—"} />
        <ReviewItem label="Domain" value={spec.domain || "—"} />
        <ReviewItem label="Template" value={spec.template || "—"} />
        <ReviewItem label="Locale" value={spec.locale_default || "—"} />
        <ReviewItem label="SEO Title" value={spec.seo?.title || "—"} />
        <ReviewItem label="Deploy Target" value={spec.deploy?.target || "—"} />
        <ReviewItem label="SSL Enabled" value={spec.deploy?.ssl_enabled ? "Yes" : "No"} />
        <ReviewItem label="DNS Enabled" value={spec.deploy?.dns?.enable ? "Yes" : "No"} />
      </div>

      <div className="rounded-lg border border-blue-800 bg-blue-900/20 p-4">
        <p className="text-sm text-neutral-300">
          Click <strong className="text-blue-400">"Deploy Now"</strong> to run the full deployment pipeline:
          Spec → Generate → Build → Deploy
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// Helper Components
// ============================================================================

interface FormFieldProps {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}

function FormField({ label, required = false, children }: FormFieldProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-neutral-400">
        {label}
        {required && <span className="ml-1 text-red-400">*</span>}
      </label>
      <div className="mt-1">{children}</div>
    </div>
  );
}

interface ColorFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

function ColorField({ label, value, onChange }: ColorFieldProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-neutral-400">{label}</label>
      <div className="mt-1 flex items-center gap-2">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-10 w-16 cursor-pointer rounded border border-neutral-700 bg-neutral-800"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-xs font-mono text-neutral-200 focus:border-blue-500 focus:outline-none"
        />
      </div>
    </div>
  );
}

interface ReviewItemProps {
  label: string;
  value: string;
}

function ReviewItem({ label, value }: ReviewItemProps) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-800/50 p-3">
      <div className="text-xs font-medium text-neutral-500">{label}</div>
      <div className="mt-1 text-sm text-neutral-200">{value}</div>
    </div>
  );
}
