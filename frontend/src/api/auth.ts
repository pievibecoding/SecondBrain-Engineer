import { request } from "./client";
import type { TokenResponse, User } from "../types";

export function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: { email, password },
    skipAuth: true
  });
}

export function me(): Promise<User> {
  return request<User>("/api/auth/me");
}
