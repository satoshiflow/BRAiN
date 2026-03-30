"use client";

import Link from "next/link";
import * as Popover from "@radix-ui/react-popover";
import * as Tooltip from "@radix-ui/react-tooltip";
import { Info } from "lucide-react";

import { cn } from "@/lib/utils";
import type { HelpTopic } from "@/lib/help/topics";

interface HelpHintProps {
  topic: HelpTopic;
  className?: string;
}

export function HelpHint({ topic, className }: HelpHintProps) {
  return (
    <Tooltip.Provider delayDuration={150}>
      <Popover.Root>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <Popover.Trigger asChild>
              <button
                type="button"
                className={cn(
                  "inline-flex h-6 w-6 items-center justify-center rounded-full border border-slate-300 text-slate-500 transition-colors hover:border-cyan-400 hover:text-cyan-600 dark:border-slate-600 dark:text-slate-300 dark:hover:border-cyan-500 dark:hover:text-cyan-300",
                  className
                )}
                aria-label={`Hilfe: ${topic.title}`}
              >
                <Info className="h-3.5 w-3.5" />
              </button>
            </Popover.Trigger>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              side="top"
              sideOffset={8}
              className="z-50 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 shadow-lg dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              Hilfe anzeigen
              <Tooltip.Arrow className="fill-white dark:fill-slate-900" />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>

        <Popover.Portal>
          <Popover.Content
            sideOffset={10}
            className="z-50 w-[360px] rounded-lg border border-slate-200 bg-white p-4 shadow-xl dark:border-slate-700 dark:bg-slate-900"
          >
            <div className="space-y-3">
              <div>
                <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{topic.title}</h4>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">{topic.summary}</p>
              </div>

              <div className="rounded-md border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                <span className="font-semibold">Warum wichtig:</span> {topic.whyItMatters}
              </div>

              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Beispiele</p>
                <ul className="mt-1 space-y-1">
                  {topic.examples.slice(0, 2).map((example) => (
                    <li key={example} className="text-xs text-slate-600 dark:text-slate-300">• {example}</li>
                  ))}
                </ul>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-500 dark:text-slate-400">Use Cases: {topic.useCases.join(", ")}</span>
                <Link
                  href={topic.docPath}
                  className="text-xs font-medium text-cyan-600 hover:text-cyan-700 dark:text-cyan-300 dark:hover:text-cyan-200"
                >
                  Details
                </Link>
              </div>
            </div>
            <Popover.Arrow className="fill-white dark:fill-slate-900" />
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </Tooltip.Provider>
  );
}
