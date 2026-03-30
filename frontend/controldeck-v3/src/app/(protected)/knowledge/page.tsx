"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { knowledgeApi, type KnowledgeItem } from "@/lib/api/knowledge";
import { cn, formatRelativeTime } from "@/lib/utils";
import { HelpHint } from "@/components/help/help-hint";
import { getControlDeckHelpTopic } from "@/lib/help/topics";

const typeOptions = ["all", "note", "doc", "skill", "concept"] as const;

export default function KnowledgePage() {
  const searchParams = useSearchParams();
  const queryFromUrl = (searchParams.get("q") || "").trim();
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [selected, setSelected] = useState<KnowledgeItem | null>(null);
  const [related, setRelated] = useState<KnowledgeItem[]>([]);
  const [versions, setVersions] = useState<Array<{ id: string; version: number; created_at: string }>>([]);
  const [query, setQuery] = useState("");
  const [type, setType] = useState<(typeof typeOptions)[number]>("all");
  const [useSemantic, setUseSemantic] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newType, setNewType] = useState("note");

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await knowledgeApi.list(undefined, type === "all" ? undefined : type);
      setItems(response.items);
      if (response.items.length > 0 && !selected) {
        setSelected(response.items[0]);
      }
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Knowledge konnte nicht geladen werden");
    } finally {
      setIsLoading(false);
    }
  }, [type, selected]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!selected) {
      setRelated([]);
      setVersions([]);
      return;
    }

    let active = true;
    const fetchDetails = async () => {
      try {
        const [relatedRes, versionRes] = await Promise.all([
          knowledgeApi.related(selected.id),
          knowledgeApi.versions(selected.id),
        ]);
        if (!active) return;
        setRelated(relatedRes.related);
        setVersions(versionRes.map(v => ({ id: v.id, version: v.version, created_at: v.created_at })));
      } catch (err) {
        console.error("Failed to load knowledge details", err);
      }
    };

    fetchDetails();
    return () => {
      active = false;
    };
  }, [selected]);

  const runSearch = async () => {
    if (!query.trim()) {
      load();
      return;
    }
    setIsSearching(true);
    try {
      const response = useSemantic
        ? await knowledgeApi.semanticSearch(query.trim(), 25)
        : await knowledgeApi.search(query.trim(), type === "all" ? undefined : type, 25);
      setItems(response.items);
      setSelected(response.items[0] ?? null);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Suche fehlgeschlagen");
    } finally {
      setIsSearching(false);
    }
  };

  useEffect(() => {
    if (!queryFromUrl) {
      return;
    }
    setQuery(queryFromUrl);

    const runInitialSearch = async () => {
      setIsSearching(true);
      try {
        const response = await knowledgeApi.search(queryFromUrl, type === "all" ? undefined : type, 25);
        setItems(response.items);
        setSelected(response.items[0] ?? null);
        setError(null);
      } catch (err) {
        console.error(err);
        setError("Suche fehlgeschlagen");
      } finally {
        setIsSearching(false);
      }
    };

    void runInitialSearch();
  }, [queryFromUrl, type]);

  const createItem = async () => {
    if (!newTitle.trim() || !newContent.trim()) {
      setError("Titel und Inhalt sind erforderlich");
      return;
    }
    try {
      const created = await knowledgeApi.create({
        title: newTitle.trim(),
        content: newContent.trim(),
        type: newType,
        tags: [],
      });
      setItems(prev => [created, ...prev]);
      setSelected(created);
      setNewTitle("");
      setNewContent("");
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Knowledge Item konnte nicht erstellt werden");
    }
  };

  const selectedMeta = useMemo(() => {
    if (!selected) return [] as Array<[string, unknown]>;
    return Object.entries(selected.metadata || {});
  }, [selected]);

  return (
    <div className="space-y-6">

      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Knowledge</h1>
        {(() => {
          const topic = getControlDeckHelpTopic("knowledge.explorer");
          return topic ? <HelpHint topic={topic} /> : null;
        })()}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </div>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">Knowledge Search</h2>
        <div className="grid gap-3 md:grid-cols-[1fr,180px,160px,auto]">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Suche nach Wissen, Konzepten, Skill-Doku..."
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-blue-500 focus:ring-2 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
          />
          <select
            value={type}
            onChange={(e) => setType(e.target.value as (typeof typeOptions)[number])}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
          >
            {typeOptions.map((option) => (
              <option key={option} value={option}>
                {option === "all" ? "Alle Typen" : option}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={useSemantic}
              onChange={(e) => setUseSemantic(e.target.checked)}
              className="h-4 w-4"
            />
            Semantic
          </label>
          <button
            onClick={runSearch}
            disabled={isSearching}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSearching ? "Sucht..." : "Suchen"}
          </button>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">Neues Knowledge Item</h2>
        <div className="grid gap-3 md:grid-cols-[1fr,180px]">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Titel"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
          />
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
          >
            <option value="note">note</option>
            <option value="doc">doc</option>
            <option value="skill">skill</option>
            <option value="concept">concept</option>
          </select>
        </div>
        <textarea
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          placeholder="Inhalt"
          className="mt-3 min-h-28 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
        />
        <div className="mt-3 flex justify-end">
          <button
            onClick={createItem}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            Speichern
          </button>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[420px,1fr]">
        <section className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
          <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-900 dark:border-slate-700 dark:text-slate-100">
            Knowledge Explorer ({items.length})
          </div>
          {isLoading ? (
            <p className="p-4 text-sm text-slate-500">Laden...</p>
          ) : items.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">Keine Einträge</p>
          ) : (
            <div className="max-h-[560px] overflow-auto divide-y divide-slate-100 dark:divide-slate-700">
              {items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setSelected(item)}
                  className={cn(
                    "w-full text-left px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50",
                    selected?.id === item.id && "bg-blue-50 dark:bg-blue-900/20"
                  )}
                >
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{item.title}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.type} · {formatRelativeTime(item.updated_at)}</p>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          {!selected ? (
            <p className="text-sm text-slate-500">Waehle ein Knowledge Item aus.</p>
          ) : (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{selected.title}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{selected.type} · {selected.visibility}</p>
              </div>

              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 whitespace-pre-wrap">
                {selected.content}
              </div>

              <div className="flex flex-wrap gap-2">
                {selected.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-200">#{tag}</span>
                ))}
                {selected.tags.length === 0 && <span className="text-xs text-slate-500">Keine Tags</span>}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Verknuepfte Items</h4>
                  {related.length === 0 ? (
                    <p className="text-xs text-slate-500">Keine Verknuepfungen</p>
                  ) : (
                    <ul className="space-y-1">
                      {related.map((item) => (
                        <li key={item.id} className="text-xs text-slate-700 dark:text-slate-200">{item.title}</li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Versionen</h4>
                  {versions.length === 0 ? (
                    <p className="text-xs text-slate-500">Keine Versionen</p>
                  ) : (
                    <ul className="space-y-1">
                      {versions.map((version) => (
                        <li key={version.id} className="text-xs text-slate-700 dark:text-slate-200">v{version.version} · {formatRelativeTime(version.created_at)}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {selectedMeta.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Metadata</h4>
                  <pre className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 overflow-auto">
                    {JSON.stringify(Object.fromEntries(selectedMeta), null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
