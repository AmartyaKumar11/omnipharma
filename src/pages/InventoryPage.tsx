import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RoleGate } from "@/components/RoleGate";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/auth/AuthContext";
import type { InventoryRowPublic, UserRole } from "@/api/client";
import {
  fetchDashboardStores,
  fetchInventoryRows,
  postInventoryAdjust,
} from "@/api/client";

function badgeClass(kind: "low" | "exp") {
  if (kind === "low") return "bg-destructive/15 text-destructive border border-destructive/30";
  return "bg-amber-500/15 text-amber-900 dark:text-amber-100 border border-amber-500/35";
}

export function InventoryPage() {
  const { token, user } = useAuth();
  const role = user?.role as UserRole | undefined;

  const canAdjust = role === "ADMIN" || role === "INVENTORY_CONTROLLER";
  const canReplenishUi = role === "ADMIN" || role === "BRANCH_MANAGER";

  const [rows, setRows] = useState<InventoryRowPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const storeFilter = "";
  const [productFilter, setProductFilter] = useState("");
  const [sortBy, setSortBy] = useState<"expiry_date" | "quantity">("expiry_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const [adjStore, setAdjStore] = useState("");
  const [adjBatch, setAdjBatch] = useState("");
  const [adjQty, setAdjQty] = useState("");
  const [adjReason, setAdjReason] = useState("");
  const [adjBusy, setAdjBusy] = useState(false);

  const [marked, setMarked] = useState<Set<string>>(() => new Set());

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const st = await fetchDashboardStores(token);
      if (!adjStore && st[0]) setAdjStore(st[0].id);
      const list = await fetchInventoryRows(token, {
        store_id: storeFilter || undefined,
        product_id: productFilter || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      });
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load inventory");
    } finally {
      setLoading(false);
    }
  }, [token, storeFilter, productFilter, sortBy, sortDir]);

  useEffect(() => {
    void load();
  }, [load]);

  const productOptions = useMemo(() => {
    const m = new Map<string, string>();
    for (const r of rows) {
      m.set(r.product.id, r.product.name);
    }
    return [...m.entries()];
  }, [rows]);

  const lowStockRows = useMemo(() => {
    return rows.filter(
      (r) => r.reorder_threshold != null && r.quantity < r.reorder_threshold,
    );
  }, [rows]);

  async function onAdjust(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !adjStore || !adjBatch) return;
    const delta = parseInt(adjQty, 10);
    if (Number.isNaN(delta) || delta === 0) {
      setError("Enter a non-zero adjustment quantity (+ or −).");
      return;
    }
    setAdjBusy(true);
    setError(null);
    try {
      await postInventoryAdjust(token, {
        store_id: adjStore,
        batch_id: adjBatch,
        quantity_delta: delta,
        reason: adjReason.trim() || null,
      });
      setToast("Stock updated.");
      setAdjQty("");
      setAdjReason("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Adjustment failed");
    } finally {
      setAdjBusy(false);
    }
  }

  return (
    <AppShell
      title="Inventory"
      description="Stock levels, adjustments, and replenishment signals."
    >
      <RoleGate allow={["ADMIN", "BRANCH_MANAGER", "INVENTORY_CONTROLLER", "STAFF"]}>
        {toast ? (
          <p className="mb-4 rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-foreground">{toast}</p>
        ) : null}

        <div className="mb-6 flex flex-wrap gap-3">
          <div className="space-y-1">
            <Label htmlFor="f-product">Product</Label>
            <select
              id="f-product"
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
          <div className="space-y-1">
            <Label htmlFor="f-sort">Sort by</Label>
            <select
              id="f-sort"
              className="flex h-10 rounded-md border border-border bg-card px-3 py-2 text-sm"
              value={`${sortBy}:${sortDir}`}
              onChange={(e) => {
                const [sb, sd] = e.target.value.split(":") as [typeof sortBy, typeof sortDir];
                setSortBy(sb);
                setSortDir(sd);
              }}
            >
              <option value="expiry_date:asc">Expiry ↑</option>
              <option value="expiry_date:desc">Expiry ↓</option>
              <option value="quantity:asc">Quantity ↑</option>
              <option value="quantity:desc">Quantity ↓</option>
            </select>
          </div>
          <div className="flex items-end">
            <Button type="button" variant="outline" onClick={() => void load()} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Apply"}
            </Button>
          </div>
        </div>

        {canReplenishUi && lowStockRows.length > 0 ? (
          <Card className="mb-8 border-destructive/25">
            <CardHeader>
              <CardTitle className="text-lg">Replenishment suggestions</CardTitle>
              <CardDescription>Rows below reorder threshold — suggested restock = max(0, 2×threshold − quantity)</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="py-2 pr-2">Product</th>
                    <th className="py-2 pr-2">Batch</th>
                    <th className="py-2 pr-2">Qty</th>
                    <th className="py-2 pr-2">Threshold</th>
                    <th className="py-2 pr-2">Suggested</th>
                    <th className="py-2" />
                  </tr>
                </thead>
                <tbody>
                  {lowStockRows.map((r) => {
                    const th = r.reorder_threshold ?? 0;
                    const suggested = Math.max(0, th * 2 - r.quantity);
                    const key = r.inventory_id;
                    return (
                      <tr key={key} className="border-b border-border/60">
                        <td className="py-2 pr-2 font-medium">{r.product.name}</td>
                        <td className="py-2 pr-2">{r.batch.batch_number}</td>
                        <td className="py-2 pr-2 tabular-nums">{r.quantity}</td>
                        <td className="py-2 pr-2 tabular-nums">{th}</td>
                        <td className="py-2 pr-2 tabular-nums text-amber-800 dark:text-amber-200">{suggested}</td>
                        <td className="py-2">
                          <Button
                            type="button"
                            size="sm"
                            variant={marked.has(key) ? "default" : "outline"}
                            onClick={() => {
                              setMarked((prev) => {
                                const n = new Set(prev);
                                if (n.has(key)) n.delete(key);
                                else n.add(key);
                                return n;
                              });
                            }}
                          >
                            {marked.has(key) ? "Marked" : "Mark for restock"}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </CardContent>
          </Card>
        ) : null}

        {canAdjust ? (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="text-lg">Inventory adjustment</CardTitle>
              <CardDescription>Positive adds stock, negative removes. Logged as ADJUST / ADJUSTMENT.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={onAdjust} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="adj-batch">Batch ID</Label>
                  <Input
                    id="adj-batch"
                    required
                    placeholder="UUID from table below"
                    value={adjBatch}
                    onChange={(e) => setAdjBatch(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="adj-qty">Quantity (+ / −)</Label>
                  <Input
                    id="adj-qty"
                    required
                    inputMode="numeric"
                    placeholder="e.g. -2 or 5"
                    value={adjQty}
                    onChange={(e) => setAdjQty(e.target.value)}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2 lg:col-span-3">
                  <Label htmlFor="adj-reason">Reason</Label>
                  <Input
                    id="adj-reason"
                    placeholder="Damaged, recount, etc."
                    value={adjReason}
                    onChange={(e) => setAdjReason(e.target.value)}
                  />
                </div>
                <div className="sm:col-span-2 lg:col-span-3">
                  <Button type="submit" disabled={adjBusy}>
                    {adjBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Apply adjustment
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        ) : null}

        {error ? (
          <p className="mb-4 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">On-hand inventory</CardTitle>
            <CardDescription>FEFO selling uses earliest expiry first.</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {loading ? (
              <p className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </p>
            ) : rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No records found.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="py-2 pr-2">Product</th>
                    <th className="py-2 pr-2">Batch</th>
                    <th className="py-2 pr-2">Expiry</th>
                    <th className="py-2 pr-2">Qty</th>
                    <th className="py-2 pr-2">Reserved</th>
                    <th className="py-2 pr-2">Reorder</th>
                    <th className="py-2">Batch ID</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const low =
                      r.reorder_threshold != null && r.quantity < r.reorder_threshold;
                    const expSoon =
                      new Date(r.batch.expiry_date) <=
                      new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
                    return (
                      <tr key={r.inventory_id} className="border-b border-border/60">
                        <td className="py-2 pr-2">
                          <span className="font-medium">{r.product.name}</span>
                          {low ? (
                            <span className={`ml-2 inline-block rounded px-1.5 py-0.5 text-xs ${badgeClass("low")}`}>
                              LOW STOCK
                            </span>
                          ) : null}
                          {expSoon ? (
                            <span className={`ml-2 inline-block rounded px-1.5 py-0.5 text-xs ${badgeClass("exp")}`}>
                              EXPIRING
                            </span>
                          ) : null}
                        </td>
                        <td className="py-2 pr-2">{r.batch.batch_number}</td>
                        <td className="py-2 pr-2 tabular-nums">{r.batch.expiry_date}</td>
                        <td className="py-2 pr-2 tabular-nums">{r.quantity}</td>
                        <td className="py-2 pr-2 tabular-nums">{r.reserved_quantity}</td>
                        <td className="py-2 pr-2 tabular-nums">{r.reorder_threshold ?? "—"}</td>
                        <td className="py-2 font-mono text-xs text-muted-foreground">{r.batch.id}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </RoleGate>
    </AppShell>
  );
}
