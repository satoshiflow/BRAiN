import { NextRequest, NextResponse } from "next/server"
import { callLocalOllamaLLM, type ChatMessage } from "@/lib/llm"

export const runtime = "nodejs"

type AxeRequestBody = {
  message: string
  history?: ChatMessage[]
}

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as AxeRequestBody

    if (!body.message || typeof body.message !== "string") {
      return NextResponse.json(
        { error: "Missing 'message' in body" },
        { status: 400 }
      )
    }

    const messages: ChatMessage[] = [
      {
        role: "system",
        content:
          "Du bist AXE, ein ruhiger, technischer Assistent für das BRAIN Control Center. " +
          "Antworte kurz, klar und deutsch. Hilf bei der Bedienung des Dashboards, " +
          "erkläre Funktionen, aber führe keine gefährlichen Aktionen aus. " +
          "Wenn dir Infos fehlen, sag es offen und schlage nächste Schritte vor.",
      },
    ]

    if (Array.isArray(body.history)) {
      const safeHistory = body.history.slice(-6)
      messages.push(...safeHistory)
    }

    messages.push({
      role: "user",
      content: body.message,
    })

    const reply = await callLocalOllamaLLM(messages)

    return NextResponse.json({
      reply,
    })
  } catch (err: any) {
    console.error("AXE API error:", err)
    return NextResponse.json(
      {
        error: "AXE backend error",
        details: err?.message ?? "unknown",
      },
      { status: 500 }
    )
  }
}
