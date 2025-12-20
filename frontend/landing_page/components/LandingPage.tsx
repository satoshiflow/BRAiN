"use client";

import React, { useMemo, useState } from "react";
import type { Lang } from "@/content/i18n";
import { COPY, PRICING } from "@/content/copy";
import { LanguageToggle } from "./LanguageToggle";

// ========== Hero Section ==========
function Hero({ t, lang, setLang }: { t: any; lang: Lang; setLang: (l: Lang) => void }) {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-black via-black/70 to-black" />
      <div className="relative mx-auto max-w-6xl px-6 pt-10 pb-16">
        <div className="flex items-center justify-between gap-4">
          <div className="text-white/80 text-sm tracking-widest uppercase">BRAiN™ × RYR</div>
          <LanguageToggle lang={lang} onChange={setLang} />
        </div>

        <div className="mt-10 inline-flex rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-white/80">
          {t.hero.badge}
        </div>

        <h1 className="mt-6 text-4xl md:text-6xl font-semibold leading-tight">
          {t.hero.h1}
        </h1>
        <p className="mt-5 max-w-3xl text-lg text-white/75">
          {t.hero.subline}
        </p>
        <p className="mt-4 max-w-3xl text-white/65">{t.hero.trustLine}</p>

        <div className="mt-8 flex flex-wrap gap-3">
          <a href="#waitlist" className="rounded-xl bg-white px-5 py-3 text-black font-medium">
            {t.hero.ctaPrimary}
          </a>
          <a href="#pricing" className="rounded-xl border border-white/20 bg-black/30 px-5 py-3 text-white font-medium">
            {t.hero.ctaSecondary}
          </a>
        </div>

        <p className="mt-6 text-sm text-white/55">{t.hero.micro}</p>
      </div>
    </section>
  );
}

// ========== Problem Section ==========
function Problem({ t }: { t: any }) {
  return (
    <section id="product" className="mx-auto max-w-6xl px-6 py-16">
      <h2 className="text-2xl md:text-3xl font-semibold">{t.problem.title}</h2>
      <ul className="mt-6 grid gap-3 md:grid-cols-2">
        {t.problem.bullets.map((b: string) => (
          <li key={b} className="rounded-2xl border border-white/10 bg-white/5 p-5 text-white/75">
            {b}
          </li>
        ))}
      </ul>
      <p className="mt-6 text-white/65">{t.problem.note}</p>
    </section>
  );
}

// ========== Solution Section ==========
function Solution({ t }: { t: any }) {
  return (
    <section className="mx-auto max-w-6xl px-6 pb-4">
      <h2 className="text-2xl md:text-3xl font-semibold">{t.solution.title}</h2>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {t.solution.blocks.map((x: any) => (
          <div key={x.title} className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-lg font-medium">{x.title}</h3>
            <p className="mt-2 text-white/70">{x.desc}</p>
          </div>
        ))}
      </div>

      <h3 className="mt-12 text-xl font-semibold">{t.solution.stepsTitle}</h3>
      <ol className="mt-4 grid gap-3 md:grid-cols-2">
        {t.solution.steps.map((s: string, idx: number) => (
          <li key={idx} className="rounded-2xl border border-white/10 bg-black/30 p-5 text-white/70">
            <span className="text-white/50 mr-2">{idx + 1}.</span> {s}
          </li>
        ))}
      </ol>
    </section>
  );
}

