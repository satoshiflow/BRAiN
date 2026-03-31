import { fireEvent, render, screen } from "@testing-library/react";

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
          activity_source: "worker_run",
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

  it("renders approval actions for waiting_input approval artifacts", () => {
    const onApprove = jest.fn();
    const onReject = jest.fn();

    render(
      <WorkerRunCard
        update={{
          worker_run_id: "wr-2",
          session_id: "session-1",
          message_id: "message-1",
          worker_type: "miniworker",
          activity_source: "worker_run",
          status: "waiting_input",
          label: "AXE miniworker waiting for approval",
          detail: "Awaiting approval",
          updated_at: new Date().toISOString(),
          artifacts: [
            {
              type: "approval",
              label: "Approval required",
              metadata: { approval_required: true },
            },
          ],
        }}
        onApprove={onApprove}
        onReject={onReject}
      />,
    );

    const textareas = screen.getAllByRole("textbox");
    fireEvent.change(textareas[0], { target: { value: "approved because scoped" } });
    fireEvent.change(textareas[1], { target: { value: "rejected because unsafe" } });

    fireEvent.click(screen.getByRole("button", { name: "Approve apply" }));
    fireEvent.click(screen.getByRole("button", { name: "Reject apply" }));

    expect(onApprove).toHaveBeenCalledWith("wr-2", "approved because scoped");
    expect(onReject).toHaveBeenCalledWith("wr-2", "rejected because unsafe");
    expect(screen.getByText("Approval Panel")).toBeInTheDocument();
    expect(screen.getByText("Policy: approve only if the requested edit is narrow, reviewable, and expected.")).toBeInTheDocument();
    expect(screen.getByText("Risk: bounded_apply can change repository files immediately after approval.")).toBeInTheDocument();
  });

  it("renders approval history when a decision was already recorded", () => {
    render(
      <WorkerRunCard
        update={{
          worker_run_id: "wr-3",
          session_id: "session-1",
          message_id: "message-1",
          worker_type: "miniworker",
          activity_source: "worker_run",
          status: "completed",
          label: "AXE miniworker completed",
          detail: "Patch applied",
          updated_at: new Date().toISOString(),
          artifacts: [
            {
              type: "approval_history",
              label: "Approval recorded",
              metadata: {
                approved: true,
                approval_reason: "Reviewed and approved",
                decided_by: "axe-user",
                decided_at: "2026-03-31T19:00:00+00:00",
              },
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Approval history")).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.getByText("Reviewed and approved")).toBeInTheDocument();
    expect(screen.getByText("Actor: axe-user")).toBeInTheDocument();
    expect(screen.getByText(/^Time:/)).toBeInTheDocument();
  });

  it("renders routing decision metadata when present", () => {
    render(
      <WorkerRunCard
        update={{
          worker_run_id: "wr-4",
          session_id: "session-1",
          message_id: "message-1",
          worker_type: "miniworker",
          activity_source: "worker_run",
          status: "queued",
          label: "BRAiN worker queued",
          detail: "Job accepted by BRAiN orchestrator",
          updated_at: new Date().toISOString(),
          artifacts: [
            {
              type: "routing_decision",
              label: "BRAiN routing decision",
              metadata: {
                routing_decision_id: "route-123",
                selected_worker: "miniworker",
                strategy: "single_worker",
              },
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Routing decision")).toBeInTheDocument();
    expect(screen.getByText("ID: route-123")).toBeInTheDocument();
    expect(screen.getByText("Selected: miniworker")).toBeInTheDocument();
    expect(screen.getByText("Strategy: single_worker")).toBeInTheDocument();
  });

  it("renders runtime source details for openclaw activity", () => {
    render(
      <WorkerRunCard
        update={{
          worker_run_id: "openclaw:task-1",
          session_id: "session-1",
          message_id: "message-1",
          worker_type: "openclaw",
          activity_source: "skillrun_tasklease",
          status: "running",
          label: "OpenClaw task running",
          detail: "Lease active",
          updated_at: new Date().toISOString(),
          artifacts: [
            {
              type: "runtime_source",
              label: "Runtime source",
              metadata: {
                source: "skillrun_tasklease",
                task_id: "task-1",
                skill_run_id: "sr-1",
              },
            },
          ],
        }}
      />,
    );

    expect(screen.getAllByText("Runtime source")).toHaveLength(2);
    expect(screen.getByText("Source: skillrun_tasklease")).toBeInTheDocument();
    expect(screen.getByText("Task: task-1")).toBeInTheDocument();
    expect(screen.getByText("SkillRun: sr-1")).toBeInTheDocument();
  });
});
