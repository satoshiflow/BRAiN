/**
 * Sovereign Mode & Fabric Bundle Management Types
 *
 * Auto-generated TypeScript types from backend Pydantic schemas
 * Source: backend/app/modules/sovereign_mode/schemas.py
 *
 * @module types/sovereign
 * @version 1.0.0
 */

// ============================================================================
// ENUMS
// ============================================================================

/**
 * System operation modes
 */
export enum OperationMode {
  /** Full internet access, external models allowed */
  ONLINE = "online",
  /** No internet, offline bundles only */
  OFFLINE = "offline",
  /** Strict mode: offline + enhanced validation */
  SOVEREIGN = "sovereign",
  /** Isolated mode: all external access blocked */
  QUARANTINE = "quarantine",
}

/**
 * Bundle validation and loading status
 */
export enum BundleStatus {
  /** Not yet validated */
  PENDING = "pending",
  /** Hash verified, ready to load */
  VALIDATED = "validated",
  /** Currently active */
  LOADED = "loaded",
  /** Failed validation or security check */
  QUARANTINED = "quarantined",
  /** Load error */
  FAILED = "failed",
}

// ============================================================================
// BUNDLE MODELS
// ============================================================================

/**
 * Offline model bundle metadata
 */
export interface Bundle {
  /** Unique bundle identifier */
  id: string;
  /** Human-readable name */
  name: string;
  /** Semantic version (e.g., 1.0.0) */
  version: string;
  /** Model type (e.g., 'llama', 'mistral') */
  model_type: string;
  /** Model size (e.g., '7B', '13B') */
  model_size: string;
  /** Relative path to model file */
  file_path: string;
  /** Path to manifest.json */
  manifest_path: string;

  // Security
  /** SHA256 hash of model file */
  sha256_hash: string;
  /** SHA256 hash of manifest */
  sha256_manifest_hash: string;
  /** Digital signature (future) */
  signed_by?: string | null;

  // Metadata
  /** Bundle description */
  description?: string | null;
  /** Model capabilities */
  capabilities: string[];
  /** System requirements */
  requirements: Record<string, any>;

  // Status
  status: BundleStatus;
  /** Last validation timestamp */
  last_validated?: string | null;
  /** Last load timestamp */
  last_loaded?: string | null;
  /** Number of times loaded */
  load_count: number;

  // Quarantine info
  /** Reason for quarantine */
  quarantine_reason?: string | null;
  /** Quarantine timestamp */
  quarantine_timestamp?: string | null;
}

/**
 * Result of bundle or operation validation
 */
export interface ValidationResult {
  /** Validation passed */
  is_valid: boolean;
  /** Bundle being validated */
  bundle_id?: string | null;

  // Hash validation
  /** SHA256 hash matches */
  hash_match: boolean;
  /** Expected SHA256 */
  expected_hash?: string | null;
  /** Computed SHA256 */
  actual_hash?: string | null;

  // File checks
  /** File exists on disk */
  file_exists: boolean;
  /** Manifest is valid JSON */
  manifest_valid: boolean;

  // Errors
  /** Validation errors */
  errors: string[];
  /** Validation warnings */
  warnings: string[];

  // Metadata
  validated_at: string;
  /** Validator version */
  validator_version: string;
}

// ============================================================================
// MODE & CONFIGURATION
// ============================================================================

/**
 * Sovereign mode configuration
 */
export interface ModeConfig {
  // Current state
  current_mode: OperationMode;
  /** Currently loaded bundle */
  active_bundle_id?: string | null;

  // Auto-detection
  /** Auto-switch on network loss */
  auto_detect_network: boolean;
  /** Seconds between checks */
  network_check_interval: number;
  /** Enable network monitoring */
  network_check_enabled: boolean;

  // Security settings
  /** Enforce strict hash validation */
  strict_validation: boolean;
  /** Allow unsigned bundles */
  allow_unsigned_bundles: boolean;
  /** Auto-quarantine failed bundles */
  quarantine_on_failure: boolean;