// ========== UseCases Section ==========
function UseCases({ t }: { t: any }) {
  return (
    <section id="usecases" className="mx-auto max-w-6xl px-6 py-16">
      <h2 className="text-2xl md:text-3xl font-semibold">{t.useCases.title}</h2>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {t.useCases.cards.map((c: any) => (
          <div key={c.title} className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-lg font-medium">{c.title}</h3>
            <p className="mt-2 text-white/70">{c.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// ========== Pricing Section ==========
function Pricing({ t }: { t: any }) {
  return (
    <section id="pricing" className="mx-auto max-w-6xl px-6 py-16">
      <h2 className="text-2xl md:text-3xl font-semibold">{t.pricing.title}</h2>
      <p className="mt-3 max-w-3xl text-white/70">{t.pricing.subtitle}</p>

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        <Card>
          <p className="text-sm text-white/60">{t.pricing.base}</p>
          <p className="mt-3 text-4xl font-semibold">{PRICING.baseMonthlyNet} €</p>
          <p className="mt-2 text-white/70">/ month</p>
        </Card>

        <Card>
          <p className="text-sm text-white/60">{t.pricing.hourly}</p>
          <p className="mt-3 text-4xl font-semibold">{PRICING.hourlyNet.toFixed(2).replace(".", ",")} €</p>
          <p className="mt-2 text-white/70">/ hour</p>
        </Card>

        <Card>
          <p className="text-sm text-white/60">{t.pricing.earlyTitle}</p>
          <p className="mt-3 text-4xl font-semibold">{PRICING.earlyDepositNet} €</p>
          <p className="mt-2 text-white/70">
            {PRICING.earlyTermMonths} months
          </p>
          <p className="mt-4 text-sm text-white/70">{t.pricing.earlyBody}</p>
        </Card>
      </div>

      <p className="mt-6 text-sm text-white/55">{t.pricing.smallPrint}</p>
    </section>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-sm">
      {children}
    </div>
  );
}

// ========== Trust Section ==========
function Trust({ t }: { t: any }) {
  return (
    <section id="trust" className="mx-auto max-w-6xl px-6 pb-8">
      <h2 className="text-2xl md:text-3xl font-semibold">{t.trust.title}</h2>
      <ul className="mt-6 grid gap-3 md:grid-cols-2">
        {t.trust.bullets.map((b: string) => (
          <li key={b} className="rounded-2xl border border-white/10 bg-white/5 p-5 text-white/75">
            {b}
          </li>
        ))}
      </ul>
      <p className="mt-6 text-white/65">{t.trust.note}</p>
    </section>
  );
}

// ========== Waitlist Section ==========
function Waitlist({ t }: { t: any }) {
  const [status, setStatus] = useState<"idle" | "ok">("idle");

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("ok");
  }

  return (
    <section id="waitlist" className="mx-auto max-w-6xl px-6 pb-20 pt-4">
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="text-2xl font-semibold">{t.waitlist.title}</h2>
          <p className="mt-3 text-white/70">{t.waitlist.subtitle}</p>

          <form className="mt-6 grid gap-3" onSubmit={onSubmit}>
            <Field label={t.waitlist.form.company} name="company" />
            <Field label={t.waitlist.form.name} name="name" />
            <Field label={t.waitlist.form.email} name="email" type="email" />

            <button
              type="submit"
              className="mt-2 rounded-xl bg-white px-5 py-3 text-black font-medium"
            >
              {t.waitlist.form.submit}
            </button>

            {status === "ok" && (
              <p className="text-sm text-emerald-400">
                ✓ Erfolgreich vorgemerkt. Wir melden uns bei Ihnen!
              </p>
            )}

            <p className="text-xs text-white/55">{t.waitlist.compliance}</p>
          </form>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h3 className="text-xl font-semibold">{t.waitlist.early.title}</h3>
          <p className="mt-3 text-white/70">{t.waitlist.early.body}</p>

          <button
            type="button"
            className="mt-6 w-full rounded-xl border border-white/20 bg-black/40 px-5 py-3 text-white font-medium"
            onClick={() => alert("Phase 2: Checkout integration")}
          >
            {t.waitlist.early.button}
          </button>

          <p className="mt-3 text-sm text-white/55">{t.waitlist.early.note}</p>

          <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
            <div className="flex items-center justify-between">
              <span>Base</span><span>499 € / month</span>
            </div>
            <div className="mt-2 flex items-center justify-between">
              <span>Usage</span><span>+ 3,60 € / hour</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Field({
  label,
  name,
  type = "text",
}: {
  label: string;
  name: string;
  type?: string;
}) {
  return (
    <label className="grid gap-1">
      <span className="text-sm text-white/70">{label}</span>
      <input
        name={name}
        type={type}
        required
        className="rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white"
      />
    </label>
  );
}

// ========== Footer Section ==========
function Footer({ t }: { t: any }) {
  return (
    <footer className="border-t border-white/10">
      <div className="mx-auto max-w-6xl px-6 py-10 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
        <div className="text-white/70 text-sm">{t.footer.claim}</div>
        <div className="flex gap-4 text-sm text-white/60">
          <a href="#" className="hover:text-white">{t.footer.imprint}</a>
          <a href="#" className="hover:text-white">{t.footer.privacy}</a>
          <a href="#waitlist" className="hover:text-white">{t.footer.contact}</a>
        </div>
      </div>
    </footer>
  );
}

// ========== Main LandingPage Component ==========
export function LandingPage({ initialLang }: { initialLang: Lang }) {
  const [lang, setLang] = useState<Lang>(initialLang);
  const t = useMemo(() => COPY[lang], [lang]);

  return (
    <main className="min-h-screen bg-black text-white">
      <Hero t={t} lang={lang} setLang={setLang} />
      <Problem t={t} />
      <Solution t={t} />
      <UseCases t={t} />
      <Pricing t={t} />
      <Trust t={t} />
      <Waitlist t={t} />
      <Footer t={t} />
    </main>
  );
}
