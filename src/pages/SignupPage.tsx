import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { UserRole } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/auth/AuthContext";

const roles: { value: UserRole; label: string }[] = [
  { value: "STAFF", label: "Staff" },
  { value: "BRANCH_MANAGER", label: "Branch manager" },
  { value: "INVENTORY_CONTROLLER", label: "Inventory controller" },
  { value: "ADMIN", label: "Admin" },
];

export function SignupPage() {
  const navigate = useNavigate();
  const { signup, user, loading } = useAuth();
  const [username, setUsername] = useState("");
  const [emailOptional, setEmailOptional] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("STAFF");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [stores, setStores] = useState<{ id: string; name: string }[]>([]);
  const [storeId, setStoreId] = useState("");

  useEffect(() => {
    fetch("/api/stores")
      .then((r) => r.json())
      .then((data) => {
        setStores(data);
        if (data.length > 0) setStoreId(data[0].id);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (user && !loading) navigate("/dashboard", { replace: true });
  }, [user, loading, navigate]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await signup(username.trim().toLowerCase(), password, role, emailOptional.trim() || null, role === "ADMIN" ? null : storeId);
      setDone(true);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="mx-auto flex min-h-[100dvh] max-w-md flex-col justify-center px-4 py-12">
        <Card>
          <CardHeader>
            <CardTitle>Account created</CardTitle>
            <CardDescription>You can sign in with your new credentials.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link to="/login">Go to sign in</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-[100dvh] max-w-md flex-col justify-center px-4 py-12">
      <div className="mb-8 text-center">
        <p className="font-display text-3xl font-semibold tracking-tight text-foreground">
          Centific
        </p>
        <p className="mt-1 text-sm text-muted-foreground">Create an operations account</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Sign up</CardTitle>
          <CardDescription>Choose a role for this environment.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="su-username">Username</Label>
              <Input
                id="su-username"
                type="text"
                autoComplete="username"
                required
                minLength={3}
                maxLength={32}
                placeholder="e.g. admin_demo, staff_1"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                3–32 characters: letters, digits, underscore (stored lowercase).
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="su-email">Email (optional)</Label>
              <Input
                id="su-email"
                type="text"
                inputMode="email"
                autoComplete="off"
                placeholder="Leave blank if you only use a username"
                value={emailOptional}
                onChange={(e) => setEmailOptional(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="su-password">Password</Label>
              <Input
                id="su-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="su-role">Role</Label>
              <select
                id="su-role"
                className="flex h-10 w-full rounded-md border border-border bg-card px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                {roles.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
            {role !== "ADMIN" && (
              <div className="space-y-2">
                <Label htmlFor="su-store">Store</Label>
                <select
                  id="su-store"
                  className="flex h-10 w-full rounded-md border border-border bg-card px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                  value={storeId}
                  onChange={(e) => setStoreId(e.target.value)}
                  required
                >
                  {stores.length === 0 ? <option value="">Loading...</option> : null}
                  {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
            )}
            {formError ? (
              <p className="text-sm text-destructive" role="alert">
                {formError}
              </p>
            ) : null}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Creating…" : "Create account"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
