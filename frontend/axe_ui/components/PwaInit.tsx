"use client";

import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

export function PwaInit() {
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(
    null,
  );
  const [dismissed, setDismissed] = useState(false);
  const [showIosHint, setShowIosHint] = useState(false);

  const dismissKey = "axe_pwa_prompt_dismissed_until";

  const dismissPrompt = (days = 7) => {
    const until = Date.now() + days * 24 * 60 * 60 * 1000;
    window.localStorage.setItem(dismissKey, String(until));
    setDismissed(true);
    setShowIosHint(false);
  };

  useEffect(() => {
    if (typeof window === "undefined" || process.env.NODE_ENV !== "production") {
      return;
    }

    const dismissedUntil = Number(window.localStorage.getItem(dismissKey) || "0");
    if (dismissedUntil > Date.now()) {
      setDismissed(true);
      return;
    }

    const userAgent = window.navigator.userAgent;
    const isIos = /iPhone|iPad|iPod/i.test(userAgent);
    const isStandalone = window.matchMedia("(display-mode: standalone)").matches ||
      (window.navigator as Navigator & { standalone?: boolean }).standalone === true;
    const isSafari = /^((?!chrome|android).)*safari/i.test(userAgent);

    if (isIos && isSafari && !isStandalone) {
      setShowIosHint(true);
    }

    if (!("serviceWorker" in navigator)) {
      return;
    }

    navigator.serviceWorker.register("/sw.js").catch((error: unknown) => {
      console.error("[PWA] service worker registration failed", error);
    });

    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    };

    const handleInstalled = () => {
      setInstallEvent(null);
      setDismissed(true);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  if (!installEvent || dismissed) {
    if (!showIosHint || dismissed) {
      return null;
    }
  }

  const handleInstall = async () => {
    if (!installEvent) {
      return;
    }
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    if (choice.outcome === "accepted") {
      setInstallEvent(null);
      setShowIosHint(false);
    }
  };

  return (
    <div
      className="fixed inset-x-3 z-[70] sm:left-auto sm:right-4 sm:inset-x-auto sm:w-[360px]"
      style={{ bottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
    >
      <div className="rounded-2xl border border-sky-400/30 bg-slate-900/80 px-4 py-3 shadow-2xl backdrop-blur-xl">
        <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-r from-sky-500/10 via-cyan-400/5 to-blue-500/10" />
        <div className="relative flex items-start gap-3">
          <div className="mt-0.5 rounded-xl bg-sky-500/20 p-2 text-sky-200">
            <Download className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-slate-100">AXE als WebApp installieren</p>
            {installEvent ? (
              <>
                <p className="mt-1 text-xs text-slate-300">
                  Schneller Start vom Homescreen und volle Mobile-Experience.
                </p>
                <button
                  onClick={handleInstall}
                  className="mt-3 rounded-lg bg-sky-500 px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-sky-400"
                >
                  Jetzt installieren
                </button>
              </>
            ) : (
              <p className="mt-1 text-xs text-slate-300">
                iPhone/iPad: Teile-Menue oeffnen und &quot;Zum Home-Bildschirm&quot; waehlen.
              </p>
            )}
          </div>
          <button
            onClick={() => dismissPrompt()}
            className="rounded-md p-1 text-slate-300 transition hover:bg-slate-800 hover:text-white"
            aria-label="Installationshinweis schließen"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
