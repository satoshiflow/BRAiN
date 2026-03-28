import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";

import { AuthApiError } from "@/lib/auth";
import { AuthSessionProvider, useAuthSession } from "@/hooks/useAuthSession";
import {
  fetchCurrentUser,
  login,
  logout,
  refreshAccessToken,
} from "@/lib/auth";

jest.mock("@/lib/auth", () => {
  const actual = jest.requireActual("@/lib/auth");
  return {
    ...actual,
    login: jest.fn(),
    logout: jest.fn(),
    refreshAccessToken: jest.fn(),
    fetchCurrentUser: jest.fn(),
  };
});

const mockedLogin = login as jest.MockedFunction<typeof login>;
const mockedLogout = logout as jest.MockedFunction<typeof logout>;
const mockedRefresh = refreshAccessToken as jest.MockedFunction<typeof refreshAccessToken>;
const mockedFetchCurrentUser = fetchCurrentUser as jest.MockedFunction<typeof fetchCurrentUser>;

function Harness({ request }: { request: (token: string) => Promise<string> }) {
  const auth = useAuthSession();

  return (
    <>
      <div data-testid="status">{auth.status}</div>
      <div data-testid="user">{auth.user?.email ?? ""}</div>
      <button onClick={() => void auth.login("operator@example.com", "secretpass")}>login</button>
      <button onClick={() => void auth.logout()}>logout</button>
      <button
        onClick={() => {
          void auth.withAuthRetry(request).then(
            (value) => {
              (window as Window & { __authResult?: string }).__authResult = value;
            },
            (error: Error) => {
              (window as Window & { __authError?: string }).__authError = error.message;
            }
          );
        }}
      >
        retry
      </button>
    </>
  );
}

function renderHarness(request: (token: string) => Promise<string>) {
  return render(
    <AuthSessionProvider>
      <Harness request={request} />
    </AuthSessionProvider>
  );
}

describe("AuthSessionProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockedLogin.mockReset();
    mockedLogout.mockReset();
    mockedRefresh.mockReset();
    mockedFetchCurrentUser.mockReset();
    delete (window as Window & { __authResult?: string }).__authResult;
    delete (window as Window & { __authError?: string }).__authError;

    mockedLogin.mockResolvedValue({
      access_token: "access-token-1",
      refresh_token: "refresh-token-1",
      token_type: "bearer",
      expires_in: 900,
    });
    mockedFetchCurrentUser.mockResolvedValue({
      id: "user-1",
      email: "operator@example.com",
      username: "operator",
      full_name: "Operator",
      role: "operator",
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
      last_login: new Date().toISOString(),
    });
  });

  it("marks the session authenticated after login", async () => {
    renderHarness(async (token) => token);

    fireEvent.click(screen.getByRole("button", { name: "login" }));

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
      expect(screen.getByTestId("user")).toHaveTextContent("operator@example.com");
    });
  });

  it("retries with a refreshed token when the request fails with 401", async () => {
    const request = jest
      .fn<Promise<string>, [string]>()
      .mockRejectedValueOnce(new AuthApiError(401, '{"detail":"Invalid token"}'))
      .mockResolvedValueOnce("ok-after-refresh");

    mockedRefresh.mockResolvedValue({
      access_token: "access-token-2",
      refresh_token: "refresh-token-2",
      token_type: "bearer",
      expires_in: 900,
    });

    renderHarness(request);

    fireEvent.click(screen.getByRole("button", { name: "login" }));
    await screen.findByText("authenticated");

    fireEvent.click(screen.getByRole("button", { name: "retry" }));

    await waitFor(() => {
      expect(request).toHaveBeenNthCalledWith(1, "access-token-1");
      expect(request).toHaveBeenNthCalledWith(2, "access-token-2");
      expect((window as Window & { __authResult?: string }).__authResult).toBe("ok-after-refresh");
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    });
  });

  it("clears auth state when refresh fails after a 401 response", async () => {
    const request = jest
      .fn<Promise<string>, [string]>()
      .mockRejectedValueOnce(new AuthApiError(401, '{"detail":"Expired"}'));

    mockedRefresh.mockRejectedValue(new AuthApiError(401, '{"detail":"Refresh expired"}'));

    renderHarness(request);

    fireEvent.click(screen.getByRole("button", { name: "login" }));
    await screen.findByText("authenticated");

    fireEvent.click(screen.getByRole("button", { name: "retry" }));

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
      expect(screen.getByTestId("user")).toHaveTextContent("");
      expect((window as Window & { __authError?: string }).__authError).toContain("Refresh expired");
    });
  });

  it("always clears local auth state on logout even if backend revoke fails", async () => {
    mockedLogout.mockRejectedValue(new Error("backend unavailable"));

    renderHarness(async (token) => token);

    fireEvent.click(screen.getByRole("button", { name: "login" }));
    await screen.findByText("authenticated");

    fireEvent.click(screen.getByRole("button", { name: "logout" }));

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
      expect(screen.getByTestId("user")).toHaveTextContent("");
    });
  });
});
