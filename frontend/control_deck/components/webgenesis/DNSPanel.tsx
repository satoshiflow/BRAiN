/**
 * DNSPanel Component
 *
 * DNS tab for site detail page
 * Shows DNS configuration with LOCAL-only enforcement warnings
 */

"use client";

import { useEffect, useState } from "react";
import { Globe, AlertTriangle, Lock, CheckCircle2, XCircle } from "lucide-react";
import type { DNSZone, DNSRecordApplyRequest, DNSApplyResult } from "@/types/webgenesis";
import { fetchDNSZones, applyDNSRecord, getEstimatedTrustTier } from "@/lib/dnsApi";

type LoadState<T> = {
  data?: T;
  loading: boolean;
  error?: string;
};

interface DNSPanelProps {
  siteId: string;
}

export function DNSPanel({ siteId }: DNSPanelProps) {
  const [zonesState, setZonesState] = useState<LoadState<DNSZone[]>>({
    loading: true,
  });
  const [trustTier, setTrustTier] = useState<string>("UNKNOWN");
  const [isApplying, setIsApplying] = useState(false);
  const [lastResult, setLastResult] = useState<DNSApplyResult | null>(null);

  // Form state
  const [selectedZone, setSelectedZone] = useState<string>("");
  const [recordType, setRecordType] = useState<string>("A");
  const [recordName, setRecordName] = useState<string>("");
  const [recordValue, setRecordValue] = useState<string>("");
  const [ttl, setTtl] = useState<number>(3600);

  useEffect(() => {
    setTrustTier(getEstimatedTrustTier());
    loadZones();
  }, []);

  async function loadZones() {
    setZonesState((prev) => ({ ...prev, loading: true, error: undefined }));
    try {
      const response = await fetchDNSZones();
      setZonesState({ data: response.zones, loading: false });
      if (response.zones.length > 0 && !selectedZone) {
        setSelectedZone(response.zones[0].name);
      }
    } catch (err) {
      setZonesState({ loading: false, error: String(err) });
    }
  }

  async function handleApplyDNS() {
    if (!selectedZone || !recordName) {
      alert("Please fill in all required fields");
      return;
    }

    setIsApplying(true);
    setLastResult(null);

    try {
      const request: DNSRecordApplyRequest = {
        zone: selectedZone,
        record_type: recordType as any,
        name: recordName,
        value: recordValue || null,
        ttl,
      };

      const result = await applyDNSRecord(request);
      setLastResult(result);

      // Clear form on success
      if (result.success) {
        setRecordName("");
        setRecordValue("");
      }
    } catch (error) {
      console.error("Failed to apply DNS record:", error);
      setLastResult({
        success: false,
        zone: selectedZone,
        record_type: recordType as any,
        name: recordName,
        value: recordValue,
        ttl,
        action: "no_change" as any,
        message: String(error),
        errors: [String(error)],
        warnings: [],
      });
    } finally {
      setIsApplying(false);
    }
  }

  const isLocalTier = trustTier === "LOCAL";
  const zones = zonesState.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* Trust Tier Warning */}
      {!isLocalTier && (
        <div className="rounded-2xl border border-amber-800 bg-amber-900/20 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-amber-500">
                DNS Operations Restricted
              </h3>
              <p className="mt-1 text-sm text-neutral-300">
                DNS management requires <strong>LOCAL</strong> trust tier (localhost only).
              </p>
              <p className="mt-2 text-sm text-neutral-400">
                Detected trust tier: <strong>{trustTier}</strong>
              </p>
              <p className="mt-2 text-xs text-neutral-500">
                Access this page from localhost (127.0.0.1) to manage DNS records.
                All DNS operations are blocked at DMZ and EXTERNAL trust tiers for security.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* LOCAL Trust Tier Indicator */}
      {isLocalTier && (
        <div className="rounded-2xl border border-emerald-800 bg-emerald-900/20 p-4">
          <div className="flex items-start gap-3">
            <Lock className="h-5 w-5 text-emerald-500 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-emerald-500">
                LOCAL Trust Tier Detected
              </h3>
              <p className="mt-1 text-sm text-neutral-300">
                You are accessing from localhost. DNS operations are enabled.
              </p>
              <p className="mt-2 text-xs text-neutral-500">
                Trust tier: <strong className="text-emerald-400">LOCAL</strong> (verified client-side hint)
              </p>
            </div>
          </div>
        </div>
      )}

      {/* DNS Zones */}
      {zonesState.loading ? (
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-8">
          <div className="flex items-center justify-center gap-3">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-neutral-700 border-t-blue-500" />
            <span className="text-sm text-neutral-400">Loading DNS zones...</span>
          </div>
        </div>
      ) : zonesState.error ? (
        <div className="rounded-2xl border border-red-800 bg-red-900/20 p-4">
          <h3 className="text-sm font-semibold text-red-500">Error Loading DNS Zones</h3>
          <p className="mt-1 text-sm text-neutral-300">{zonesState.error}</p>
          <p className="mt-2 text-xs text-neutral-500">
            This may be because you are not accessing from localhost (LOCAL trust tier required).
          </p>
        </div>
      ) : zones.length === 0 ? (
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-8 text-center">
          <Globe className="mx-auto h-12 w-12 text-neutral-600" />
          <p className="mt-3 text-sm text-neutral-400">No DNS zones available</p>
          <p className="mt-1 text-xs text-neutral-500">
            Configure HETZNER_DNS_ALLOWED_ZONES in backend settings
          </p>
        </div>
      ) : (
        <>
          {/* DNS Form */}
          <section className="rounded-2xl border border-neutral-800 bg-neutral-900/70 p-4">
            <h2 className="mb-4 text-sm font-semibold text-white">Apply DNS Record</h2>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Zone Selection */}
              <div>
                <label className="block text-xs font-medium text-neutral-400">
                  Zone
                </label>
                <select
                  value={selectedZone}
                  onChange={(e) => setSelectedZone(e.target.value)}
                  disabled={!isLocalTier || isApplying}
                  className="mt-1 w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none disabled:opacity-50"
                >
                  {zones.map((zone) => (
                    <option key={zone.id} value={zone.name}>
                      {zone.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Record Type */}
              <div>
                <label className="block text-xs font-medium text-neutral-400">
                  Record Type
                </label>
                <select
                  value={recordType}
                  onChange={(e) => setRecordType(e.target.value)}
                  disabled={!isLocalTier || isApplying}
                  className="mt-1 w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none disabled:opacity-50"
                >
                  <option value="A">A (IPv4)</option>
                  <option value="AAAA">AAAA (IPv6)</option>
                  <option value="CNAME">CNAME (Alias)</option>
                  <option value="MX">MX (Mail)</option>
                  <option value="TXT">TXT (Text)</option>
                </select>
              </div>

              {/* Record Name */}
              <div>
                <label className="block text-xs font-medium text-neutral-400">
                  Record Name
                </label>
                <input
                  type="text"
                  value={recordName}
                  onChange={(e) => setRecordName(e.target.value)}
                  placeholder="@ or subdomain"
                  disabled={!isLocalTier || isApplying}
                  className="mt-1 w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
                />
                <p className="mt-1 text-xs text-neutral-500">
                  Use "@" for root domain or subdomain name (e.g., "www", "api")
                </p>
              </div>

              {/* Record Value */}
              <div>
                <label className="block text-xs font-medium text-neutral-400">
                  Record Value
                </label>
                <input
                  type="text"
                  value={recordValue}
                  onChange={(e) => setRecordValue(e.target.value)}
                  placeholder={
                    recordType === "A"
                      ? "IPv4 address"
                      : recordType === "AAAA"
                      ? "IPv6 address"
                      : "Value"
                  }
                  disabled={!isLocalTier || isApplying}
                  className="mt-1 w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 placeholder:text-neutral-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
                />
              </div>

              {/* TTL */}
              <div>
                <label className="block text-xs font-medium text-neutral-400">
                  TTL (seconds)
                </label>
                <input
                  type="number"
                  value={ttl}
                  onChange={(e) => setTtl(parseInt(e.target.value, 10))}
                  min={60}
                  max={86400}
                  disabled={!isLocalTier || isApplying}
                  className="mt-1 w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-200 focus:border-blue-500 focus:outline-none disabled:opacity-50"
                />
              </div>
            </div>

            <button
              onClick={handleApplyDNS}
              disabled={!isLocalTier || isApplying || !selectedZone || !recordName}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isApplying ? "Applying..." : "Apply DNS Record"}
            </button>
          </section>

          {/* Last Result */}
          {lastResult && (
            <section
              className={`rounded-2xl border p-4 ${
                lastResult.success
                  ? "border-emerald-800 bg-emerald-900/20"
                  : "border-red-800 bg-red-900/20"
              }`}
            >
              <div className="flex items-start gap-3">
                {lastResult.success ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-500 mt-0.5" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
                )}
                <div className="flex-1">
                  <h3
                    className={`text-sm font-semibold ${
                      lastResult.success ? "text-emerald-500" : "text-red-500"
                    }`}
                  >
                    {lastResult.success ? "DNS Record Applied" : "DNS Operation Failed"}
                  </h3>
                  <p className="mt-1 text-sm text-neutral-300">{lastResult.message}</p>
                  {lastResult.success && (
                    <div className="mt-2 text-xs text-neutral-400">
                      <p>
                        <strong>Action:</strong> {lastResult.action}
                      </p>
                      <p>
                        <strong>Zone:</strong> {lastResult.zone}
                      </p>
                      <p>
                        <strong>Record:</strong> {lastResult.name} ({lastResult.record_type})
                      </p>
                      <p>
                        <strong>Value:</strong> {lastResult.value}
                      </p>
                      {lastResult.record_id && (
                        <p className="font-mono">
                          <strong>Record ID:</strong> {lastResult.record_id}
                        </p>
                      )}
                    </div>
                  )}
                  {lastResult.errors && lastResult.errors.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-medium text-red-400">Errors:</p>
                      <ul className="mt-1 list-inside list-disc text-xs text-neutral-300">
                        {lastResult.errors.map((error, i) => (
                          <li key={i}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {lastResult.warnings && lastResult.warnings.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-medium text-amber-400">Warnings:</p>
                      <ul className="mt-1 list-inside list-disc text-xs text-neutral-300">
                        {lastResult.warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
