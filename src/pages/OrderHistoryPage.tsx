import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RoleGate } from "@/components/RoleGate";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/auth/AuthContext";
import type { OrderOut } from "@/api/client";
import { fetchDashboardStores, fetchOrder, fetchOrders } from "@/api/client";

function formatMoney(s: string): string {
  const n = Number.parseFloat(s);
  if (Number.isNaN(n)) return s;
  return new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

export function OrderHistoryPage() {
  const { token, user, loading: authLoading } = useAuth();
  const [stores, setStores] = useState<{ id: string; name: string }[]>([]);
  const [storeFilter, setStoreFilter] = useState("");
  const [productFilter, setProductFilter] = useState("");
  const [orders, setOrders] = useState<OrderOut[]>([]);
  const [listBusy, setListBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [detailId, setDetailId] = useState<string | null>(null);
  const [detail, setDetail] = useState<OrderOut | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setListBusy(true);
    setError(null);
    try {
      const st = await fetchDashboardStores(token);
      setStores(st);
      const list = await fetchOrders(token, {
        store_id: storeFilter || undefined,
      });
      setOrders(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load orders");
    } finally {
      setListBusy(false);
    }
  }, [token, storeFilter]);

  useEffect(() => {
    if (!authLoading && token && user) void load();
  }, [authLoading, token, user, load]);

  const productOptions = useMemo(() => {
    const m = new Map<string, string>();
    for (const o of orders) {
      for (const it of o.items) {
        if (!m.has(it.product_id)) m.set(it.product_id, it.product_name);
      }
    }
    return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [orders]);

  const filtered = useMemo(() => {
    if (!productFilter) return orders;
    return orders.filter((o) => o.items.some((it) => it.product_id === productFilter));
  }, [orders, productFilter]);

  useEffect(() => {
    if (!detailId || !token) return;
    let cancelled = false;
    setDetailBusy(true);
    void (async () => {
      try {
        const d = await fetchOrder(token, detailId);
        if (!cancelled) setDetail(d);
      } catch {
        if (!cancelled) setDetail(null);
      } finally {
        if (!cancelled) setDetailBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [detailId, token]);

  if (authLoading || !user) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <AppShell title="Order history" description="Recent orders for your stores.">
      <RoleGate allow={["STAFF", "ADMIN", "INVENTORY_CONTROLLER", "BRANCH_MANAGER"]}>
        <div className="mb-6 flex flex-wrap gap-3">
          <div className="space-y-1">
            <Label htmlFor="oh-store">Store</Label>
            <select
              id="oh-store"
              className="flex h-10 min-w-[180px] rounded-md border border-border bg-card px-3 py-2 text-sm"
              value={storeFilter}
              onChange={(e) => setStoreFilter(e.target.value)}
            >
              <option value="">All stores</option>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="oh-product">Product</Label>
            <select
              id="oh-product"
              className="flex h-10 min-w-[200px] rounded-md border border-border bg-card px-3 py-2 text-sm"
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
            >
              <option value="">All products</option>
              {productOptions.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button type="button" variant="outline" onClick={() => void load()} disabled={listBusy}>
              {listBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Apply"}
            </Button>
          </div>
        </div>

        {error ? (
          <p className="mb-4 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Orders</CardTitle>
            <CardDescription>Click a row for line items and batches.</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {listBusy ? (
              <p className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </p>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-muted-foreground">No records found.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="py-2 pr-2">Order #</th>
                    <th className="py-2 pr-2">Date</th>
                    <th className="py-2 pr-2">Total</th>
                    <th className="py-2 pr-2">Items</th>
                    <th className="py-2">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((o) => (
                    <tr
                      key={o.id}
                      className="cursor-pointer border-b border-border/60 hover:bg-muted/40"
                      onClick={() => setDetailId(o.id)}
                    >
                      <td className="py-2 pr-2 font-medium">{o.order_number}</td>
                      <td className="py-2 pr-2 tabular-nums text-muted-foreground">
                        {new Date(o.created_at).toLocaleString()}
                      </td>
                      <td className="py-2 pr-2 tabular-nums">{formatMoney(o.total_amount)}</td>
                      <td className="py-2 pr-2 tabular-nums">{o.items.length}</td>
                      <td className="py-2">{o.order_type}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        {detailId ? (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="order-detail-title"
          >
            <Card className="max-h-[90vh] w-full max-w-2xl overflow-y-auto shadow-lg">
              <CardHeader className="flex flex-row items-start justify-between space-y-0">
                <div>
                  <CardTitle id="order-detail-title" className="text-lg">
                    Order details
                  </CardTitle>
                  <CardDescription>
                    {detail ? `${detail.order_number} · ${new Date(detail.created_at).toLocaleString()}` : "Loading…"}
                  </CardDescription>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-9 w-9 shrink-0 p-0"
                  onClick={() => setDetailId(null)}
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                {detailBusy || !detail ? (
                  <p className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> Loading…
                  </p>
                ) : (
                  <div className="space-y-4 text-sm">
                    <p>
                      <span className="text-muted-foreground">Total: </span>
                      <span className="font-medium tabular-nums">{formatMoney(detail.total_amount)}</span>
                      {" · "}
                      <span className="text-muted-foreground">Payment:</span> {detail.payment_method}
                    </p>
                    <table className="w-full text-left">
                      <thead>
                        <tr className="border-b border-border text-muted-foreground">
                          <th className="py-2 pr-2">Product</th>
                          <th className="py-2 pr-2">Batch</th>
                          <th className="py-2 pr-2">Qty</th>
                          <th className="py-2">Line total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.items.map((it) => (
                          <tr key={it.id} className="border-b border-border/60">
                            <td className="py-2 pr-2">{it.product_name}</td>
                            <td className="py-2 pr-2">{it.batch_number}</td>
                            <td className="py-2 pr-2 tabular-nums">{it.quantity}</td>
                            <td className="py-2 tabular-nums">{formatMoney(it.line_total)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        ) : null}
      </RoleGate>
    </AppShell>
  );
}
