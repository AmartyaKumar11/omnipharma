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
  store_id?: string | null;
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
  store_id?: string | null;
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
  if (body.store_id) payload.store_id = body.store_id;

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

// —— Inventory ——

export type ProductPublic = {
  id: string;
  name: string;
  generic_name: string | null;
  category: string | null;
  manufacturer: string | null;
  description: string | null;
  is_prescription_required: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
};

export type BatchPublic = {
  id: string;
  product_id: string;
  batch_number: string;
  expiry_date: string;
  manufacture_date: string | null;
  purchase_price: string | null;
  selling_price: string | null;
  created_at: string;
  updated_at: string;
};

export type InventoryRowPublic = {
  inventory_id: string;
  store_id: string;
  product: ProductPublic;
  batch: BatchPublic;
  quantity: number;
  reserved_quantity: number;
  reorder_threshold: number | null;
  last_restocked_at: string | null;
};

export type InventoryLogRow = {
  id: string;
  username: string | null;
  change_type: string;
  source_type: string;
  product_name: string;
  batch_number: string;
  quantity_changed: number;
  reason: string | null;
  created_at: string;
};

export async function fetchInventoryRows(
  token: string,
  params?: {
    store_id?: string;
    product_id?: string;
    sort_by?: "expiry_date" | "quantity";
    sort_dir?: "asc" | "desc";
  },
): Promise<InventoryRowPublic[]> {
  const res = await fetch(`${base}/inventory${buildQuery(params as Record<string, string | undefined>)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<InventoryRowPublic[]>(res);
}

export async function postInventoryAdjust(
  token: string,
  body: { store_id: string; batch_id: string; quantity_delta: number; reason?: string | null },
): Promise<{ status: string; inventory_id: string }> {
  const res = await fetch(`${base}/inventory/adjust`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson(res);
}

export async function fetchInventoryLogs(token: string, limit?: number): Promise<InventoryLogRow[]> {
  const res = await fetch(
    `${base}/inventory/logs${buildQuery(limit ? { limit: String(limit) } : {})}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  return parseJson<InventoryLogRow[]>(res);
}

export async function postInventoryStock(
  token: string,
  body: { store_id: string; batch_id: string; quantity: number },
): Promise<{ status: string; inventory_id: string }> {
  const res = await fetch(`${base}/inventory/stock`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson(res);
}

// —— Orders ——

export type PaymentMethod = "CASH" | "CARD" | "UPI";
export type OrderType = "OTC" | "PRESCRIPTION";

export type OrderLineIn = { product_id: string; quantity: number };

export type OrderItemOut = {
  id: string;
  product_id: string;
  product_name: string;
  batch_id: string;
  batch_number: string;
  quantity: number;
  price_at_sale: string;
  line_total: string;
};

export type OrderOut = {
  id: string;
  order_number: string;
  store_id: string;
  user_id: string;
  order_type: string;
  status: string;
  total_amount: string;
  payment_method: string;
  notes: string | null;
  created_at: string;
  items: OrderItemOut[];
};

export async function fetchOrders(
  token: string,
  params?: { store_id?: string; date_from?: string; date_to?: string },
): Promise<OrderOut[]> {
  const res = await fetch(`${base}/orders${buildQuery(params ?? {})}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<OrderOut[]>(res);
}

export async function fetchOrder(token: string, orderId: string): Promise<OrderOut> {
  const res = await fetch(`${base}/orders/${orderId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJson<OrderOut>(res);
}

export async function createOrder(
  token: string,
  body: {
    store_id: string;
    items: OrderLineIn[];
    payment_method: PaymentMethod;
    order_type?: OrderType;
    prescription_file_url?: string | null;
    doctor_name?: string | null;
    prescription_notes?: string | null;
    notes?: string | null;
  },
): Promise<OrderOut> {
  const res = await fetch(`${base}/orders`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      store_id: body.store_id,
      items: body.items,
      payment_method: body.payment_method,
      order_type: body.order_type ?? "OTC",
      prescription_file_url: body.prescription_file_url,
      doctor_name: body.doctor_name,
      prescription_notes: body.prescription_notes,
      notes: body.notes,
    }),
  });
  return parseJson<OrderOut>(res);
}
