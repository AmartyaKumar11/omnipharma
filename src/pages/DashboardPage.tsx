import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAdminPing } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/auth/AuthContext";

export function DashboardPage() {
  const { user, token, logout, loading } = useAuth();
  const [adminMsg, setAdminMsg] = useState<string | null>(null);
  const [adminErr, setAdminErr] = useState<string | null>(null);

  useEffect(() => {
    setAdminMsg(null);
    setAdminErr(null);
  }, [user?.role]);

  async function tryAdminPing() {
    if (!token) return;
    setAdminErr(null);
    setAdminMsg(null);
    try {
      const r = await fetchAdminPing(token);
      setAdminMsg(r.message);
    } catch (e) {
      setAdminErr(e instanceof Error ? e.message : "Forbidden");
    }
  }

  if (loading || !user) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center p-6">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Protected route — JWT required</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link to="/">Home</Link>
          </Button>
          <Button variant="outline" onClick={() => logout()}>
            Log out
          </Button>
        </div>
      </header>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Session</CardTitle>
          <CardDescription>Loaded from GET /auth/me</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>
            <span className="text-muted-foreground">Email:</span> {user.email}
          </p>
          <p>
            <span className="text-muted-foreground">Role:</span>{" "}
            <span className="rounded-md bg-muted px-2 py-0.5 font-medium capitalize">{user.role}</span>
          </p>
          <p className="break-all text-muted-foreground">
            <span className="text-foreground">User id:</span> {user.id}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Role check</CardTitle>
          <CardDescription>
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">GET /auth/admin/ping</code> is
            restricted to <strong>admin</strong>.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button type="button" onClick={() => void tryAdminPing()}>
            Call admin-only endpoint
          </Button>
          {adminMsg ? (
            <p className="text-sm text-primary" role="status">
              {adminMsg}
            </p>
          ) : null}
          {adminErr ? (
            <p className="text-sm text-destructive" role="alert">
              {adminErr}
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
