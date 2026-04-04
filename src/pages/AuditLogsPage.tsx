import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RoleGate } from "@/components/RoleGate";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/auth/AuthContext";
import type { InventoryLogRow } from "@/api/client";
import { fetchInventoryLogs } from "@/api/client";

function actionLabel(changeType: string): string {
  const u = changeType.toUpperCase();
  if (u.includes("ADJUST")) return "ADJUST";
  if (u.includes("SALE") || u.includes("REMOVE")) return "REMOVE";
  if (u.includes("ADD") || u.includes("RESTOCK")) return "ADD";
  return changeType;
}

export function AuditLogsPage() {
  const { token, user, loading: authLoading } = useAuth();
  const [rows, setRows] = useState<InventoryLogRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const list = await fetchInventoryLogs(token, 500);
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!authLoading && token && user) void load();
  }, [authLoading, token, user, load]);

  if (authLoading || !user) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <AppShell
      title="Audit logs"
      description="Inventory changes: who did what, when (admin only)."
    >
      <RoleGate allow={["ADMIN"]}>
        <div className="mb-4 flex justify-end">
          <Button type="button" variant="outline" onClick={() => void load()} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Refresh"}
          </Button>
        </div>

        {error ? (
          <p className="mb-4 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Inventory audit</CardTitle>
            <CardDescription>Source: GET /inventory/logs</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {loading ? (
              <p className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </p>
            ) : rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No records found.</p>
            ) : (
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="py-2 pr-2">User</th>
                    <th className="py-2 pr-2">Action</th>
                    <th className="py-2 pr-2">Product</th>
                    <th className="py-2 pr-2">Batch</th>
                    <th className="py-2 pr-2">Qty Δ</th>
                    <th className="py-2">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id} className="border-b border-border/60">
                      <td className="py-2 pr-2">{r.username ?? "—"}</td>
                      <td className="py-2 pr-2">{actionLabel(r.change_type)}</td>
                      <td className="py-2 pr-2">{r.product_name}</td>
                      <td className="py-2 pr-2">{r.batch_number}</td>
                      <td className="py-2 pr-2 tabular-nums">{r.quantity_changed}</td>
                      <td className="py-2 text-muted-foreground">{new Date(r.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </RoleGate>
    </AppShell>
  );
}
