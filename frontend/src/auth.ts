import type { User } from "./api/client";

const KEY = "digiscore_user";

export function getUser(): User | null {
  const raw = sessionStorage.getItem(KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

export function setUser(u: User | null) {
  if (u) sessionStorage.setItem(KEY, JSON.stringify(u));
  else sessionStorage.removeItem(KEY);
}
