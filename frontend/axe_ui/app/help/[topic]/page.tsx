"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { getAxeHelpTopic, AXE_HELP_TOPICS } from "@/lib/help/topics";
import { useAuthSession } from "@/hooks/useAuthSession";

interface KnowledgeItem {
  id: string;
  title: string;
  content: string;
  updated_at: string;
}

export default function AxeHelpTopicPage() {
  const { withAuthRetry } = useAuthSession();
  const params = useParams<{ topic: string }>();
  const topicKey = decodeURIComponent(params.topic || "");
  const topic = useMemo(() => getAxeHelpTopic(topicKey), [topicKey]);
  const [remote, setRemote] = useState<KnowledgeItem | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const response = await withAuthRetry((token) =>
          fetch(`/api/knowledge-engine/help/${topicKey}?surface=axe-ui`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
            cache: "no-store",
          })
        );
        if (!response.ok) return;
        const data = (await response.json()) as KnowledgeItem;
        if (!active) return;
        setRemote(data);
      } catch {
        if (!active) return;
        setRemote(null);
      }
    };

    if (topicKey) {
      void load();
    }

    return () => {
      active = false;
    };
  }, [topicKey, withAuthRetry]);

  if (!topic && !remote) {
    return (
      <div className="axe-panel rounded-xl p-6">
        <h1 className="axe-surface-title text-xl font-semibold text-white">Hilfe nicht gefunden</h1>
        <p className="mt-2 text-sm text-slate-300">Dieser Hilfebeitrag existiert noch nicht.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="axe-panel rounded-xl p-6">
        <p className="text-[11px] uppercase tracking-[0.18em] text-cyan-300/70">AXE Help</p>
        <h1 className="axe-surface-title mt-2 text-2xl font-bold text-white">{remote?.title || topic?.title || topicKey}</h1>
        {topic?.summary && <p className="mt-2 text-sm text-slate-300">{topic.summary}</p>}
      </div>

      {topic && (
        <div className="axe-panel rounded-xl p-6 space-y-3">
          <p className="text-sm text-slate-200"><span className="font-semibold text-cyan-200">Warum wichtig:</span> {topic.whyItMatters}</p>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <h2 className="text-xs uppercase tracking-wide text-slate-400">Beispiele</h2>
              <ul className="mt-2 space-y-1 text-sm text-slate-200">
                {topic.examples.map((example) => (
                  <li key={example}>• {example}</li>
                ))}
              </ul>
            </div>
            <div>
              <h2 className="text-xs uppercase tracking-wide text-slate-400">Use Cases</h2>
              <ul className="mt-2 space-y-1 text-sm text-slate-200">
                {topic.useCases.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {remote && (
        <div className="axe-panel rounded-xl p-6">
          <h2 className="text-sm font-semibold text-cyan-200">Detaildokumentation</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-200">{remote.content}</p>
        </div>
      )}

      <div className="axe-panel rounded-xl p-6">
        <h2 className="text-sm font-semibold text-cyan-200">Weitere Hilfethemen</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {Object.values(AXE_HELP_TOPICS).map((entry) => (
            <Link
              key={entry.key}
              href={entry.docPath}
              className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:border-cyan-400 hover:text-cyan-200"
            >
              {entry.title}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
