/**
 * ControlDeck v3 Configuration
 *
 * MUST HAVE:
 * - Never hardcode real deployment URLs in app feature code.
 * - All runtime service resolution must go through this file.
 */

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

export type RuntimeMode = "local" | "production";

function normalizeAbsoluteUrl(value?: string): string | null {
  if (!value) {
    return null;
  }

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function resolveOriginRelativeBase(pathValue?: string): string | null {
  if (!pathValue || typeof window === "undefined") {
    return null;
  }

  const normalizedPath = pathValue.startsWith("/") ? pathValue : `/${pathValue}`;
  return `${window.location.origin}${normalizedPath}`;
}

function warnOnCompatibilityFallback(target: "api" | "controlDeck" | "axeUI", fallback: string) {
  if (typeof window === "undefined") {
    return;
  }

  if (process.env.NODE_ENV === "production") {
    console.warn(
      `[${process.env.NEXT_PUBLIC_APP_ENV || 'unknown'} config] Using compatibility fallback for ${target}: ${fallback}. ` +
        "Set explicit NEXT_PUBLIC_* runtime variables to avoid environment drift."
    );
  }
}

export function detectRuntimeMode(): RuntimeMode {
  const explicit = process.env.NEXT_PUBLIC_APP_ENV;
  if (explicit === "local" || explicit === "production") {
    return explicit;
  }

  if (typeof window !== "undefined") {
    return LOCAL_HOSTS.has(window.location.hostname) ? "local" : "production";
  }

  return "production";
}

export function getApiBase(mode?: RuntimeMode): string {
  const explicit = normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_BRAIN_API_BASE);
  if (explicit) {
    return explicit;
  }

  const runtimeMode = mode ?? detectRuntimeMode();

  const originRelative = resolveOriginRelativeBase(process.env.NEXT_PUBLIC_BRAIN_API_PATH);
  if (originRelative) {
    return originRelative;
  }

  const modeSpecific =
    runtimeMode === "local"
      ? normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_BRAIN_API_BASE_LOCAL)
      : normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_BRAIN_API_BASE_PRODUCTION);
  if (modeSpecific) {
    return modeSpecific;
  }

  if (runtimeMode === "local") {
    const fallback = "http://127.0.0.1:8000";
    warnOnCompatibilityFallback("api", fallback);
    return fallback;
  }

  const fallback = "https://api.brain.falklabs.de";
  warnOnCompatibilityFallback("api", fallback);
  return fallback;
}

export function getControlDeckBase(mode?: RuntimeMode): string {
  const explicit = normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_CONTROL_DECK_BASE);
  if (explicit) {
    return explicit;
  }

  const runtimeMode = mode ?? detectRuntimeMode();
  const originRelative = resolveOriginRelativeBase(process.env.NEXT_PUBLIC_CONTROL_DECK_PATH);
  if (originRelative) {
    return originRelative;
  }

  const modeSpecific =
    runtimeMode === "local"
      ? normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_CONTROL_DECK_BASE_LOCAL)
      : normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_CONTROL_DECK_BASE_PRODUCTION);
  if (modeSpecific) {
    return modeSpecific;
  }

  if (runtimeMode === "local") {
    const fallback = "http://127.0.0.1:3003";
    warnOnCompatibilityFallback("controlDeck", fallback);
    return fallback;
  }

  const fallback = "https://control.brain.falklabs.de";
  warnOnCompatibilityFallback("controlDeck", fallback);
  return fallback;
}

export function getAxeUIBase(mode?: RuntimeMode): string {
  const explicit = normalizeAbsoluteUrl(process.env.NEXT_PUBLIC_AXE_UI_BASE);
  if (explicit) {
    return explicit;
  }

  const runtimeMode = mode ?? detectRuntimeMode();
  if (runtimeMode === "local") {
    const fallback = "http://127.0.0.1:3002";
    warnOnCompatibilityFallback("axeUI", fallback);
    return fallback;
  }

  const fallback = "https://axe.brain.falklabs.de";
  warnOnCompatibilityFallback("axeUI", fallback);
  return fallback;
}

export const config = {
  runtimeMode: detectRuntimeMode(),
  api: {
    base: getApiBase(),
  },
};
