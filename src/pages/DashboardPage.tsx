import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  BarChart3,
  IndianRupee,
  Package,
  ShoppingCart,
  Store,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/auth/AuthContext";
import type {
  AlertItem,
  AlertsResponse,
  DashboardSummary,
  SalesTrendPoint,
  StoreBrief,
  StorePerformanceRow,
} from "@/api/client";
import {
  fetchDashboardStores,
  fetchDashboardSummary,
  fetchInventoryAlerts,
  fetchSalesTrend,
  fetchStorePerformance,
} from "@/api/client";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function formatMoney(n: number): string {
  return new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

function SalesTrendChart({ points }: { points: SalesTrendPoint[] }) {
  const w = 560;
  const h = 200;
  const pad = 24;
  if (points.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">No sales in this range.</p>
    );
  }
  const maxY = Math.max(...points.map((p) => p.sales), 1);
  const minX = 0;
  const maxX = points.length - 1;
  const xScale = (i: number) => pad + ((i - minX) / Math.max(maxX - minX, 1)) * (w - pad * 2);
  const yScale = (v: number) => h - pad - (v / maxY) * (h - pad * 2);
  const d = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(i)} ${yScale(p.sales)}`)
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="w-full max-h-[220px] text-primary"
      role="img"
      aria-label="Sales trend"
    >
      <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} className="stroke-border" strokeWidth={1} />
      <line x1={pad} y1={pad} x2={pad} y2={h - pad} className="stroke-border" strokeWidth={1} />
      <path d={d} fill="none" stroke="currentColor" strokeWidth={2} strokeLinejoin="round" />
      {points.map((p, i) => (
        <circle key={p.date} cx={xScale(i)} cy={yScale(p.sales)} r={3} className="fill-primary" />
      ))}
    </svg>
  );
}

function AlertList({ title, items, emptyHint }: { title: string; items: AlertItem[]; emptyHint: string }) {
  const show = items.slice(0, 12);
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>{items.length ? `${items.length} item(s)` : emptyHint}</CardDescription>
      </CardHeader>
      <CardContent className="max-h-72 flex-1 overflow-y-auto space-y-2 text-sm">
        {show.length === 0 ? (
          <p className="text-muted-foreground">None right now.</p>
        ) : (
          show.map((a, idx) => (
            <div
              key={`${a.batch_id}-${idx}`}
              className="rounded-md border border-border/80 bg-card/50 px-3 py-2"
            >
              <p className="font-medium text-foreground">{a.product_name}</p>
              <p className="text-muted-foreground">{a.message}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {a.severity} · batch {a.batch_number}
              </p>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { user, token, logout, loading } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertsResponse | null>(null);
  const [trend, setTrend] = useState<SalesTrendPoint[]>([]);
  const [stores, setStores] = useState<StoreBrief[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string>("");
  const [storePerf, setStorePerf] = useState<StorePerformanceRow[]>([]);
  const [dashLoading, setDashLoading] = useState(true);
  const [dashError, setDashError] = useState<string | null>(null);

  const canAnalytics = user?.role !== "STAFF";

  const range30 = useMemo(() => {
    const to = new Date();
    const from = new Date();
    from.setDate(from.getDate() - 30);
    return { date_from: isoDate(from), date_to: isoDate(to) };
  }, []);

  const range14 = useMemo(() => {
    const to = new Date();
    const from = new Date();
    from.setDate(from.getDate() - 14);
    return { date_from: isoDate(from), date_to: isoDate(to) };
  }, []);

  const loadCore = useCallback(async () => {
    if (!token) return;
    setDashError(null);
    setDashLoading(true);
    try {
      const [sum, al] = await Promise.all([
        fetchDashboardSummary(token, range30),
        fetchInventoryAlerts(token, { expiry_days: "30" }),
      ]);
      setSummary(sum);
      setAlerts(al);
    } catch (e) {
      setDashError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setDashLoading(false);
    }
  }, [token, range30.date_from, range30.date_to]);

  const loadAnalytics = useCallback(async () => {
    if (!token || !canAnalytics) return;
    try {
      const st = await fetchDashboardStores(token);
      setStores(st);
      const sid = st[0]?.id ?? "";
      setSelectedStoreId(sid);
      const [perf, tr] = await Promise.all([
        fetchStorePerformance(token, range30),
        sid
          ? fetchSalesTrend(token, { store_id: sid, date_from: range14.date_from, date_to: range14.date_to })
          : Promise.resolve([]),
      ]);
      setStorePerf(perf);
      setTrend(tr);
    } catch {
      /* optional panels */
    }
  }, [token, canAnalytics, range30, range14]);

  useEffect(() => {
    if (!loading && user && token) void loadCore();
  }, [loading, user, token, loadCore]);

  useEffect(() => {
    if (!loading && user && token && canAnalytics) void loadAnalytics();
  }, [loading, user, token, canAnalytics, loadAnalytics]);

  useEffect(() => {
    if (!token || !canAnalytics || !selectedStoreId) return;
    let cancelled = false;
    void (async () => {
      try {
        const tr = await fetchSalesTrend(token, {
          store_id: selectedStoreId,
          date_from: range14.date_from,
          date_to: range14.date_to,
        });
        if (!cancelled) setTrend(tr);
      } catch {
        if (!cancelled) setTrend([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, canAnalytics, selectedStoreId, range14.date_from, range14.date_to]);

  if (loading || !user) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto min-h-[100dvh] max-w-6xl px-4 py-10">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Operations dashboard</h1>
          <p className="text-sm text-muted-foreground">Sales, inventory health, and alerts</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild>
            <Link to="/">Home</Link>
          </Button>
          <Button variant="outline" onClick={() => logout()}>
            Log out
          </Button>
        </div>
      </header>

      {dashError ? (
        <p className="mb-6 text-sm text-destructive" role="alert">
          {dashError}
        </p>
      ) : null}

      {dashLoading && !summary ? (
        <p className="text-muted-foreground">Loading metrics…</p>
      ) : summary ? (
        <>
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total sales</CardTitle>
                <IndianRupee className="h-4 w-4 text-muted-foreground" aria-hidden />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold tabular-nums">{formatMoney(summary.total_sales)}</p>
                <CardDescription className="text-xs">Last 30 days</CardDescription>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Orders</CardTitle>
                <ShoppingCart className="h-4 w-4 text-muted-foreground" aria-hidden />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold tabular-nums">{summary.total_orders}</p>
                <CardDescription className="text-xs">Completed orders</CardDescription>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg order</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" aria-hidden />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold tabular-nums">{formatMoney(summary.average_order_value)}</p>
                <CardDescription className="text-xs">Mean value</CardDescription>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Low stock</CardTitle>
                <Package className="h-4 w-4 text-muted-foreground" aria-hidden />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold tabular-nums">{summary.low_stock_count}</p>
                <CardDescription className="text-xs">Below reorder threshold</CardDescription>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Expiring soon</CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" aria-hidden />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold tabular-nums">{summary.expiring_soon_count}</p>
                <CardDescription className="text-xs">Within 30 days</CardDescription>
              </CardContent>
            </Card>
          </div>

          {canAnalytics ? (
            <div className="mb-10 space-y-8">
              <Card>
                <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5" aria-hidden />
                      Sales trend
                    </CardTitle>
                    <CardDescription>Daily revenue for the selected store (last 14 days)</CardDescription>
                  </div>
                  {stores.length > 0 ? (
                    <label className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Store</span>
                      <select
                        className="rounded-md border border-border bg-card px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                        value={selectedStoreId}
                        onChange={(e) => setSelectedStoreId(e.target.value)}
                      >
                        {stores.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </CardHeader>
                <CardContent>
                  <SalesTrendChart points={trend} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Store className="h-5 w-5" aria-hidden />
                    Store performance
                  </CardTitle>
                  <CardDescription>Sales by store (last 30 days)</CardDescription>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <table className="w-full min-w-[480px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th className="py-2 pr-4 font-medium">Store</th>
                        <th className="py-2 pr-4 font-medium">Orders</th>
                        <th className="py-2 font-medium">Sales</th>
                      </tr>
                    </thead>
                    <tbody>
                      {storePerf.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="py-6 text-muted-foreground">
                            No orders in range, or stores not set up yet.
                          </td>
                        </tr>
                      ) : (
                        storePerf.map((row) => (
                          <tr key={row.store_id} className="border-b border-border/60">
                            <td className="py-3 pr-4 font-medium">{row.store_name}</td>
                            <td className="py-3 pr-4 tabular-nums">{row.order_count}</td>
                            <td className="py-3 tabular-nums">{formatMoney(row.total_sales)}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </div>
          ) : (
            <p className="mb-8 text-sm text-muted-foreground">
              Detailed charts and store comparison are available to managers and admins. You still have summary
              metrics and alerts below.
            </p>
          )}

          {alerts ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <AlertList
                title="Low stock"
                items={alerts.low_stock}
                emptyHint="All tracked SKUs above reorder levels"
              />
              <AlertList
                title="Expiry & quality"
                items={alerts.expiry}
                emptyHint="No batches in the expiry window"
              />
            </div>
          ) : null}
        </>
      ) : (
        <p className="text-muted-foreground">No data.</p>
      )}
    </div>
  );
}
