import type { User } from "./api/client";

const USER_KEY = "digiscore_user";
const TOKEN_KEY = "digiscore_token";

export function getUser(): User | null {
  const raw = sessionStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setSession(token: string, user: User) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function homeFor(role: string): string {
  if (role === "cic") return "/cic";
  if (role === "chef_agence") return "/chef";
  return "/dashboard";
}