  // Network guards
  /** Block HTTP in offline mode */
  block_external_http: boolean;
  /** Block DNS in offline mode */
  block_external_dns: boolean;
  /** Whitelisted domains */
  allowed_domains: string[];

  // Fallback
  /** Fallback on network loss */
  fallback_to_offline: boolean;
  /** Default offline bundle */
  fallback_bundle_id?: string | null;

  // Audit
  /** Log all mode changes */
  audit_mode_changes: boolean;
  /** Log all bundle operations */
  audit_bundle_loads: boolean;
  /** Log blocked requests */
  audit_network_blocks: boolean;
}

/**
 * Sovereign mode status response
 */
export interface SovereignMode {
  /** Current operation mode */
  mode: OperationMode;
  /** Network connectivity detected */
  is_online: boolean;
  /** In sovereign mode */
  is_sovereign: boolean;

  // Active bundle
  /** Currently loaded bundle */
  active_bundle?: Bundle | null;

  // Statistics
  /** Total bundles available */
  available_bundles: number;
  /** Validated bundles */
  validated_bundles: number;
  /** Quarantined bundles */
  quarantined_bundles: number;

  // Network guards
  /** Blocked requests count */
  network_blocks_count: number;
  /** Last connectivity check */
  last_network_check?: string | null;

  // Config
  config: ModeConfig;

  // Metadata
  /** Sovereign mode version */
  system_version: string;
  /** Last mode switch */
  last_mode_change?: string | null;
}

// ============================================================================
// REQUEST PAYLOADS
// ============================================================================

/**
 * Request to change operation mode
 */
export interface ModeChangeRequest {
  /** Desired mode */
  target_mode: OperationMode;
  /** Force mode change */
  force?: boolean;
  /** Reason for change */
  reason?: string | null;
  /** Bundle to load (for offline) */
  bundle_id?: string | null;
}

/**
 * Request to load a bundle
 */
export interface BundleLoadRequest {
  /** Bundle ID to load */
  bundle_id: string;
  /** Revalidate before loading */
  force_revalidate?: boolean;
  /** Skip quarantine check (unsafe) */
  skip_quarantine_check?: boolean;
}

// ============================================================================
// NETWORK & AUDIT
// ============================================================================

/**
 * Result of network connectivity check
 */
export interface NetworkCheckResult {
  /** Network is available */
  is_online: boolean;
  /** Ping latency in milliseconds */
  latency_ms?: number | null;
  /** Method used (dns, http, ping) */
  check_method: string;
  checked_at: string;
  /** Error if check failed */
  error?: string | null;
}

/**
 * Audit log entry for sovereign mode operations
 */
export interface AuditEntry {
  /** Unique entry ID */
  id: string;
  timestamp: string;
  /** Event type (mode_change, bundle_load, etc.) */
  event_type: string;

  // Event details
  mode_before?: OperationMode | null;
  mode_after?: OperationMode | null;
  bundle_id?: string | null;

  // Context
  /** Reason for event */
  reason?: string | null;
  /** Who/what triggered event */
  triggered_by: string;

  // Result
  /** Operation succeeded */
  success: boolean;
  /** Error if failed */
  error?: string | null;

  // Metadata
  /** Additional context */
  metadata: Record<string, any>;
}

/**
 * System information response
 */
export interface SovereignInfo {
  name: string;
  version: string;
  description: string;
  features: string[];
  endpoints: string[];
}

/**
 * Statistics response
 */
export interface SovereignStatistics {
  bundles: {
    total: number;
    validated: number;
    loaded: number;
    quarantined: number;
    pending: number;
  };
  network: {
    blocks_total: number;
    last_check?: string | null;
    is_online: boolean;
  };
  mode: {
    current: OperationMode;
    changes_count: number;
    last_change?: string | null;
  };
  audit: {
    total_entries: number;
    event_types: Record<string, number>;
  };
}

/**
 * Bundle discovery response
 */
export interface BundleDiscoveryResult {
  discovered: number;
  bundles: string[];
}
