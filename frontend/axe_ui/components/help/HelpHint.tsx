"use client";

import Link from "next/link";
import * as Popover from "@radix-ui/react-popover";
import { CircleHelp } from "lucide-react";

import { Tooltip } from "@/components/ui/tooltip";
import type { HelpTopic } from "@/lib/help/topics";

interface HelpHintProps {
  topic: HelpTopic;
}

export function HelpHint({ topic }: HelpHintProps) {
  return (
    <Popover.Root>
      <Tooltip content={<span>Hilfe</span>}>
        <Popover.Trigger asChild>
          <button
            type="button"
            className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-cyan-400/40 text-cyan-300 transition-colors hover:border-cyan-300 hover:text-cyan-200"
            aria-label={`Hilfe: ${topic.title}`}
          >
            <CircleHelp className="h-3.5 w-3.5" />
          </button>
        </Popover.Trigger>
      </Tooltip>
      <Popover.Portal>
        <Popover.Content
          sideOffset={10}
          className="z-50 w-[360px] rounded-lg border border-cyan-500/30 bg-slate-950/95 p-4 text-slate-100 shadow-[0_14px_38px_rgba(0,0,0,0.6)]"
        >
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-semibold text-cyan-100">{topic.title}</h4>
              <p className="mt-1 text-xs text-slate-300">{topic.summary}</p>
            </div>
            <p className="rounded-md border border-cyan-500/20 bg-slate-900/70 p-2 text-xs text-slate-300">
              <span className="font-semibold text-cyan-200">Warum wichtig:</span> {topic.whyItMatters}
            </p>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Beispiele</p>
              <ul className="mt-1 space-y-1 text-xs text-slate-300">
                {topic.examples.slice(0, 2).map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Use Cases: {topic.useCases.join(", ")}</span>
              <Link href={topic.docPath} className="text-cyan-300 hover:text-cyan-200 text-xs font-medium">
                Details
              </Link>
            </div>
          </div>
          <Popover.Arrow className="fill-slate-950" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
