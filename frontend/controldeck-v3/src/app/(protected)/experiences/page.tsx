"use client";

import { useState } from "react";

import {
  experiencesApi,
  type ExperiencePayload,
  type ExperienceRenderRequest,
  type ExperienceRenderResponse,
  type ExperienceSection,
} from "@/lib/api/experiences";

const intentOptions = ["explain", "present", "sell", "summarize"] as const;
const experienceOptions = ["landingpage", "customer_explainer", "mobile_view", "chat_answer", "presentation"] as const;
const audienceOptions = ["public", "customer", "partner", "internal"] as const;
const deviceOptions = ["web", "mobile", "chat"] as const;

type JsonRecord = Record<string, unknown>;

function trimToString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function resolveDataRef(payload: ExperiencePayload, dataRef: string): unknown {
  const directFromData = payload.data[dataRef];
  if (directFromData !== undefined) {
    return directFromData;
  }

  const topLevel = payload as unknown as JsonRecord;
  const path = dataRef.split(".");

  let current: unknown = topLevel;
  for (const key of path) {
    if (!current || typeof current !== "object" || !(key in (current as JsonRecord))) {
      current = undefined;
      break;
    }
    current = (current as JsonRecord)[key];
  }

  if (current !== undefined) {
    return current;
  }

  current = payload.data;
  for (const key of path) {
    if (!current || typeof current !== "object" || !(key in (current as JsonRecord))) {
      return undefined;
    }
    current = (current as JsonRecord)[key];
  }
  return current;
}

