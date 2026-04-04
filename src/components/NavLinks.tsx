import { Link } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import type { UserRole } from "@/api/client";

const linkClass = "rounded-md px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground";

export function NavLinks() {
  const { user } = useAuth();
  if (!user) return null;
  const r = user.role as UserRole;

  const canOrders = r === "STAFF" || r === "ADMIN" || r === "INVENTORY_CONTROLLER";
  const canHistory = canOrders || r === "BRANCH_MANAGER";
  const canAudit = r === "ADMIN";

  return (
    <nav className="flex flex-wrap items-center gap-1 text-sm" aria-label="App">
      <Link className={linkClass} to="/dashboard">
        Dashboard
      </Link>
      <Link className={linkClass} to="/inventory">
        Inventory
      </Link>
      {canOrders ? (
        <Link className={linkClass} to="/orders">
          New order
        </Link>
      ) : null}
      {canHistory ? (
        <Link className={linkClass} to="/orders/history">
          Order history
        </Link>
      ) : null}
      {canAudit ? (
        <Link className={linkClass} to="/audit">
          Audit logs
        </Link>
      ) : null}
    </nav>
  );
}
