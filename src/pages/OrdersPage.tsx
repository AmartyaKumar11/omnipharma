import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RoleGate } from "@/components/RoleGate";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/auth/AuthContext";
import type { InventoryRowPublic, OrderType, PaymentMethod } from "@/api/client";
import { createOrder, fetchDashboardStores, fetchInventoryRows } from "@/api/client";

type Line = { product_id: string; quantity: number };

export function OrdersPage() {
  const { token, user, loading: authLoading } = useAuth();
  const [storeId, setStoreId] = useState("");
  const [rows, setRows] = useState<InventoryRowPublic[]>([]);
  const [lines, setLines] = useState<Line[]>([{ product_id: "", quantity: 1 }]);
  const [payment, setPayment] = useState<PaymentMethod>("CASH");
  const [orderType, setOrderType] = useState<OrderType>("OTC");
  const [doctorName, setDoctorName] = useState("");
  const [prescriptionNotes, setPrescriptionNotes] = useState("");
  const [prescriptionFileUrl, setPrescriptionFileUrl] = useState<string | null>(null);
  const [fileLabel, setFileLabel] = useState<string | null>(null);

  const [loadBusy, setLoadBusy] = useState(true);
  const [submitBusy, setSubmitBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadStores = useCallback(async () => {
    if (!token) return;
    setLoadBusy(true);
    setError(null);
    try {
      const st = await fetchDashboardStores(token);
      setStoreId((prev) => prev || st[0]?.id || "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load stores");
    } finally {
      setLoadBusy(false);
    }
  }, [token]);

  const loadInventory = useCallback(async () => {
    if (!token || !storeId) return;
    setLoadBusy(true);
    setError(null);
    try {
      const list = await fetchInventoryRows(token, { store_id: storeId });
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load inventory");
    } finally {
      setLoadBusy(false);
    }
  }, [token, storeId]);

  useEffect(() => {
    if (!authLoading && token && user) void loadStores();
  }, [authLoading, token, user, loadStores]);

  useEffect(() => {
    if (storeId && token) void loadInventory();
  }, [storeId, token, loadInventory]);

  const productOptions = useMemo(() => {
    const m = new Map<string, string>();
    for (const r of rows) {
      if (!m.has(r.product.id)) m.set(r.product.id, r.product.name);
    }
    return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [rows]);

  function addLine() {
    setLines((prev) => [...prev, { product_id: "", quantity: 1 }]);
  }

  function removeLine(i: number) {
    setLines((prev) => (prev.length <= 1 ? prev : prev.filter((_, j) => j !== i)));
  }

  function updateLine(i: number, patch: Partial<Line>) {
    setLines((prev) => prev.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  }

  function onPrescriptionFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) {
      setFileLabel(null);
      setPrescriptionFileUrl(null);
      return;
    }
    setFileLabel(f.name);
    const reader = new FileReader();
    reader.onload = () => {
      const r = reader.result as string;
      const MAX = 120_000;
      setPrescriptionFileUrl(r.length > MAX ? `inline://${f.name}` : r);
    };
    reader.readAsDataURL(f);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !storeId) return;
    const items = lines
      .filter((l) => l.product_id && l.quantity > 0)
      .map((l) => ({ product_id: l.product_id, quantity: l.quantity }));
    if (items.length === 0) {
      setError("Add at least one line with a product and quantity.");
      return;
    }
    if (orderType === "PRESCRIPTION") {
      const hasDoc = Boolean(doctorName.trim());
      const hasFile = Boolean(prescriptionFileUrl?.trim());
      if (!hasDoc && !hasFile) {
        setError("Prescription orders need a doctor name and/or an uploaded file.");
        return;
      }
    }
    setSubmitBusy(true);
    setError(null);
    setSuccess(null);
    try {
      await createOrder(token, {
        store_id: storeId,
        items,
        payment_method: payment,
        order_type: orderType,
        prescription_file_url: prescriptionFileUrl,
        doctor_name: doctorName.trim() || null,
        prescription_notes: prescriptionNotes.trim() || null,
      });
      setSuccess("Order created successfully.");
      setLines([{ product_id: "", quantity: 1 }]);
      setDoctorName("");
      setPrescriptionNotes("");
      setPrescriptionFileUrl(null);
      setFileLabel(null);
      await loadInventory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create order");
    } finally {
      setSubmitBusy(false);
    }
  }

  if (authLoading || !user) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <AppShell title="New order" description="Create a sale; stock is reduced using FEFO allocation.">
      <RoleGate allow={["STAFF", "ADMIN", "INVENTORY_CONTROLLER"]}>
        {success ? (
          <p className="mb-4 rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-foreground" role="status">
            {success}
          </p>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Order details</CardTitle>
            <CardDescription>Select store and lines. Prescription orders can include an optional file and doctor name.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="o-pay">Payment</Label>
                  <select
                    id="o-pay"
                    className="flex h-10 w-full rounded-md border border-border bg-card px-3 py-2 text-sm"
                    value={payment}
                    onChange={(e) => setPayment(e.target.value as PaymentMethod)}
                  >
                    <option value="CASH">Cash</option>
                    <option value="CARD">Card</option>
                    <option value="UPI">UPI</option>
                  </select>
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="o-type">Order type</Label>
                  <select
                    id="o-type"
                    className="flex h-10 max-w-md rounded-md border border-border bg-card px-3 py-2 text-sm"
                    value={orderType}
                    onChange={(e) => setOrderType(e.target.value as OrderType)}
                  >
                    <option value="OTC">OTC</option>
                    <option value="PRESCRIPTION">Prescription</option>
                  </select>
                </div>
              </div>

              {orderType === "PRESCRIPTION" ? (
                <div className="space-y-4 rounded-md border border-border/80 bg-muted/30 p-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="o-doc">Doctor name</Label>
                      <Input
                        id="o-doc"
                        placeholder="Prescriber (optional if file attached)"
                        value={doctorName}
                        onChange={(e) => setDoctorName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="o-rx-file">Prescription file (optional)</Label>
                      <Input id="o-rx-file" type="file" accept="image/*,.pdf" onChange={onPrescriptionFile} />
                      {fileLabel ? <p className="text-xs text-muted-foreground">Selected: {fileLabel}</p> : null}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="o-rx-notes">Prescription notes</Label>
                    <Input
                      id="o-rx-notes"
                      placeholder="Rx notes (optional)"
                      value={prescriptionNotes}
                      onChange={(e) => setPrescriptionNotes(e.target.value)}
                    />
                  </div>
                </div>
              ) : null}

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <Label>Lines</Label>
                  <Button type="button" variant="outline" size="sm" onClick={addLine}>
                    <Plus className="mr-1 h-4 w-4" />
                    Add line
                  </Button>
                </div>
                {lines.map((line, i) => (
                  <div key={i} className="flex flex-wrap items-end gap-2 rounded-md border border-border/60 p-3">
                    <div className="min-w-[200px] flex-1 space-y-1">
                      <Label htmlFor={`p-${i}`}>Product</Label>
                      <select
                        id={`p-${i}`}
                        className="flex h-10 w-full rounded-md border border-border bg-card px-3 py-2 text-sm"
                        value={line.product_id}
                        onChange={(e) => updateLine(i, { product_id: e.target.value })}
                      >
                        <option value="">Select…</option>
                        {productOptions.map(([id, name]) => (
                          <option key={id} value={id}>
                            {name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="w-28 space-y-1">
                      <Label htmlFor={`q-${i}`}>Qty</Label>
                      <Input
                        id={`q-${i}`}
                        inputMode="numeric"
                        min={1}
                        value={line.quantity}
                        onChange={(e) => updateLine(i, { quantity: Math.max(1, parseInt(e.target.value, 10) || 0) })}
                      />
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-10 w-10 shrink-0 p-0"
                      onClick={() => removeLine(i)}
                      disabled={lines.length <= 1}
                      aria-label="Remove line"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>

              {error ? (
                <p className="text-sm text-destructive" role="alert">
                  {error}
                </p>
              ) : null}

              <Button type="submit" disabled={submitBusy || loadBusy}>
                {submitBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Place order
              </Button>
            </form>
          </CardContent>
        </Card>
      </RoleGate>
    </AppShell>
  );
}
