"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";

interface DecisionDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  initialReason: string;
  busy?: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (reason: string) => Promise<void>;
}

export function DecisionDialog({
  open,
  title,
  description,
  confirmLabel,
  initialReason,
  busy = false,
  onOpenChange,
  onConfirm,
}: DecisionDialogProps) {
  const [reason, setReason] = useState(initialReason);

  useEffect(() => {
    if (open) {
      setReason(initialReason);
    }
  }, [initialReason, open]);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,560px)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
          <div className="space-y-4">
            <div>
              <Dialog.Title className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-slate-600 dark:text-slate-300">{description}</Dialog.Description>
            </div>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Reason</span>
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                rows={4}
                minLength={3}
                maxLength={1000}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-0 transition focus:border-cyan-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                placeholder="Document the operator decision"
              />
            </label>

            <div className="flex justify-end gap-2">
              <Dialog.Close asChild>
                <button
                  type="button"
                  disabled={busy}
                  className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="button"
                disabled={busy || reason.trim().length < 3}
                onClick={() => void onConfirm(reason.trim())}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? "Working..." : confirmLabel}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
