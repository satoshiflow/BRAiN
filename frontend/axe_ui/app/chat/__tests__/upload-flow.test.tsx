import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import ChatPage from "@/app/chat/page";
import { appendAxeSessionMessage, getAxeWorkerRun, postAxeChat, uploadAxeAttachment } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  postAxeChat: jest.fn(),
  uploadAxeAttachment: jest.fn(),
  appendAxeSessionMessage: jest.fn(),
  getAxeWorkerRun: jest.fn(),
}));

jest.mock("@/components/auth/AuthGate", () => ({
  AuthGate: ({ children }: { children: ReactNode }) => children,
}));

jest.mock("@/hooks/useAuthSession", () => ({
  useAuthSession: () => ({
    accessToken: "test-token",
    withAuthRetry: async <T,>(request: (token: string) => Promise<T>) => request("test-token"),
  }),
}));

const mockedActiveSession = { id: "session-1", title: "Session", messages: [] };
const mockedLoadSessions = jest.fn().mockResolvedValue(undefined);
const mockedCreateSession = jest.fn().mockResolvedValue({ id: "session-1" });
const mockedSelectSession = jest.fn().mockResolvedValue(mockedActiveSession);
const mockedRenameSession = jest.fn().mockResolvedValue(null);
const mockedRemoveSession = jest.fn().mockResolvedValue(true);

jest.mock("@/hooks/useChatSessions", () => ({
  useChatSessions: () => ({
    groupedSessions: { today: [], yesterday: [], older: [] },
    activeSessionId: "session-1",
    activeSession: mockedActiveSession,
    loading: false,
    error: null,
    loadSessions: mockedLoadSessions,
    createSession: mockedCreateSession,
    selectSession: mockedSelectSession,
    renameSession: mockedRenameSession,
    removeSession: mockedRemoveSession,
  }),
}));

jest.mock("@/src/plugins", () => ({
  pluginRegistry: {
    register: jest.fn(),
    renderUiSlot: jest.fn(() => []),
    handleCommand: jest.fn(),
  },
  initializePlugins: jest.fn().mockResolvedValue(undefined),
  destroyPlugins: jest.fn().mockResolvedValue(undefined),
}));

jest.mock("@/src/plugins/slashCommands", () => ({
  __esModule: true,
  default: {},
}));

const mockedUpload = uploadAxeAttachment as jest.MockedFunction<typeof uploadAxeAttachment>;
const mockedChat = postAxeChat as jest.MockedFunction<typeof postAxeChat>;
const mockedAppendMessage = appendAxeSessionMessage as jest.MockedFunction<typeof appendAxeSessionMessage>;
const mockedGetWorkerRun = getAxeWorkerRun as jest.MockedFunction<typeof getAxeWorkerRun>;

