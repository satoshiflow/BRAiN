import { render, screen } from "@testing-library/react";

import { WorkerRunCard } from "@/components/chat/WorkerRunCard";

describe("WorkerRunCard", () => {
  it("renders patch artifacts in diff-style rows", () => {
    render(
      <WorkerRunCard
        update={{
          worker_run_id: "wr-1",
          session_id: "session-1",
          message_id: "message-1",
          worker_type: "miniworker",
          status: "completed",
          label: "AXE miniworker completed",
          detail: "Patch proposal ready",
          updated_at: new Date().toISOString(),
          artifacts: [
            {
              type: "patch",
              label: "AXE miniworker patch proposal",
              content: "@@ block\n-old line\n+new line",
            },
          ],
        }}
      />,
    );

    expect(screen.getAllByText("AXE miniworker patch proposal")).toHaveLength(2);
    expect(screen.getByText("-old line")).toBeInTheDocument();
    expect(screen.getByText("+new line")).toBeInTheDocument();
  });
});
