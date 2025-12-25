/**
 * WebGenesis TypeScript DTOs
 *
 * Type definitions matching backend/app/modules/webgenesis/schemas.py
 * Sprint I + Sprint II (Operational + DNS)
 */

// ============================================================================
// Enums
// ============================================================================

export type SiteStatus =
  | "pending"
  | "generating"
  | "generated"
  | "building"
  | "built"
  | "deploying"
  | "deployed"
  | "failed";

export type SiteLifecycleStatus =
  | "running"
  | "stopped"
  | "exited"
  | "restarting"
  | "paused"
  | "dead"
  | "created"
  | "unknown";

export type HealthStatus = "healthy" | "unhealthy" | "starting" | "unknown";

export type TemplateType = "static_html" | "nextjs" | "react";

export type DNSRecordType = "A" | "AAAA" | "CNAME" | "MX" | "TXT" | "NS" | "SRV" | "CAA" | "TLSA";

// ============================================================================
// WebsiteSpec Models (Sprint I)
// ============================================================================

export interface ThemeColors {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
}

export interface Typography {
  font_family: string;
  base_size: string;
  heading_font?: string;
}

export interface SEOConfig {
  title: string;
  description: string;
  keywords: string[];
  og_image?: string;
  twitter_card: "summary" | "summary_large_image" | "app" | "player";
}

export interface DNSConfig {
  enable: boolean;
  zone: string;
  record_type: DNSRecordType;
  name: string;
  value?: string | null;
  ttl: number;
}

export interface DeployConfig {
  target: "compose" | "k8s";
  domain?: string;
  ports?: number[];
  ssl_enabled: boolean;
  healthcheck_path: string;
  dns?: DNSConfig;
}

export interface PageSection {
  section_id: string;
  type: "hero" | "features" | "content" | "cta" | "contact" | string;
  title?: string;
  content?: string;
  data: Record<string, any>;
  order: number;
}

export interface PageSpec {
  slug: string;
  title: string;
  description: string;
  sections: PageSection[];
  layout: string;
}

export interface WebsiteSpec {
  spec_version: string;
  name: string;
  domain: string;
  locale_default: string;
  locales: string[];
  template: TemplateType;
  pages: PageSpec[];
  theme: {
    colors: ThemeColors;
    typography: Typography;
  };
  seo: SEOConfig;
  deploy: DeployConfig;
}

// ============================================================================
// Site Manifest (Sprint I)
// ============================================================================

export interface SiteManifest {
  site_id: string;
  spec_hash: string;
  status: SiteStatus;
  created_at: string;
  updated_at: string;
  generated_at?: string;
  built_at?: string;
  deployed_at?: string;
  artifact_hash?: string;
  deployed_url?: string;
  deployed_ports?: number[];
  docker_container_id?: string;
  docker_image_tag?: string;
  deploy_path?: string;
  last_error?: string;
  error_count: number;
  metadata: Record<string, any>;
}

// ============================================================================
// API Response Models (Sprint I)
// ============================================================================

export interface SpecSubmitResponse {
  success: boolean;
  site_id: string;
  spec_hash: string;
  message: string;
}

export interface GenerateResponse {
  success: boolean;
  site_id: string;
  source_path: string;
  files_created: number;
  message: string;
  errors: string[];
}

export interface BuildResult {
  success: boolean;
  site_id: string;
  artifact_path: string;
  artifact_hash?: string;
  timestamp: string;
  errors: string[];
  warnings: string[];
}

export interface BuildResponse {
  result: BuildResult;
  message: string;
}

export interface DeployResult {
  success: boolean;
  site_id: string;
  url?: string;
  container_id?: string;
  container_name?: string;
  ports?: number[];
  timestamp: string;
  errors: string[];
  warnings: string[];
  deploy_log?: string;
}

export interface DeployResponse {
  result: DeployResult;
  message: string;
}

export interface SiteStatusResponse {
  site_id: string;
  manifest: SiteManifest;
  is_running: boolean;
  health_status?: string;
}

// ============================================================================
// Sprint II - Operational Models
// ============================================================================

export interface LifecycleOperationResponse {
  success: boolean;
  site_id: string;
  operation: "start" | "stop" | "restart";
  lifecycle_status: SiteLifecycleStatus;
  message: string;
  warnings: string[];
  errors?: string[];
}

export interface RemoveResponse {
  success: boolean;
  site_id: string;
  message: string;
  data_removed: boolean;
  warnings: string[];
  errors?: string[];
}

export interface ReleaseMetadata {
  release_id: string;
  site_id: string;
  artifact_hash: string;
  created_at: string;
  deployed_url?: string;
  health_status?: HealthStatus;
  metadata?: Record<string, any>;
}

export interface ReleasesListResponse {
  site_id: string;
  releases: ReleaseMetadata[];
  total_count: number;
}

export interface RollbackResponse {
  success: boolean;
  site_id: string;
  from_release?: string;
  to_release: string;
  lifecycle_status: SiteLifecycleStatus;
  health_status: HealthStatus;
  message: string;
  warnings: string[];
  errors?: string[];
}

export interface SiteOperationalStatus {
  site_id: string;
  lifecycle_status: SiteLifecycleStatus;
  health_status: HealthStatus;
  current_release_id?: string;
  uptime_seconds?: number;
  container_id?: string;
  ports?: number[];
}

// ============================================================================
// DNS Models (Sprint II)
// ============================================================================

export interface DNSZone {
  id: string;
  name: string;
  ttl: number;
}

export interface DNSRecord {
  id: string;
  zone_id: string;
  type: DNSRecordType;
  name: string;
  value: string;
  ttl: number;
  created?: string;
  modified?: string;
}

export interface DNSRecordApplyRequest {
  zone: string;
  record_type: DNSRecordType;
  name: string;
  value?: string | null;
  ttl?: number;
}

export interface DNSApplyResult {
  success: boolean;
  zone: string;
  record_type: DNSRecordType;
  name: string;
  value: string;
  ttl: number;
  action: "created" | "updated" | "no_change";
  record_id?: string;
  message: string;
  errors: string[];
  warnings: string[];
}

export interface DNSZonesResponse {
  zones: DNSZone[];
  total_count: number;
  allowed_zones: string[];
}

// ============================================================================
// UI-Specific Models
// ============================================================================

export interface SiteListItem {
  site_id: string;
  domain?: string;
  status: SiteStatus;
  lifecycle_status?: SiteLifecycleStatus;
  health_status?: HealthStatus;
  current_release_id?: string;
  deployed_url?: string;
  dns_enabled: boolean;
  last_action?: string;
  updated_at: string;
}

export interface SiteDetailTabs {
  overview: boolean;
  releases: boolean;
  dns: boolean;
  audit: boolean;
}

// ============================================================================
// Trust Tier (from AXE Governance)
// ============================================================================

export type TrustTier = "LOCAL" | "DMZ" | "EXTERNAL";

export interface TrustContext {
  trust_tier: TrustTier;
  source_ip?: string;
  source_service?: string;
}

// ============================================================================
// Audit Events (for Audit Tab)
// ============================================================================

export interface AuditEvent {
  id: string;
  timestamp: string;
  event_type: string;
  severity: "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  source: string;
  description: string;
  metadata?: Record<string, any>;
}

export interface AuditEventsResponse {
  events: AuditEvent[];
  total_count: number;
  filtered_count: number;
}
