/**
 * TrustTierBanner Component
 *
 * Reusable trust tier awareness banner
 * Shows warnings/info based on current trust tier
 */

"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Lock, Shield, Globe } from "lucide-react";
import { getEstimatedTrustTier } from "@/lib/dnsApi";

type TrustTier = "LOCAL" | "DMZ" | "EXTERNAL" | "UNKNOWN";

interface TrustTierBannerProps {
  requiredTier?: TrustTier;
  feature?: string;
  variant?: "warning" | "info" | "error";
}

export function TrustTierBanner({
  requiredTier = "LOCAL",
  feature = "this operation",
  variant = "warning",
}: TrustTierBannerProps) {
  const [trustTier, setTrustTier] = useState<TrustTier>("UNKNOWN");

  useEffect(() => {
    setTrustTier(getEstimatedTrustTier());
  }, []);

  const isAllowed = checkTierAllowed(trustTier, requiredTier);

  if (isAllowed) {
    // Show success banner for LOCAL tier
    if (trustTier === "LOCAL" && variant === "info") {
      return (
        <div className="rounded-2xl border border-emerald-800 bg-emerald-900/20 p-4">
          <div className="flex items-start gap-3">
            <Lock className="h-5 w-5 text-emerald-500 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-emerald-500">
                LOCAL Trust Tier Detected
              </h3>
              <p className="mt-1 text-sm text-neutral-300">
                You are accessing from localhost. {feature} is enabled.
              </p>
              <p className="mt-2 text-xs text-neutral-500">
                Trust tier: <strong className="text-emerald-400">{trustTier}</strong> (verified client-side hint)
              </p>
            </div>
          </div>
        </div>
      );
    }
    return null;
  }

  // Show restriction banner
  const config = getBannerConfig(variant, trustTier, requiredTier);

  return (
    <div className={`rounded-2xl border p-4 ${config.borderColor} ${config.bgColor}`}>
      <div className="flex items-start gap-3">
        <config.icon className={`h-5 w-5 mt-0.5 ${config.iconColor}`} />
        <div className="flex-1">
          <h3 className={`text-sm font-semibold ${config.titleColor}`}>
            {config.title}
          </h3>
          <p className="mt-1 text-sm text-neutral-300">
            {feature} requires <strong>{requiredTier}</strong> trust tier (localhost only).
          </p>
          <p className="mt-2 text-sm text-neutral-400">
            Detected trust tier: <strong>{trustTier}</strong>
          </p>
          <p className="mt-2 text-xs text-neutral-500">
            {config.instructions}
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function checkTierAllowed(current: TrustTier, required: TrustTier): boolean {
  const hierarchy: Record<TrustTier, number> = {
    LOCAL: 3,
    DMZ: 2,
    EXTERNAL: 1,
    UNKNOWN: 0,
  };

  return hierarchy[current] >= hierarchy[required];
}

function getBannerConfig(variant: string, current: TrustTier, required: TrustTier) {
  if (variant === "error") {
    return {
      icon: AlertTriangle,
      borderColor: "border-red-800",
      bgColor: "bg-red-900/20",
      iconColor: "text-red-500",
      titleColor: "text-red-500",
      title: "Operation Blocked",
      instructions:
        "This operation is strictly restricted to LOCAL trust tier. Access this page from localhost (127.0.0.1) to proceed. All operations are blocked at DMZ and EXTERNAL trust tiers for security.",
    };
  }

  return {
    icon: AlertTriangle,
    borderColor: "border-amber-800",
    bgColor: "bg-amber-900/20",
    iconColor: "text-amber-500",
    titleColor: "text-amber-500",
    title: "Operation Restricted",
    instructions:
      "Access this page from localhost (127.0.0.1) to enable this operation. Operations are blocked at DMZ and EXTERNAL trust tiers for security.",
  };
}
