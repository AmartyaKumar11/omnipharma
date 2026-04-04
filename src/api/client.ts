const base = import.meta.env.VITE_API_URL || "/api";

export type UserRole =
  | "ADMIN"
  | "BRANCH_MANAGER"
  | "INVENTORY_CONTROLLER"
  | "STAFF";

export type UserPublic = {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  if (!text) {
    if (!res.ok) throw new Error(res.statusText || "Request failed");
    return {} as T;
  }
  const data = JSON.parse(text) as T & { detail?: string | { msg: string }[] };
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(", ")
          : res.statusText;
    throw new Error(message || "Request failed");
  }
  return data;
}

export async function signup(body: {
  email: string;
  password: string;
  role: UserRole;
}): Promise<UserPublic> {
  const res = await fetch(`${base}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson<UserPublic>(res);
}

export async function login(body: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  const res = await fetch(`${base}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson<TokenResponse>(res);
}

export async function fetchMe(token: string): Promise<UserPublic> {
  const res = await fetch(`${base}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<UserPublic>(res);
}

export async function fetchAdminPing(token: string): Promise<{ message: string }> {
  const res = await fetch(`${base}/auth/admin/ping`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<{ message: string }>(res);
}
