"use client";

import { useState } from "react";

import { requestPasswordRecovery, resetPassword } from "@/lib/auth";

type LoginGatewayProps = {
  onLogin: (email: string, password: string) => Promise<void>;
  loading?: boolean;
};

type Mode = "login" | "request-reset" | "apply-reset";

export function LoginGateway({ onLogin, loading = false }: LoginGatewayProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const busy = loading || submitting;

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setNotice(null);
    try {
      await onLogin(email, password);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed");
    }
  };

  const handleRequestReset = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSubmitting(true);
    try {
      const response = await requestPasswordRecovery(email);
      setNotice(response.message);
      if (response.reset_token) {
        setResetToken(response.reset_token);
        setMode("apply-reset");
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Recovery request failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleApplyReset = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSubmitting(true);
    try {
      const response = await resetPassword(resetToken, newPassword);
      setNotice(response.message);
      setPassword("");
      setNewPassword("");
      setMode("login");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Password reset failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 px-4 py-8 sm:px-6 lg:grid-cols-2 lg:gap-10 lg:px-8 lg:py-10">
        <section className="relative mb-6 overflow-hidden rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/15 via-slate-900 to-orange-500/10 p-6 lg:mb-0 lg:p-10">
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/80">BRAiN Access</p>
          <h1 className="mt-3 text-3xl font-bold leading-tight text-white sm:text-4xl">AXE Mission Relay</h1>
          <p className="mt-4 max-w-md text-sm text-slate-300 sm:text-base">
            Secure operator access for mission orchestration, governance controls, and live runtime interaction.
          </p>

          <div className="mt-8 space-y-3 text-sm text-slate-200/90">
            <div className="rounded-lg border border-cyan-400/20 bg-slate-900/60 px-3 py-2">SkillRun-first execution and auditability</div>
            <div className="rounded-lg border border-cyan-400/20 bg-slate-900/60 px-3 py-2">Governed provider runtime switching</div>
            <div className="rounded-lg border border-cyan-400/20 bg-slate-900/60 px-3 py-2">Tenant-aware AXE session continuity</div>
          </div>
        </section>

        <section className="flex items-center justify-center">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-2xl">
            <h2 className="text-xl font-semibold text-white">Sign in to AXE</h2>
            <p className="mt-1 text-sm text-slate-400">Login and password recovery only. User onboarding is admin-controlled.</p>

            {mode === "login" && (
              <form className="mt-5 space-y-4" onSubmit={handleLogin}>
                <label className="block text-sm text-slate-300">
                  <span className="mb-1 block">Email</span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400"
                    placeholder="you@example.com"
                  />
                </label>

                <label className="block text-sm text-slate-300">
                  <span className="mb-1 block">Password</span>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400"
                    placeholder="********"
                  />
                </label>

                <div className="flex items-center justify-between text-xs">
                  <button type="button" onClick={() => setMode("request-reset")} className="text-cyan-300 hover:text-cyan-200">
                    Forgot password?
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={busy}
                  className="w-full rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
                >
                  {busy ? "Signing in..." : "Sign in"}
                </button>
              </form>
            )}

            {mode === "request-reset" && (
              <form className="mt-5 space-y-4" onSubmit={handleRequestReset}>
                <label className="block text-sm text-slate-300">
                  <span className="mb-1 block">Recovery email</span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400"
                    placeholder="you@example.com"
                  />
                </label>

                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={busy}
                    className="flex-1 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
                  >
                    {busy ? "Requesting..." : "Request recovery"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode("login")}
                    className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
                  >
                    Back
                  </button>
                </div>
              </form>
            )}

            {mode === "apply-reset" && (
              <form className="mt-5 space-y-4" onSubmit={handleApplyReset}>
                <label className="block text-sm text-slate-300">
                  <span className="mb-1 block">Recovery token</span>
                  <input
                    type="text"
                    required
                    value={resetToken}
                    onChange={(event) => setResetToken(event.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400"
                    placeholder="Paste recovery token"
                  />
                </label>

                <label className="block text-sm text-slate-300">
                  <span className="mb-1 block">New password</span>
                  <input
                    type="password"
                    minLength={8}
                    required
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400"
                    placeholder="At least 8 characters"
                  />
                </label>

                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={busy}
                    className="flex-1 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
                  >
                    {busy ? "Applying..." : "Set new password"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode("login")}
                    className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
                  >
                    Back
                  </button>
                </div>
              </form>
            )}

            {error && <div className="mt-4 rounded-md border border-rose-700 bg-rose-950/60 px-3 py-2 text-sm text-rose-200">{error}</div>}
            {notice && <div className="mt-4 rounded-md border border-cyan-700 bg-cyan-950/40 px-3 py-2 text-sm text-cyan-100">{notice}</div>}
          </div>
        </section>
      </div>
    </div>
  );
}
