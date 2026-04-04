import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { NavLinks } from "@/components/NavLinks";
import { useAuth } from "@/auth/AuthContext";

export function AppShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  const { logout } = useAuth();

  return (
    <div className="mx-auto min-h-[100dvh] max-w-6xl px-4 py-8">
      <header className="mb-8 flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight md:text-3xl">{title}</h1>
          {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
          <div className="mt-4">
            <NavLinks />
          </div>
        </div>
        <div className="flex flex-shrink-0 flex-wrap gap-2">
          <Button variant="outline" asChild>
            <Link to="/">Home</Link>
          </Button>
          <Button variant="outline" onClick={() => logout()}>
            Log out
          </Button>
        </div>
      </header>
      {children}
    </div>
  );
}
