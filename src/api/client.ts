const base = import.meta.env.VITE_API_URL || "/api";

export type UserRole =
  | "ADMIN"
  | "BRANCH_MANAGER"
  | "INVENTORY_CONTROLLER"
  | "STAFF";

export type UserPublic = {
  id: string;
  username: string;
  email: string | null;
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
  let data: T & { detail?: string | { msg: string }[] };
  try {
    data = JSON.parse(text) as T & { detail?: string | { msg: string }[] };
  } catch {
    if (!res.ok) {
      const snippet = text.replace(/\s+/g, " ").slice(0, 180);
      throw new Error(snippet || res.statusText || "Request failed");
    }
    throw new Error("Invalid JSON response");
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((d: { loc?: unknown[]; msg?: string }) => {
                const loc = Array.isArray(d.loc) ? d.loc.filter((x) => x !== "body").join(".") : "";
                return loc ? `${loc}: ${d.msg ?? ""}` : (d.msg ?? "");
              })
              .join("; ")
          : res.statusText;
    throw new Error(message || "Request failed");
  }
  return data;
}

export async function signup(body: {
  username: string;
  password: string;
  role: UserRole;
  email?: string | null;
}): Promise<UserPublic> {
  // Never omit keys: JSON.stringify drops `undefined`, which makes FastAPI report "Field required"
  // for username/password/role even when the UI filled them.
  const payload: Record<string, string> = {
    username: body.username ?? "",
    password: body.password ?? "",
    role: body.role,
  };
  const em = body.email?.trim();
  if (em) payload.email = em;

  const res = await fetch(`${base}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<UserPublic>(res);
}

export async function login(body: {
  username: string;
  password: string;
}): Promise<TokenResponse> {
  const res = await fetch(`${base}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: body.username ?? "",
      password: body.password ?? "",
    }),
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

function buildQuery(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") q.set(k, v);
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

export type DashboardSummary = {
  total_sales: number;
  total_orders: number;
  average_order_value: number;
  low_stock_count: number;
  expiring_soon_count: number;
};

export type SalesTrendPoint = { date: string; sales: number };

export type StorePerformanceRow = {
  store_id: string;
  store_name: string;
  total_sales: number;
  order_count: number;
};

export type StoreBrief = { id: string; name: string };

export type AlertItem = {
  alert_type: string;
  severity: string;
  store_id: string;
  product_id: string;
  product_name: string;
  batch_id: string;
  batch_number: string;
  expiry_date: string | null;
  quantity: number | null;
  reorder_threshold: number | null;
  message: string;
};

export type AlertsResponse = {
  low_stock: AlertItem[];
  expiry: AlertItem[];
};

export async function fetchDashboardSummary(
  token: string,
  params?: { store_id?: string; date_from?: string; date_to?: string },
): Promise<DashboardSummary> {
  const res = await fetch(`${base}/dashboard/summary${buildQuery(params ?? {})}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<DashboardSummary>(res);
}

export async function fetchSalesTrend(
  token: string,
  params: { store_id: string; date_from: string; date_to: string },
): Promise<SalesTrendPoint[]> {
  const res = await fetch(`${base}/dashboard/sales-trend${buildQuery(params)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<SalesTrendPoint[]>(res);
}

export async function fetchStorePerformance(
  token: string,
  params?: { date_from?: string; date_to?: string },
): Promise<StorePerformanceRow[]> {
  const res = await fetch(`${base}/dashboard/store-performance${buildQuery(params ?? {})}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<StorePerformanceRow[]>(res);
}

export async function fetchDashboardStores(token: string): Promise<StoreBrief[]> {
  const res = await fetch(`${base}/dashboard/stores`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<StoreBrief[]>(res);
}

export async function fetchInventoryAlerts(
  token: string,
  params?: { store_id?: string; expiry_days?: string },
): Promise<AlertsResponse> {
  const res = await fetch(`${base}/inventory/alerts${buildQuery(params ?? {})}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<AlertsResponse>(res);
}
