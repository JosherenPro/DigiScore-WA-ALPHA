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
  // Chef et CIC atterrissent sur leur espace de revue, pas directement dans la
  // file : ils ont besoin de voir la charge et l'etat du risque avant de signer.
  if (role === "cic" || role === "chef_agence") return "/revue";
  return "/dashboard";
}
