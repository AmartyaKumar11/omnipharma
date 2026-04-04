import { Link } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import type { UserRole } from "@/api/client";

export function RoleGate({ allow, children }: { allow: UserRole[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user || !allow.includes(user.role as UserRole)) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="text-destructive">You don&apos;t have access to this page.</p>
        <Link to="/dashboard" className="mt-4 inline-block text-sm text-primary underline">
          Back to dashboard
        </Link>
      </div>
    );
  }
  return <>{children}</>;
}
