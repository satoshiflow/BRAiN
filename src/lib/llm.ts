const OLLAMA_HOST = process.env.OLLAMA_HOST || "http://127.0.0.1:11434"
const DEFAULT_MODEL = process.env.LLM_DEFAULT_MODEL || "phi3"

export type ChatMessage = {
  role: "system" | "user" | "assistant"
  content: string
}

export async function callLocalOllamaLLM(
  messages: ChatMessage[],
  options?: { model?: string }
): Promise<string> {
  const model = options?.model || DEFAULT_MODEL

  const res = await fetch(`${OLLAMA_HOST}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages,
      stream: false,
    }),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    console.error("Ollama error:", res.status, text)
    throw new Error(`Ollama request failed: ${res.status}`)
  }

  const data = (await res.json()) as {
    message?: { content?: string }
  }

  const content = data?.message?.content?.trim()
  if (!content) {
    throw new Error("Ollama returned empty response")
  }

  return content
}
