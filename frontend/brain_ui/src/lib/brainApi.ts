export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type ChatResponse = {
  reply: string;
};

const BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_BASE || "http://localhost:8000";

export async function sendChat(messages: ChatMessage[]): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ messages })
  });

  if (!res.ok) {
    throw new Error(`Chat request failed with status ${res.status}`);
  }

  return res.json();
}
