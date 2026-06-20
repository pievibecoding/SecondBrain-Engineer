import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./AuthContext";
import { useAuth } from "../hooks/useAuth";

vi.mock("../api/auth", () => ({
  login: async () => ({
    access_token: "token",
    token_type: "bearer",
    user: { id: "u1", username: "Admin", email: "admin@robolinks.vn", role: "admin" }
  })
}));

describe("AuthContext", () => {
  it("handles login and logout", async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => <AuthProvider>{children}</AuthProvider>;
    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {
      await result.current.login("admin@robolinks.vn", "password123");
    });
    expect(result.current.currentUser?.email).toBe("admin@robolinks.vn");
    expect(result.current.isAdmin).toBe(true);
    act(() => result.current.logout());
    expect(result.current.currentUser).toBeNull();
  });
});
