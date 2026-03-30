"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { knowledgeApi, type KnowledgeItem } from "@/lib/api/knowledge";
import { CONTROLDECK_HELP_TOPICS, getControlDeckHelpTopic } from "@/lib/help/topics";

export default function HelpTopicPage() {
  const params = useParams<{ topic: string }>();
  const topicKey = decodeURIComponent(params.topic || "");
  const localTopic = useMemo(() => getControlDeckHelpTopic(topicKey), [topicKey]);
  const [remoteDoc, setRemoteDoc] = useState<KnowledgeItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const item = await knowledgeApi.getHelpDoc(topicKey, "controldeck-v3");
        if (!active) return;
        setRemoteDoc(item);
      } catch {
        if (!active) return;
        setRemoteDoc(null);
      }
    };

    if (topicKey) {
      void load();
    }

    return () => {
      active = false;
    };
  }, [topicKey]);

  if (!localTopic && !remoteDoc) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Hilfe nicht gefunden</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">Für diesen Bereich gibt es noch keinen Hilfebeitrag.</p>
        <Link href="/knowledge" className="text-sm text-cyan-600 dark:text-cyan-300">Zum Knowledge Explorer</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">BRAiN Help</p>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          {remoteDoc?.title || localTopic?.title || topicKey}
        </h1>
        {localTopic?.summary && (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{localTopic.summary}</p>
        )}
      </header>

      {localTopic && (
        <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Quick Guidance</h2>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">
            <span className="font-semibold">Warum wichtig:</span> {localTopic.whyItMatters}
          </p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Beispiele</h3>
              <ul className="mt-1 space-y-1 text-sm text-slate-700 dark:text-slate-200">
                {localTopic.examples.map((example) => (
                  <li key={example}>• {example}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Use Cases</h3>
              <ul className="mt-1 space-y-1 text-sm text-slate-700 dark:text-slate-200">
                {localTopic.useCases.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      {remoteDoc && (
        <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Detaildokumentation</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200">{remoteDoc.content}</p>
        </section>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Weitere Hilfe-Themen</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {Object.values(CONTROLDECK_HELP_TOPICS).map((topic) => (
            <Link
              key={topic.key}
              href={topic.docPath}
              className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:border-cyan-400 hover:text-cyan-700 dark:border-slate-700 dark:text-slate-200 dark:hover:border-cyan-500 dark:hover:text-cyan-300"
            >
              {topic.title}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
