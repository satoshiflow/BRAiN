/**
 * WebGenesis API Client
 *
 * Client for WebGenesis REST API endpoints
 * Sprint I + Sprint II (Operational + DNS)
 */

import { fetchJson, API_BASE } from "./api";
import type {
  WebsiteSpec,
  SpecSubmitResponse,
  GenerateResponse,
  BuildResponse,
  DeployResponse,
  SiteStatusResponse,
  LifecycleOperationResponse,
  RemoveResponse,
  RollbackResponse,
  ReleasesListResponse,
  SiteListItem,
} from "@/types/webgenesis";

// ============================================================================
// Sprint I - Core Operations
// ============================================================================

/**
 * Submit website specification
 */
export async function submitSpec(spec: WebsiteSpec): Promise<SpecSubmitResponse> {
  const res = await fetch(`${API_BASE}/api/webgenesis/spec`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ spec }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to submit spec: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Generate website source code
 */
export async function generateSite(
  siteId: string,
  force = false
): Promise<GenerateResponse> {
  const res = await fetch(`${API_BASE}/api/webgenesis/${siteId}/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ force }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to generate site: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Build website artifacts
 */
export async function buildSite(
  siteId: string,
  force = false
): Promise<BuildResponse> {
  const res = await fetch(`${API_BASE}/api/webgenesis/${siteId}/build`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ force }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to build site: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Deploy website
 */
export async function deploySite(
  siteId: string,
  force = false
): Promise<DeployResponse> {
  const res = await fetch(`${API_BASE}/api/webgenesis/${siteId}/deploy`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // DMZ headers if available (optional)
      // "x-dmz-gateway-id": "control_center",
      // "x-dmz-gateway-token": "...",
    },
    body: JSON.stringify({ force }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to deploy site: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Get site status
 */
export async function getSiteStatus(siteId: string): Promise<SiteStatusResponse> {
  return fetchJson<SiteStatusResponse>(`/api/webgenesis/${siteId}/status`);
}

// ============================================================================
// Sprint II - Lifecycle Operations
// ============================================================================

/**
 * Start a stopped site
 */
export async function startSite(siteId: string): Promise<LifecycleOperationResponse> {
  const res = await fetch(`${API_BASE}/api/webgenesis/${siteId}/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to start site: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Stop a running site
 */
export async function stopSite(siteId: string): Promise<LifecycleOperationResponse> {
  const res = await fetch(`${API_BASE}/api/webgenesis/${siteId}/stop`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to stop site: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Restart a site
 */
export async function restartSite(siteId: string): Promise<LifecycleOperationResponse> {
  const res = await fetch(`${API_BASE}/api/webgenesis/${siteId}/restart`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to restart site: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Remove a site
 * @param keepData - If true, keep data; if false, delete all data (DESTRUCTIVE)
 */
export async function removeSite(
  siteId: string,
  keepData = true
): Promise<RemoveResponse> {
  const res = await fetch(`${API_BASE}/api/webgenesis/${siteId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ keep_data: keepData }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to remove site: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Rollback site to previous or specific release
 * @param releaseId - Optional: specific release to rollback to
 * @param currentReleaseId - Optional: current release for context
 */
export async function rollbackSite(
  siteId: string,
  releaseId?: string,
  currentReleaseId?: string
): Promise<RollbackResponse> {
  const body: any = {};
  if (releaseId) body.release_id = releaseId;
  if (currentReleaseId) body.current_release_id = currentReleaseId;

  const res = await fetch(`${API_BASE}/api/webgenesis/${siteId}/rollback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to rollback site: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * List all releases for a site
 */
export async function fetchReleases(siteId: string): Promise<ReleasesListResponse> {
  return fetchJson<ReleasesListResponse>(`/api/webgenesis/${siteId}/releases`);
}

// ============================================================================
// Site List Operations
// ============================================================================

/**
 * Fetch all sites
 *
 * NOTE: This requires scanning the storage directory or a new backend endpoint.
 * For MVP, we'll fetch individual site statuses as needed.
 * TODO: Add backend endpoint GET /api/webgenesis/sites
 */
export async function fetchAllSites(): Promise<SiteListItem[]> {
  // PLACEHOLDER: Backend needs to implement GET /api/webgenesis/sites
  // For now, return empty array
  // In production, this should call a backend endpoint that lists all sites

  console.warn(
    "fetchAllSites() placeholder - backend endpoint /api/webgenesis/sites not yet implemented"
  );

  // Temporary solution: Return mock data or empty array
  return [];

  // Future implementation:
  // return fetchJson<{ sites: SiteListItem[] }>("/api/webgenesis/sites")
  //   .then((res) => res.sites);
}

/**
 * Fetch multiple site statuses in parallel
 * Workaround until backend implements bulk list endpoint
 */
export async function fetchSiteStatuses(
  siteIds: string[]
): Promise<SiteStatusResponse[]> {
  const promises = siteIds.map((siteId) => getSiteStatus(siteId));
  return Promise.all(promises);
}

// ============================================================================
// Full Deployment Pipeline
// ============================================================================

/**
 * Execute full deployment pipeline: spec → generate → build → deploy
 * @returns Final deployment result
 */
export async function deployFullPipeline(
  spec: WebsiteSpec,
  options?: {
    forceGenerate?: boolean;
    forceBuild?: boolean;
    forceDeploy?: boolean;
    onProgress?: (stage: string, result: any) => void;
  }
): Promise<{
  spec: SpecSubmitResponse;
  generate: GenerateResponse;
  build: BuildResponse;
  deploy: DeployResponse;
}> {
  const { forceGenerate, forceBuild, forceDeploy, onProgress } = options || {};

  // Step 1: Submit spec
  const specResult = await submitSpec(spec);
  if (onProgress) onProgress("spec", specResult);

  if (!specResult.success) {
    throw new Error(`Spec submission failed: ${specResult.message}`);
  }

  const siteId = specResult.site_id;

  // Step 2: Generate source
  const generateResult = await generateSite(siteId, forceGenerate);
  if (onProgress) onProgress("generate", generateResult);

  if (!generateResult.success) {
    throw new Error(
      `Generation failed: ${generateResult.errors.join(", ") || "Unknown error"}`
    );
  }

  // Step 3: Build artifacts
  const buildResult = await buildSite(siteId, forceBuild);
  if (onProgress) onProgress("build", buildResult);

  if (!buildResult.result.success) {
    throw new Error(
      `Build failed: ${buildResult.result.errors.join(", ") || "Unknown error"}`
    );
  }

  // Step 4: Deploy
  const deployResult = await deploySite(siteId, forceDeploy);
  if (onProgress) onProgress("deploy", deployResult);

  if (!deployResult.result.success) {
    throw new Error(
      `Deployment failed: ${deployResult.result.errors.join(", ") || "Unknown error"}`
    );
  }

  return {
    spec: specResult,
    generate: generateResult,
    build: buildResult,
    deploy: deployResult,
  };
}
