import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthContext";

export function HomePage() {
  const { user, loading } = useAuth();

  return (
    <div className="mx-auto flex min-h-[100dvh] max-w-3xl flex-col justify-center px-4 py-16">
      <p className="font-display text-4xl font-semibold tracking-tight md:text-5xl">
        Omnichannel pharmacy operations
      </p>
      <p className="mt-4 max-w-xl text-lg text-muted-foreground">
        Multi-store inventory, sales, and compliance-ready workflows — starting with secure access.
      </p>
      <div className="mt-10 flex flex-wrap gap-3">
        {loading ? (
          <span className="text-sm text-muted-foreground">Checking session…</span>
        ) : user ? (
          <Button asChild size="lg">
            <Link to="/dashboard">Open dashboard</Link>
          </Button>
        ) : (
          <>
            <Button asChild size="lg">
              <Link to="/login">Sign in</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to="/signup">Sign up</Link>
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
