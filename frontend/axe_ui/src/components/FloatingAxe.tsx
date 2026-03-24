"use client";

import React, { useEffect } from "react";
import CanonicalFloatingAxe from "@/components/FloatingAxe";
import type { FloatingAxeProps, AxeWidgetPosition } from "../types";

function mapLegacyPosition(position: AxeWidgetPosition | undefined): "bottom-right" | "bottom-left" | "top-right" | "top-left" {
  if (!position) {
    return "bottom-right";
  }

  const isTop = typeof position.top === "number";
  const isLeft = typeof position.left === "number";

  if (isTop && isLeft) {
    return "top-left";
  }
  if (isTop) {
    return "top-right";
  }
  if (isLeft) {
    return "bottom-left";
  }

  return "bottom-right";
}

export function FloatingAxe({ appId, backendUrl, theme = "dark", position, onEvent }: FloatingAxeProps) {
  useEffect(() => {
    if (typeof console !== "undefined") {
      console.warn("[AXE] src/components/FloatingAxe is deprecated; use src/widget.ts canonical exports.");
    }
  }, []);

  void onEvent;

  const originAllowlist = typeof window !== "undefined" ? window.location.origin : "localhost";

  return (
    <CanonicalFloatingAxe
      appId={appId}
      backendUrl={backendUrl}
      originAllowlist={originAllowlist}
      theme={theme}
      position={mapLegacyPosition(position)}
    />
  );
}
