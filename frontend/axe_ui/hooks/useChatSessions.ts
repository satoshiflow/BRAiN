"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createAxeSession,
  deleteAxeSession,
  getAxeSession,
  listAxeSessions,
  updateAxeSession,
} from "@/lib/api";
import type { AxeSessionDetail, AxeSessionSummary } from "@/lib/contracts";

function startOfDay(date: Date): number {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  return copy.getTime();
}

function timestamp(value?: string | null): number {
  if (!value) {
    return 0;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export type GroupedSessions = {
  today: AxeSessionSummary[];
  yesterday: AxeSessionSummary[];
  older: AxeSessionSummary[];
};

type UseChatSessionsOptions = {
  headers?: Record<string, string>;
  withAuthRetry?: <T>(request: (token: string) => Promise<T>) => Promise<T>;
};

export function useChatSessions({ headers, withAuthRetry }: UseChatSessionsOptions) {
  const [sessions, setSessions] = useState<AxeSessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<AxeSessionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const headersRef = useRef(headers);
  const withAuthRetryRef = useRef(withAuthRetry);

  useEffect(() => {
    headersRef.current = headers;
    withAuthRetryRef.current = withAuthRetry;
  }, [headers, withAuthRetry]);

  const withAuthorization = useCallback(
    async <T,>(request: (authHeaders?: Record<string, string>) => Promise<T>): Promise<T> => {
      if (withAuthRetryRef.current) {
        return withAuthRetryRef.current((token) => request({ Authorization: `Bearer ${token}` }));
      }
      return request(headersRef.current);
    },
    []
  );

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await withAuthorization((authHeaders) => listAxeSessions(authHeaders));
      setSessions(list);
      if (!activeSessionId && list.length > 0) {
        setActiveSessionId(list[0].id);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, [activeSessionId, withAuthorization]);

  const createSession = useCallback(async (title?: string): Promise<AxeSessionSummary | null> => {
    setError(null);
    try {
      const created = await withAuthorization((authHeaders) => createAxeSession({ title }, authHeaders));
      setSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.id);
      setActiveSession({
        ...created,
        messages: [],
      });
      return created;
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Failed to create session");
      return null;
    }
  }, [withAuthorization]);

  const selectSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const detail = await withAuthorization((authHeaders) => getAxeSession(sessionId, authHeaders));
      setActiveSessionId(sessionId);
      setActiveSession(detail);
      return detail;
    } catch (sessionError) {
      setError(sessionError instanceof Error ? sessionError.message : "Failed to load session");
      return null;
    } finally {
      setLoading(false);
    }
  }, [withAuthorization]);

  const renameSession = useCallback(async (sessionId: string, title: string) => {
    setError(null);
    try {
      const updated = await withAuthorization((authHeaders) =>
        updateAxeSession(sessionId, { title }, authHeaders)
      );
      setSessions((prev) => prev.map((item) => (item.id === sessionId ? updated : item)));
      setActiveSession((prev) => (prev && prev.id === sessionId ? { ...prev, title: updated.title } : prev));
      return updated;
    } catch (renameError) {
      setError(renameError instanceof Error ? renameError.message : "Failed to rename session");
      return null;
    }
  }, [withAuthorization]);

  const removeSession = useCallback(async (sessionId: string) => {
    setError(null);
    try {
      await withAuthorization((authHeaders) => deleteAxeSession(sessionId, authHeaders));
      setSessions((prev) => prev.filter((item) => item.id !== sessionId));

      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setActiveSession(null);
      }
      return true;
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Failed to delete session");
      return false;
    }
  }, [activeSessionId, withAuthorization]);

  const groupedSessions = useMemo<GroupedSessions>(() => {
    const now = new Date();
    const todayStart = startOfDay(now);
    const yesterdayStart = todayStart - 24 * 60 * 60 * 1000;

    const sorted = [...sessions].sort((a, b) => {
      return timestamp(b.last_message_at || b.updated_at) - timestamp(a.last_message_at || a.updated_at);
    });

    return sorted.reduce<GroupedSessions>(
      (acc, session) => {
        const updated = timestamp(session.last_message_at || session.updated_at || session.created_at);
        if (updated >= todayStart) {
          acc.today.push(session);
        } else if (updated >= yesterdayStart) {
          acc.yesterday.push(session);
        } else {
          acc.older.push(session);
        }
        return acc;
      },
      {
        today: [],
        yesterday: [],
        older: [],
      }
    );
  }, [sessions]);

  return {
    sessions,
    groupedSessions,
    activeSessionId,
    activeSession,
    loading,
    error,
    loadSessions,
    createSession,
    selectSession,
    renameSession,
    removeSession,
    setActiveSession,
    setSessions,
  };
}
