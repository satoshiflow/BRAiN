import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ChatPage from "@/app/chat/page";
import { postAxeChat, uploadAxeAttachment } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  postAxeChat: jest.fn(),
  uploadAxeAttachment: jest.fn(),
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

describe("chat upload flow", () => {
  beforeEach(() => {
    mockedUpload.mockReset();
    mockedChat.mockReset();
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
        })
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
        })
      );
    });
  });
});
