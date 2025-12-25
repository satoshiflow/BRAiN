/**
 * Hetzner DNS API Client
 *
 * Client for Hetzner DNS management endpoints (Sprint II)
 *
 * SECURITY NOTE:
 * DNS endpoints are STRICT LOCAL-only (DMZ/EXTERNAL blocked with HTTP 403)
 * All DNS operations must be from localhost
 */

import { API_BASE } from "./api";
import type {
  DNSRecordApplyRequest,
  DNSApplyResult,
  DNSZonesResponse,
} from "@/types/webgenesis";

// ============================================================================
// DNS Operations (STRICT LOCAL ONLY)
// ============================================================================

/**
 * Apply DNS record (idempotent upsert)
 *
 * **Trust Tier:** STRICT LOCAL only (DMZ/EXTERNAL → HTTP 403)
 *
 * Actions:
 * - created: Record didn't exist, created new
 * - updated: Record exists but different value/TTL, updated
 * - no_change: Record exists with same value/TTL, no action
 *
 * @throws Error if trust tier is not LOCAL or zone not in allowlist
 */
export async function applyDNSRecord(
  request: DNSRecordApplyRequest
): Promise<DNSApplyResult> {
  const res = await fetch(`${API_BASE}/api/dns/hetzner/apply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    // Handle specific error cases
    if (res.status === 403) {
      const data = await res.json().catch(() => ({}));
      throw new Error(
        data.error || "DNS operations require LOCAL trust tier (localhost only)"
      );
    }

    const text = await res.text();
    throw new Error(`Failed to apply DNS record: ${res.status} ${text}`);
  }

  return res.json();
}

/**
 * Fetch DNS zones (only allowlisted zones)
 *
 * **Trust Tier:** STRICT LOCAL only (DMZ/EXTERNAL → HTTP 403)
 *
 * Returns zones that are in HETZNER_DNS_ALLOWED_ZONES allowlist
 *
 * @throws Error if trust tier is not LOCAL
 */
export async function fetchDNSZones(): Promise<DNSZonesResponse> {
  const res = await fetch(`${API_BASE}/api/dns/hetzner/zones`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    // Handle specific error cases
    if (res.status === 403) {
      const data = await res.json().catch(() => ({}));
      throw new Error(
        data.error || "DNS operations require LOCAL trust tier (localhost only)"
      );
    }

    const text = await res.text();
    throw new Error(`Failed to fetch DNS zones: ${res.status} ${text}`);
  }

  return res.json();
}

// ============================================================================
// DNS Validation Helpers
// ============================================================================

/**
 * Validate DNS record name
 * - "@" for root
 * - alphanumeric, hyphens, underscores
 * - no spaces, no special chars
 */
export function isValidDNSName(name: string): boolean {
  if (name === "@") return true;
  return /^[a-zA-Z0-9_-]+$/.test(name);
}

/**
 * Validate DNS zone format
 */
export function isValidDNSZone(zone: string): boolean {
  // Basic domain validation
  return /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(zone);
}

/**
 * Validate IPv4 address
 */
export function isValidIPv4(ip: string): boolean {
  const parts = ip.split(".");
  if (parts.length !== 4) return false;

  return parts.every((part) => {
    const num = parseInt(part, 10);
    return num >= 0 && num <= 255 && part === num.toString();
  });
}

/**
 * Validate IPv6 address (simplified)
 */
export function isValidIPv6(ip: string): boolean {
  // Simplified IPv6 validation
  // Full validation is complex, this is basic check
  return /^[a-fA-F0-9:]+$/.test(ip) && ip.includes(":");
}

/**
 * Validate DNS record value based on type
 */
export function isValidDNSValue(
  value: string,
  recordType: string
): { valid: boolean; error?: string } {
  switch (recordType) {
    case "A":
      if (!isValidIPv4(value)) {
        return { valid: false, error: "Invalid IPv4 address" };
      }
      break;

    case "AAAA":
      if (!isValidIPv6(value)) {
        return { valid: false, error: "Invalid IPv6 address" };
      }
      break;

    case "CNAME":
      if (!isValidDNSZone(value)) {
        return { valid: false, error: "Invalid domain name" };
      }
      break;

    // Add more validation for MX, TXT, etc. as needed
  }

  return { valid: true };
}

// ============================================================================
// Trust Tier Detection (Client-side hint only - NOT security boundary)
// ============================================================================

/**
 * Detect if current request is likely LOCAL tier
 *
 * **NOTE:** This is a CLIENT-SIDE HINT ONLY for UI purposes.
 * Backend enforces actual trust tier validation.
 * Never rely on this for security decisions.
 */
export function isLikelyLocalTier(): boolean {
  if (typeof window === "undefined") return false;

  const hostname = window.location.hostname;

  // Check if localhost or 127.0.0.1
  return (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "[::1]" ||
    hostname.startsWith("192.168.") || // Local network (might be DMZ)
    hostname.startsWith("10.") || // Local network (might be DMZ)
    hostname.startsWith("172.") // Local network (might be DMZ)
  );
}

/**
 * Get estimated trust tier (client-side hint)
 *
 * **NOTE:** This is a CLIENT-SIDE HINT ONLY.
 * Backend is source of truth for trust tier.
 */
export function getEstimatedTrustTier(): "LOCAL" | "DMZ" | "EXTERNAL" | "UNKNOWN" {
  if (typeof window === "undefined") return "UNKNOWN";

  const hostname = window.location.hostname;

  // Localhost = likely LOCAL
  if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]") {
    return "LOCAL";
  }

  // Private IP ranges = likely DMZ
  if (
    hostname.startsWith("192.168.") ||
    hostname.startsWith("10.") ||
    hostname.startsWith("172.")
  ) {
    return "DMZ";
  }

  // Public domain = likely EXTERNAL
  if (hostname.includes(".")) {
    return "EXTERNAL";
  }

  return "UNKNOWN";
}
