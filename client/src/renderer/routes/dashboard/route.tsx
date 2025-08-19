import { Link, Outlet, redirect } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/dashboard")({
  loader: async ({ location }) => {
    // Redirect if exactly on /dashboard
    if (location.pathname === "/dashboard") {
      throw redirect({ to: "/dashboard/home" });
    }
  },
  component: DashboardLayout,
});

function NavLink({ to, children }: { to: string; children: string }) {
  return (
    <Link
      to={to as unknown as string}
      className="block px-4 py-2 rounded hover:bg-indigo-100"
    >
      {children}
    </Link>
  );
}

function DashboardLayout() {

  return (
    <div className="flex h-screen">
      {/* Side navigation */}
      <aside className="w-64 border-r bg-gray-50 p-4 space-y-2">
        <NavLink to="/dashboard/home">Home</NavLink>
      </aside>
      {/* Routed content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
