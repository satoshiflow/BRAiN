"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuthSession } from "@/hooks/useAuthSession";
import { getApiBase, getControlDeckBase } from "@/lib/config";
import {
  changeAdminUserRole,
  createAdminInvitation,
  getAxeProviderRuntime,
  listAdminInvitations,
  listAdminUsers,
  toggleAdminUserActive,
  updateAxeProviderRuntime,
} from "@/lib/api";
import type { AdminInvitation, AdminUser, AxeProvider, AxeProviderRuntimeResponse } from "@/lib/contracts";

export default function SettingsPage() {
  const { user, withAuthRetry } = useAuthSession();
  const apiBase = getApiBase();
  const controlDeckBase = getControlDeckBase();
  const controlDeckProviderUrl = `${controlDeckBase}/settings/llm-providers`;
  const controlDeckRoutingUrl = `${controlDeckBase}/settings`;
  const [providerRuntime, setProviderRuntime] = useState<AxeProviderRuntimeResponse | null>(null);
  const [providerSelection, setProviderSelection] = useState<AxeProvider>("mock");
  const [runtimeLoading, setRuntimeLoading] = useState(false);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [invitations, setInvitations] = useState<AdminInvitation[]>([]);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "operator" | "viewer">("operator");

  const isAdmin = user?.role === "admin";

  const loadRuntime = useCallback(async () => {
    try {
      setRuntimeLoading(true);
      setRuntimeError(null);
      const runtime = await withAuthRetry((token) =>
        getAxeProviderRuntime({ Authorization: `Bearer ${token}` })
      );
      setProviderRuntime(runtime);
      setProviderSelection(runtime.provider);
    } catch (error) {
      setRuntimeError(error instanceof Error ? error.message : "Could not load provider runtime");
    } finally {
      setRuntimeLoading(false);
    }
  }, [withAuthRetry]);

  const loadAdminData = useCallback(async () => {
    if (!isAdmin) {
      setUsers([]);
      setInvitations([]);
      return;
    }
    try {
      setAdminLoading(true);
      setAdminError(null);
      const [loadedUsers, loadedInvites] = await Promise.all([
        withAuthRetry((token) => listAdminUsers({ Authorization: `Bearer ${token}` })),
        withAuthRetry((token) => listAdminInvitations({ Authorization: `Bearer ${token}` })),
      ]);
      setUsers(loadedUsers);
      setInvitations(loadedInvites);
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : "Could not load admin data");
    } finally {
      setAdminLoading(false);
    }
  }, [isAdmin, withAuthRetry]);

  useEffect(() => {
    void loadRuntime();
  }, [loadRuntime]);

  useEffect(() => {
    void loadAdminData();
  }, [loadAdminData]);

  const applyProviderSelection = async () => {
    const confirmed = window.confirm(
      `Switch provider runtime to '${providerSelection}'? This affects all active AXE chats.`
    );
    if (!confirmed) return;
    try {
      setRuntimeLoading(true);
      setRuntimeError(null);
      const updated = await withAuthRetry((token) =>
        updateAxeProviderRuntime({ provider: providerSelection }, { Authorization: `Bearer ${token}` })
      );
      setProviderRuntime(updated);
      alert(`Provider switched to ${updated.provider}.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Provider switch failed";
      setRuntimeError(message);
      alert(`Provider switch failed: ${message}`);
    } finally {
      setRuntimeLoading(false);
    }
  };

  const handleCreateInvitation = async () => {
    if (!inviteEmail.trim()) return;
    try {
      setAdminLoading(true);
      setAdminError(null);
      await withAuthRetry((token) =>
        createAdminInvitation({ email: inviteEmail.trim(), role: inviteRole }, { Authorization: `Bearer ${token}` })
      );
      setInviteEmail("");
      await loadAdminData();
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : "Failed to create invitation");
    } finally {
      setAdminLoading(false);
    }
  };

  const handleToggleUser = async (target: AdminUser) => {
    try {
      setAdminLoading(true);
      setAdminError(null);
      await withAuthRetry((token) =>
        toggleAdminUserActive(target.id, { Authorization: `Bearer ${token}` })
      );
      await loadAdminData();
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : "Failed to update user status");
    } finally {
      setAdminLoading(false);
    }
  };

  const handleRoleChange = async (target: AdminUser, nextRole: "admin" | "operator" | "viewer") => {
    if (target.role === nextRole) return;
    try {
      setAdminLoading(true);
      setAdminError(null);
      await withAuthRetry((token) =>
        changeAdminUserRole(target.id, nextRole, { Authorization: `Bearer ${token}` })
      );
      await loadAdminData();
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : "Failed to update user role");
    } finally {
      setAdminLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <p className="mb-2 text-[11px] uppercase tracking-[0.2em] text-cyan-300/70">Runtime Control Surface</p>
        <h1 className="axe-surface-title text-3xl font-bold text-white">AXE Configuration</h1>
        <p className="mt-2 text-slate-400">Provider runtime and admin-managed access control.</p>
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">Provider Runtime</h2>
        <p className="mb-4 text-sm text-slate-400">Uses your current authenticated admin session. Manual bearer token input is removed.</p>

        <div className="mb-4 rounded-lg border border-cyan-500/20 bg-slate-900/65 p-3 text-sm text-slate-200">
          Provider credentials, model catalog governance, and policy edits remain in ControlDeck.
          <a href={controlDeckProviderUrl} target="_blank" rel="noreferrer" className="ml-1 text-cyan-300 underline hover:text-cyan-200">
            Open Provider Governance
          </a>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Active Provider</label>
            <select
              value={providerSelection}
              onChange={(e) => setProviderSelection(e.target.value as AxeProvider)}
              className="w-full rounded-lg border border-cyan-500/25 bg-slate-900/70 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-cyan-400"
              disabled={runtimeLoading}
            >
              <option value="openai">OpenAI</option>
              <option value="groq">Groq</option>
              <option value="ollama">Ollama</option>
              <option value="mock">Mock</option>
            </select>
          </div>

          <button
            onClick={() => void applyProviderSelection()}
            disabled={runtimeLoading}
            className="axe-ring rounded-lg bg-cyan-500/80 px-4 py-2 text-slate-950 hover:bg-cyan-400 disabled:opacity-60"
          >
            {runtimeLoading ? "Applying..." : "Apply Provider"}
          </button>

          {providerRuntime && (
            <div className="rounded-lg border border-cyan-500/25 bg-slate-900/75 p-3 text-sm space-y-1">
              <div className="flex justify-between"><span className="text-slate-400">Provider</span><span className="text-white font-mono">{providerRuntime.provider}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Model</span><span className="text-white font-mono">{providerRuntime.model}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">API key</span><span className="text-white font-mono">{providerRuntime.api_key_configured ? "configured" : "missing"}</span></div>
            </div>
          )}

          {runtimeError && <p className="text-sm text-red-400">{runtimeError}</p>}
        </div>
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-4 text-xl font-semibold text-white">User Access (Admin)</h2>
        {!isAdmin && <p className="text-sm text-amber-300">Only admin users can create users and manage roles.</p>}

        {isAdmin && (
          <div className="space-y-6">
            <div className="rounded-lg border border-cyan-500/20 bg-slate-900/70 p-4">
              <h3 className="text-sm font-semibold text-white">Invite user</h3>
              <p className="mt-1 text-xs text-slate-400">User creation is admin-only through invitation links.</p>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(event) => setInviteEmail(event.target.value)}
                  placeholder="new.user@example.com"
                  className="flex-1 rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100"
                />
                <select
                  value={inviteRole}
                  onChange={(event) => setInviteRole(event.target.value as "admin" | "operator" | "viewer")}
                  className="rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100"
                >
                  <option value="operator">operator</option>
                  <option value="viewer">viewer</option>
                  <option value="admin">admin</option>
                </select>
                <button
                  onClick={() => void handleCreateInvitation()}
                  disabled={adminLoading}
                  className="rounded bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60"
                >
                  Create invitation
                </button>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-lg border border-cyan-500/20 bg-slate-900/70 p-4">
                <h3 className="text-sm font-semibold text-white">Users</h3>
                <div className="mt-3 space-y-2 text-xs">
                  {users.map((item) => (
                    <div key={item.id} className="rounded border border-slate-700 p-2">
                      <div className="flex justify-between text-slate-200">
                        <span>{item.email}</span>
                        <span>{item.is_active ? "active" : "inactive"}</span>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <select
                          value={item.role}
                          onChange={(event) => void handleRoleChange(item, event.target.value as "admin" | "operator" | "viewer")}
                          className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs"
                        >
                          <option value="admin">admin</option>
                          <option value="operator">operator</option>
                          <option value="viewer">viewer</option>
                        </select>
                        <button
                          onClick={() => void handleToggleUser(item)}
                          className="rounded border border-cyan-500/30 px-2 py-1 text-xs text-cyan-200"
                        >
                          {item.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-cyan-500/20 bg-slate-900/70 p-4">
                <h3 className="text-sm font-semibold text-white">Pending invitations</h3>
                <div className="mt-3 space-y-2 text-xs text-slate-300">
                  {invitations.length === 0 && <p className="text-slate-500">No pending invitations.</p>}
                  {invitations.map((item) => (
                    <div key={item.id} className="rounded border border-slate-700 p-2">
                      <p>{item.email} ({item.role})</p>
                      <a className="text-cyan-300 break-all" href={item.invitation_url} target="_blank" rel="noreferrer">
                        {item.invitation_url}
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {adminError && <p className="text-sm text-red-400">{adminError}</p>}
          </div>
        )}
      </div>

      <div className="axe-panel rounded-xl p-6">
        <h2 className="axe-surface-title mb-2 text-xl font-semibold text-white">Environment</h2>
        <p className="text-xs text-slate-500">API base: {apiBase}</p>
        <p className="mt-1 text-xs text-slate-500">ControlDeck base: {controlDeckBase}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <a
            href={controlDeckProviderUrl}
            target="_blank"
            rel="noreferrer"
            className="rounded border border-cyan-500/35 bg-cyan-500/10 px-3 py-1 text-cyan-200 hover:bg-cyan-500/20"
          >
            Provider governance (ControlDeck)
          </a>
          <a
            href={controlDeckRoutingUrl}
            target="_blank"
            rel="noreferrer"
            className="rounded border border-amber-400/35 bg-amber-500/10 px-3 py-1 text-amber-200 hover:bg-amber-500/20"
          >
            Routing policy (ControlDeck)
          </a>
        </div>
      </div>
    </div>
  );
}
