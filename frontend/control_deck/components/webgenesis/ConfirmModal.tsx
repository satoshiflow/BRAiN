/**
 * ConfirmModal Component
 *
 * Reusable confirmation dialog for destructive actions
 * Better UX than browser confirm()
 */

"use client";

import { AlertTriangle, Info } from "lucide-react";

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "warning" | "danger" | "info";
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "warning",
}: ConfirmModalProps) {
  if (!isOpen) return null;

  const config = getVariantConfig(variant);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900 p-6 shadow-2xl">
        <div className="flex items-start gap-4">
          <div className={`rounded-full p-2 ${config.iconBg}`}>
            <config.icon className={`h-6 w-6 ${config.iconColor}`} />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            <p className="mt-2 text-sm text-neutral-300">{message}</p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-300 transition-colors hover:bg-neutral-700"
          >
            {cancelLabel}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors ${config.buttonClass}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

function getVariantConfig(variant: string) {
  switch (variant) {
    case "danger":
      return {
        icon: AlertTriangle,
        iconBg: "bg-rose-900/20",
        iconColor: "text-rose-500",
        buttonClass: "bg-rose-600 hover:bg-rose-700",
      };
    case "warning":
      return {
        icon: AlertTriangle,
        iconBg: "bg-amber-900/20",
        iconColor: "text-amber-500",
        buttonClass: "bg-amber-600 hover:bg-amber-700",
      };
    case "info":
      return {
        icon: Info,
        iconBg: "bg-blue-900/20",
        iconColor: "text-blue-500",
        buttonClass: "bg-blue-600 hover:bg-blue-700",
      };
    default:
      return {
        icon: AlertTriangle,
        iconBg: "bg-amber-900/20",
        iconColor: "text-amber-500",
        buttonClass: "bg-amber-600 hover:bg-amber-700",
      };
  }
}
