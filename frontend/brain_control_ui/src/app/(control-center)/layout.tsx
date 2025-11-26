import type { ReactNode } from "react"
import { Header } from "@/components/control-center/header"
import { AxeChatDock } from "@/components/control-center/axe-chat-dock"

export default function ControlCenterLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <main className="min-h-screen bg-gradient-to-b from-brain-bg to-black">
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        <Header />
        {children}
      </div>
      <AxeChatDock />
    </main>
  )
}
