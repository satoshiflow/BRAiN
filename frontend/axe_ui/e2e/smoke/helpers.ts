import type { Page, Route } from "@playwright/test";

type SessionRecord = {
  id: string;
  title: string;
  preview: string | null;
  status: "active" | "deleted";
  message_count: number;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
  messages: Array<{
    id: string;
    session_id: string;
    role: "user" | "assistant";
    content: string;
    attachments: string[];
    metadata: Record<string, unknown>;
    created_at: string;
  }>;
};

function nowIso(): string {
  return new Date().toISOString();
}

function jsonResponse(route: Route, payload: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

export async function mockBackend(page: Page) {
  const sessions = new Map<string, SessionRecord>();
  const tokenPair = {
    access_token: "e2e-access-token",
    refresh_token: "e2e-refresh-token",
    token_type: "bearer",
    expires_in: 900,
  };

  await page.route("**/api/health", (route) => jsonResponse(route, { status: "ok", version: "e2e" }));

  await page.route("**/api/auth/login", async (route) => {
    const postData = route.request().postDataJSON() as { email?: string; password?: string };
    if (!postData?.email || !postData?.password) {
      return jsonResponse(route, { detail: "Invalid credentials" }, 401);
    }
    return jsonResponse(route, tokenPair);
  });

  await page.route("**/api/auth/me", (route) =>
    jsonResponse(route, {
      id: "11111111-1111-1111-1111-111111111111",
      email: "e2e@brain.local",
      username: "e2e-user",
      full_name: "E2E User",
      role: "operator",
      is_active: true,
      is_verified: true,
      created_at: nowIso(),
      last_login: nowIso(),
    })
  );

  await page.route("**/api/auth/refresh", (route) => jsonResponse(route, tokenPair));
  await page.route("**/api/auth/logout", (route) => route.fulfill({ status: 204 }));

  await page.route("**/api/axe/upload", async (route) => {
    return jsonResponse(route, {
      attachment_id: `att-${Date.now()}`,
      filename: "upload.png",
      mime_type: "image/png",
      size_bytes: 1024,
      expires_at: nowIso(),
    }, 201);
  });

  await page.route("**/api/axe/chat", async (route) => {
    const body = route.request().postDataJSON() as { messages?: Array<{ role: string; content: string }> };
    const latest = body.messages?.[body.messages.length - 1]?.content || "";
    return jsonResponse(route, { text: `Echo: ${latest}`, raw: { source: "e2e" } });
  });

  await page.route("**/api/axe/sessions", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      const list = Array.from(sessions.values())
        .filter((session) => session.status === "active")
        .sort((a, b) => (b.last_message_at || b.updated_at).localeCompare(a.last_message_at || a.updated_at))
        .map(({ messages, ...summary }) => summary);
      return jsonResponse(route, list);
    }

    if (method === "POST") {
      const body = route.request().postDataJSON() as { title?: string };
      const id = `session-${Date.now()}`;
      const createdAt = nowIso();
      const session: SessionRecord = {
        id,
        title: body?.title || "New Chat",
        preview: null,
        status: "active",
        message_count: 0,
        created_at: createdAt,
        updated_at: createdAt,
        last_message_at: null,
        messages: [],
      };
      sessions.set(id, session);
      const { messages, ...summary } = session;
      return jsonResponse(route, summary, 201);
    }

    return jsonResponse(route, { detail: "Unsupported" }, 405);
  });

  await page.route("**/api/axe/sessions/**", async (route) => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split("/").filter(Boolean);
    const sessionId = parts[parts.indexOf("sessions") + 1];
    const session = sessionId ? sessions.get(sessionId) : undefined;

    if (!session || session.status !== "active") {
      return jsonResponse(route, { detail: "Session not found" }, 404);
    }

    const method = route.request().method();

    if (parts.at(-1) === "messages" && method === "POST") {
      const body = route.request().postDataJSON() as {
        role: "user" | "assistant";
        content: string;
        attachments?: string[];
        metadata?: Record<string, unknown>;
      };
      const message = {
        id: `msg-${Date.now()}`,
        session_id: session.id,
        role: body.role,
        content: body.content,
        attachments: body.attachments || [],
        metadata: body.metadata || {},
        created_at: nowIso(),
      };
      session.messages.push(message);
      session.message_count += 1;
      session.preview = body.content.slice(0, 120);
      session.last_message_at = message.created_at;
      session.updated_at = message.created_at;
      if (session.message_count === 1 && body.role === "user" && session.title === "New Chat") {
        session.title = body.content.slice(0, 60);
      }
      return jsonResponse(route, message, 201);
    }

    if (method === "GET") {
      return jsonResponse(route, session);
    }

    if (method === "PATCH") {
      const body = route.request().postDataJSON() as { title: string };
      session.title = body.title;
      session.updated_at = nowIso();
      const { messages, ...summary } = session;
      return jsonResponse(route, summary);
    }

    if (method === "DELETE") {
      session.status = "deleted";
      session.updated_at = nowIso();
      return route.fulfill({ status: 204 });
    }

    return jsonResponse(route, { detail: "Unsupported" }, 405);
  });
}

export async function loginAxe(page: Page) {
  await page.goto("/chat");
  const signInButton = page.getByRole("button", { name: "Sign in" });
  if (await signInButton.isVisible()) {
    await page.getByLabel("Email").fill("e2e@brain.local");
    await page.getByLabel("Password").fill("brainpass123");
    await signInButton.click();
  }
  await page.getByPlaceholder("Type your message...").waitFor({ state: "visible" });
}
