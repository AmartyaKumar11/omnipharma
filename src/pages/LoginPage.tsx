import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/auth/AuthContext";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, loading, user } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (user && !loading) navigate("/dashboard", { replace: true });
  }, [user, loading, navigate]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await login(username.trim().toLowerCase(), password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[100dvh] max-w-4xl flex-col justify-center px-4 py-12">
      <div className="mb-8 text-center">
        <p className="font-display text-3xl font-semibold tracking-tight text-foreground">
          Centific
        </p>
        <p className="mt-1 text-sm text-muted-foreground">Pharmacy operations</p>
      </div>
      <div className="grid gap-8 md:grid-cols-2 items-start">
        <Card>
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>Use your username and password.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                required
                minLength={3}
                maxLength={32}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {formError ? (
              <p className="text-sm text-destructive" role="alert">
                {formError}
              </p>
            ) : null}
            <Button type="submit" className="w-full" disabled={submitting || loading}>
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link to="/signup" className="font-medium text-primary underline-offset-4 hover:underline">
              Create one
            </Link>
          </p>
        </CardContent>
        </Card>

        {/* Demo Credentials Card */}
        <Card className="bg-muted/30 border-dashed">
          <CardHeader>
            <CardTitle>Demo Credentials</CardTitle>
            <CardDescription>Password for all accounts: <span className="font-mono text-foreground font-medium">password123</span></CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div 
                className="rounded-md border bg-background p-3 text-sm cursor-pointer hover:border-primary/50 hover:bg-muted/50 transition-colors"
                onClick={() => { setUsername("amartyaadmin"); setPassword("password123"); }}
              >
                <div className="font-semibold text-foreground mb-1">Administrative Access</div>
                <div className="flex justify-between items-center text-muted-foreground">
                  <span>Username:</span>
                  <span className="font-mono text-foreground">amartyaadmin</span>
                </div>
              </div>

              <div 
                className="rounded-md border bg-background p-3 text-sm cursor-pointer hover:border-primary/50 hover:bg-muted/50 transition-colors"
                onClick={() => { setUsername("amartyabranch"); setPassword("password123"); }}
              >
                <div className="font-semibold text-foreground mb-1">Branch Manager</div>
                <div className="flex justify-between items-center text-muted-foreground">
                  <span>Username:</span>
                  <span className="font-mono text-foreground">amartyabranch</span>
                </div>
              </div>

              <div 
                className="rounded-md border bg-background p-3 text-sm cursor-pointer hover:border-primary/50 hover:bg-muted/50 transition-colors"
                onClick={() => { setUsername("amartyainventory"); setPassword("password123"); }}
              >
                <div className="font-semibold text-foreground mb-1">Inventory Manager</div>
                <div className="flex justify-between items-center text-muted-foreground">
                  <span>Username:</span>
                  <span className="font-mono text-foreground">amartyainventory</span>
                </div>
              </div>

              <div 
                className="rounded-md border bg-background p-3 text-sm cursor-pointer hover:border-primary/50 hover:bg-muted/50 transition-colors"
                onClick={() => { setUsername("amartyastaff"); setPassword("password123"); }}
              >
                <div className="font-semibold text-foreground mb-1">Staff Access</div>
                <div className="flex justify-between items-center text-muted-foreground">
                  <span>Username:</span>
                  <span className="font-mono text-foreground">amartyastaff</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
