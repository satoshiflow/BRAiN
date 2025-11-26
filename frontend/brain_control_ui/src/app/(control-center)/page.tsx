import { DeckTabs } from "@/components/control-center/deck-tabs"
import { KpiRow } from "@/components/control-center/kpi-row"
import { DeckGrid } from "@/components/control-center/deck-grid"

export default function OverviewPage() {
  return (
    <div className="space-y-8">
      <DeckTabs />
      <KpiRow />
      <DeckGrid />
    </div>
  )
}