describe("chat upload flow", () => {
  beforeEach(() => {
    mockedUpload.mockReset();
    mockedChat.mockReset();
    mockedAppendMessage.mockReset();
    mockedGetWorkerRun.mockReset();
    mockedLoadSessions.mockClear();
    mockedCreateSession.mockClear();
    mockedSelectSession.mockClear();
    mockedRenameSession.mockClear();
    mockedRemoveSession.mockClear();
    mockedAppendMessage.mockResolvedValue({
      id: "msg-1",
      session_id: "session-1",
      role: "user",
      content: "placeholder",
      attachments: [],
      metadata: {},
      created_at: new Date().toISOString(),
    });
    mockedGetWorkerRun.mockResolvedValue({
      worker_run_id: "worker-1",
      session_id: "session-1",
      message_id: "msg-1",
      worker_type: "opencode",
      status: "completed",
      label: "OpenCode worker completed",
      detail: "Finished successfully",
      updated_at: new Date().toISOString(),
      artifacts: [],
    });
    window.confirm = jest.fn(() => true);
  });

  it("uploads file and sends chat request with attachment id", async () => {
    mockedUpload.mockResolvedValue({
      attachment_id: "att-1",
      filename: "screenshot.png",
      mime_type: "image/png",
      size_bytes: 1024,
      expires_at: "2099-01-01T00:00:00Z",
    });
    mockedChat.mockResolvedValue({ text: "ok", raw: {} });

    const { container } = render(<ChatPage />);
    const fileInput = container.querySelector(
      'input[type="file"][accept*="application/pdf"]'
    ) as HTMLInputElement;

    const file = new File(["abc"], "screenshot.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await screen.findByText("ready");

    fireEvent.change(screen.getByPlaceholderText("Type your message..."), {
      target: { value: "Bitte prüfen" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    await waitFor(() => {
      expect(mockedChat).toHaveBeenCalledWith(
        expect.objectContaining({
          attachments: ["att-1"],
        }),
        expect.objectContaining({ Authorization: "Bearer test-token" })
      );
    });
  });

  it("shows failed uploads and asks for confirmation before sending", async () => {
    mockedUpload.mockRejectedValue(new Error("Upload failed"));
    mockedChat.mockResolvedValue({ text: "sent without file", raw: {} });

    const { container } = render(<ChatPage />);
    const fileInput = container.querySelector(
      'input[type="file"][accept*="application/pdf"]'
    ) as HTMLInputElement;

    const file = new File(["abc"], "broken.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await screen.findByText("error");
    expect(screen.getByRole("button", { name: "Clear failed uploads" })).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Type your message..."), {
      target: { value: "Nachricht ohne Datei" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(mockedChat).toHaveBeenCalledWith(
        expect.objectContaining({
          attachments: [],
        }),
        expect.objectContaining({ Authorization: "Bearer test-token" })
      );
    });
  });

  it("renders an optional worker status card when chat response includes worker metadata", async () => {
    mockedChat.mockResolvedValue({
      text: "ok",
      raw: {},
      worker_run_id: "worker-1",
      session_id: "session-1",
      message_id: "msg-1",
    });

    render(<ChatPage />);

    fireEvent.change(screen.getByPlaceholderText("Type your message..."), {
      target: { value: "Starte Worker bitte" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("BRAiN worker queued")).toBeInTheDocument();
    expect(screen.getByText("BRAiN delegated this request to a worker. Awaiting status updates.")).toBeInTheDocument();
  });

  it("renders openclaw worker activity as non-polling external worker update", async () => {
    mockedChat.mockResolvedValue({
      text: "[OPENCLAW via SkillRun/TaskLease]",
      raw: {
        worker_type: "openclaw",
        task_id: "task-openclaw-1",
        skill_run_id: "sr-openclaw-1",
      },
      session_id: "session-1",
      message_id: "msg-1",
    });

    render(<ChatPage />);

    fireEvent.change(screen.getByPlaceholderText("Type your message..."), {
      target: { value: "/openclaw run test" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("OpenClaw task dispatched")).toBeInTheDocument();
    expect(screen.getByText("openclaw (1)")).toBeInTheDocument();
    expect(mockedGetWorkerRun).not.toHaveBeenCalled();
  });

  it("allows filtering worker cards by status", async () => {
    mockedChat.mockResolvedValue({
      text: "ok",
      raw: {},
      worker_run_id: "worker-1",
      session_id: "session-1",
      message_id: "msg-1",
    });

    mockedGetWorkerRun.mockResolvedValue({
      worker_run_id: "worker-1",
      session_id: "session-1",
      message_id: "msg-1",
      worker_type: "opencode",
      status: "completed",
      label: "OpenCode worker completed",
      detail: "Finished successfully",
      updated_at: new Date().toISOString(),
      artifacts: [],
    });

    render(<ChatPage />);

    fireEvent.change(screen.getByPlaceholderText("Type your message..."), {
      target: { value: "Run worker" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText("BRAiN worker queued")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /failed \(/i }));
    expect(screen.queryByText("BRAiN worker queued")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /queued \(/i }));
    expect(screen.getByText("BRAiN worker queued")).toBeInTheDocument();
  });
});
