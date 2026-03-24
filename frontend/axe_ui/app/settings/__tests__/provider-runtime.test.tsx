import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SettingsPage from "@/app/settings/page";
import { getAxeProviderRuntime, updateAxeProviderRuntime } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  getAxeProviderRuntime: jest.fn(),
  updateAxeProviderRuntime: jest.fn(),
}));

const mockedGetRuntime = getAxeProviderRuntime as jest.MockedFunction<typeof getAxeProviderRuntime>;
const mockedUpdateRuntime = updateAxeProviderRuntime as jest.MockedFunction<typeof updateAxeProviderRuntime>;

describe("provider runtime settings", () => {
  beforeEach(() => {
    mockedGetRuntime.mockReset();
    mockedUpdateRuntime.mockReset();

    mockedGetRuntime.mockResolvedValue({
      provider: "mock",
      base_url: "http://127.0.0.1:11434",
      model: "mock-model",
      timeout_seconds: 30,
      sanitization_level: "moderate",
      api_key_configured: false,
    });

    window.alert = jest.fn();
    window.confirm = jest.fn(() => true);
  });

  it("loads provider runtime on mount", async () => {
    render(<SettingsPage />);

    await screen.findByText("mock-model");
    expect(mockedGetRuntime).toHaveBeenCalledTimes(1);
  });

  it("does not update runtime when confirmation is cancelled", async () => {
    (window.confirm as jest.Mock).mockReturnValue(false);
    render(<SettingsPage />);

    await screen.findByText("mock-model");
    fireEvent.click(screen.getByRole("button", { name: "Apply Provider" }));

    expect(mockedUpdateRuntime).not.toHaveBeenCalled();
  });

  it("applies provider update with bearer token header", async () => {
    mockedUpdateRuntime.mockResolvedValue({
      provider: "groq",
      base_url: "https://api.groq.com/openai/v1",
      model: "llama-3",
      timeout_seconds: 30,
      sanitization_level: "moderate",
      api_key_configured: true,
    });

    render(<SettingsPage />);
    await screen.findByText("mock-model");

    fireEvent.change(screen.getByPlaceholderText("eyJ..."), {
      target: { value: "token-123" },
    });
    const providerSelect = screen
      .getByText("Active Provider")
      .parentElement?.querySelector("select") as HTMLSelectElement;
    fireEvent.change(providerSelect, {
      target: { value: "groq" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply Provider" }));

    await waitFor(() => {
      expect(mockedUpdateRuntime).toHaveBeenCalledWith(
        { provider: "groq" },
        { Authorization: "Bearer token-123" }
      );
    });
  });

  it("clears token input when clear token is clicked", async () => {
    render(<SettingsPage />);
    const tokenInput = screen.getByPlaceholderText("eyJ...") as HTMLInputElement;

    fireEvent.change(tokenInput, { target: { value: "sensitive-token" } });
    fireEvent.click(screen.getByRole("button", { name: "Clear token" }));

    expect(tokenInput.value).toBe("");
  });
});