function compactText(value: unknown, maxLength = 220): string {
  if (typeof value !== "string") {
    return "";
  }
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 3).trimEnd()}...`;
}

function asExperiencePayload(value: Record<string, unknown>): ExperiencePayload | null {
  const schemaVersion = value.schema_version;
  const sections = value.sections;
  const data = value.data;
  const safety = value.safety;
  const cache = value.cache;

  if (
    typeof schemaVersion !== "string" ||
    !Array.isArray(sections) ||
    !data ||
    typeof data !== "object" ||
    !safety ||
    typeof safety !== "object" ||
    !cache ||
    typeof cache !== "object"
  ) {
    return null;
  }

  return value as unknown as ExperiencePayload;
}

function PreviewSection({ payload, section }: { payload: ExperiencePayload; section: ExperienceSection }) {
  const value = resolveDataRef(payload, section.data_ref);

  if (section.component === "hero_card" || section.component === "title_slide" || section.component === "compact_header") {
    const summary = (value || {}) as JsonRecord;
    const summaryBody = trimToString(summary.body);
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-700 dark:bg-slate-900/60">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{section.component}</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-100">{String(summary.title || "Untitled")}</h3>
        {summaryBody && <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{summaryBody}</p>}
      </div>
    );
  }

  if (section.component === "summary_block") {
    const summary = (value || {}) as JsonRecord;
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Summary</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{String(summary.body || "No summary available.")}</p>
      </div>
    );
  }

  if (section.component === "source_list" || section.component === "source_slide") {
    const sources = Array.isArray(value) ? value : [];
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Sources</h3>
        <div className="mt-3 space-y-2">
          {sources.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No linked sources</p>
          ) : (
            sources.map((source, index) => {
              const item = source as JsonRecord;
              return (
                <div key={`${String(item.id || index)}-${index}`} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{String(item.title || "Untitled")}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] uppercase tracking-[0.14em] text-slate-500 dark:bg-slate-700 dark:text-slate-300">
                      {String(item.type || "note")}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  }

  if (section.component === "key_points" || section.component === "step_list") {
    const knowledgeItems = Array.isArray(value) ? value : [];
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {section.component === "key_points" ? "Key Points" : "Steps"}
        </h3>
        <div className="mt-3 space-y-3">
          {knowledgeItems.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No items available</p>
          ) : (
            knowledgeItems.map((item, index) => {
              const entry = item as JsonRecord;
              return (
                <div key={`${String(entry.id || index)}-${index}`} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{String(entry.title || `Item ${index + 1}`)}</p>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{compactText(entry.content)}</p>
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  }

  if (section.component === "warning_box") {
    const safety = (value || payload.safety) as JsonRecord;
    const warnings = Array.isArray(safety.warnings) ? safety.warnings : [];
    return (
      <div className="rounded-xl border border-amber-300/60 bg-amber-50 p-4 dark:border-amber-500/40 dark:bg-amber-950/30">
        <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-200">Warnings</h3>
        <div className="mt-2 space-y-2">
          {warnings.length === 0 ? (
            <p className="text-sm text-amber-800/80 dark:text-amber-200/80">No explicit warnings</p>
          ) : (
            warnings.map((warning, index) => (
              <p key={`${String(warning)}-${index}`} className="text-sm text-amber-900 dark:text-amber-100">
                {String(warning)}
              </p>
            ))
          )}
        </div>
      </div>
    );
  }

  if (section.component === "cta_block" || section.component === "next_steps") {
    const nextStep = (value || {}) as JsonRecord;
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-950/30">
        <h3 className="text-sm font-semibold text-emerald-900 dark:text-emerald-200">Next Step</h3>
        <p className="mt-2 text-sm text-emerald-900 dark:text-emerald-100">{String(nextStep.label || "No next step defined")}</p>
      </div>
    );
  }

  if (section.component === "audience_context") {
    const audience = (value || {}) as JsonRecord;
    const audienceId = trimToString(audience.id);
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Audience Context</h3>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Type: {String(audience.type || "public")}</p>
        {audienceId && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">ID: {audienceId}</p>}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40">
      <p className="text-sm font-medium text-slate-900 dark:text-slate-100">Unsupported section: {section.component}</p>
      <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-slate-600 dark:text-slate-300">{JSON.stringify(value ?? null, null, 2)}</pre>
    </div>
  );
}

export default function ExperiencesPage() {
  const [intent, setIntent] = useState<(typeof intentOptions)[number]>("explain");
  const [experienceType, setExperienceType] = useState<(typeof experienceOptions)[number]>("landingpage");
  const [audienceType, setAudienceType] = useState<(typeof audienceOptions)[number]>("public");
  const [device, setDevice] = useState<(typeof deviceOptions)[number]>("web");
  const [query, setQuery] = useState("Phyto Uckermark Fruehlingserwachen im Grumsin");
  const [subjectId, setSubjectId] = useState("");
  const [audienceId, setAudienceId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [region, setRegion] = useState("Uckermark");
  const [season, setSeason] = useState("early_spring");
  const [userSkill, setUserSkill] = useState("beginner");
  const [inputText, setInputText] = useState("");
  const [response, setResponse] = useState<ExperienceRenderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState(false);

  async function handleRender() {
    const subjectQuery = trimToString(query);
    const subjectIdentifier = trimToString(subjectId);

    if (!subjectQuery && !subjectIdentifier) {
      setError("Bitte mindestens Query oder Subject-ID angeben.");
      return;
    }

    setIsRendering(true);
    setError(null);

    const request: ExperienceRenderRequest = {
      intent,
      experience_type: experienceType,
      subject: {
        type: "topic",
        id: subjectIdentifier,
        query: subjectQuery,
      },
      audience: {
        type: audienceType,
        id: trimToString(audienceId),
      },
      context: {
        device,
        locale: "de-DE",
        customer_id: trimToString(customerId),
        region: trimToString(region),
        season: trimToString(season),
        user_skill: trimToString(userSkill),
      },
      input: trimToString(inputText)
        ? {
            type: "text",
            source: "user",
            content: { text: inputText.trim() },
            metadata: {},
            context: {},
          }
        : null,
    };

    try {
      const result = await experiencesApi.render(request);
      setResponse(result);
    } catch (err) {
      console.error(err);
      setError("Experience konnte nicht gerendert werden.");
    } finally {
      setIsRendering(false);
    }
  }

  const output = response?.output ?? null;
  const payload = output && output.type !== "answer" ? asExperiencePayload(output.payload) : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Experiences</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Realtime Preview fuer Landingpages, Erklaerseiten, mobile Ansichten und Praesentationen auf Basis des neuen Experience-Composer-MVP.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
          {error}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[420px,1fr]">
        <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Render Request</h2>
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Intent</span>
                <select value={intent} onChange={(event) => setIntent(event.target.value as (typeof intentOptions)[number])} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100">
                  {intentOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Experience Type</span>
                <select value={experienceType} onChange={(event) => setExperienceType(event.target.value as (typeof experienceOptions)[number])} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100">
                  {experienceOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
            </div>

            <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
              <span>Subject Query</span>
              <textarea value={query} onChange={(event) => setQuery(event.target.value)} className="min-h-24 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" />
            </label>

            <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
              <span>Subject ID (optional)</span>
              <input value={subjectId} onChange={(event) => setSubjectId(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" />
            </label>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Audience</span>
                <select value={audienceType} onChange={(event) => setAudienceType(event.target.value as (typeof audienceOptions)[number])} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100">
                  {audienceOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Device</span>
                <select value={device} onChange={(event) => setDevice(event.target.value as (typeof deviceOptions)[number])} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100">
                  {deviceOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Audience ID</span>
                <input value={audienceId} onChange={(event) => setAudienceId(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" />
              </label>
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Customer ID</span>
                <input value={customerId} onChange={(event) => setCustomerId(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" />
              </label>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Region</span>
                <input value={region} onChange={(event) => setRegion(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" />
              </label>
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>Season</span>
                <input value={season} onChange={(event) => setSeason(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" />
              </label>
              <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <span>User Skill</span>
                <input value={userSkill} onChange={(event) => setUserSkill(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" />
              </label>
            </div>

            <label className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
              <span>Optional Input Text</span>
              <textarea value={inputText} onChange={(event) => setInputText(event.target.value)} placeholder="Zusatzkontext, Stichworte, Kurzbriefing..." className="min-h-24 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100" />
            </label>

            <button onClick={handleRender} disabled={isRendering} className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {isRendering ? "Rendert..." : "Experience rendern"}
            </button>
          </div>
        </section>

        <section className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Preview</h2>
              {output && (
                <>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em] text-slate-600 dark:bg-slate-700 dark:text-slate-200">{output.type}</span>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em] text-slate-600 dark:bg-slate-700 dark:text-slate-200">{output.target}</span>
                </>
              )}
            </div>

            {!output && <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">Noch keine Experience gerendert.</p>}

            {output?.type === "answer" && (
              <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
                <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">{String(output.payload.text || "")}</p>
              </div>
            )}

            {payload && (
              <div className="mt-4 space-y-4">
                {payload.sections.map((section, index) => (
                  <PreviewSection key={`${section.component}-${section.data_ref}-${index}`} payload={payload} section={section} />
                ))}
              </div>
            )}
          </div>

          {payload && output && (
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Safety + Cache</h3>
                <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                  <p>Mode: {payload.safety.mode}</p>
                  <p>TTL: {payload.cache.ttl_seconds}s</p>
                  <p>Persist: {payload.cache.persist ? "yes" : "no"}</p>
                  <p>Warnings: {payload.safety.warnings.length}</p>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Metadata</h3>
                <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-slate-600 dark:text-slate-300">{JSON.stringify(output.metadata, null, 2)}</pre>
              </div>
            </div>
          )}

          {output && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Raw Output</h3>
              <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-slate-600 dark:text-slate-300">{JSON.stringify(output, null, 2)}</pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
