import { Link, Outlet, useLocation } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";
import { AuthGuard } from "../../components/AuthGuard";

export const Route = createFileRoute("/dashboard")({
  component: ProtectedDashboardLayout,
});

function ProtectedDashboardLayout() {
  return (
    <AuthGuard>
      <DashboardLayout />
    </AuthGuard>
  );
}

function DashboardLayout() {
  const location = useLocation();

  const tabs = [
    { name: "ETO", href: "/dashboard/eto" },
    { name: "Orders", href: "/dashboard/orders" },
    { name: "Templates", href: "/dashboard/pdf-templates" },
    { name: "Configs", href: "/dashboard/configs" },
  ];

  return (
    <div className="flex h-screen bg-gray-900">
      <div className="flex-1 flex flex-col">
        {/* Tab Navigation */}
        <div
          className={"sticky top-0 z-20 bg-gray-800 border-b border-gray-600"}
        >
          <div className="flex items-end justify-between px-2">
            <div className="flex">
              {tabs.map((tab, index) => {
                const isActive = location.pathname === tab.href || location.pathname.startsWith(tab.href + '/');
                return (
                  <Link
                    key={tab.name}
                    to={tab.href}
                    className={`relative px-6 py-3 font-medium text-sm transition-all duration-200 rounded-t-lg ${
                      isActive
                        ? "bg-gray-700 text-blue-300 z-10 border-l border-r border-t border-gray-600"
                        : "bg-gray-900 text-gray-400 hover:bg-gray-800 hover:text-gray-300 border-l border-r border-t border-b border-gray-600"
                    }`}
                    style={{
                      marginRight: index < tabs.length - 1 ? "8px" : "0",
                    }}
                  >
                    {tab.name}
                  </Link>
                );
              })}
            </div>
            <Link
              to="/dashboard/settings"
              className={`flex items-center justify-center p-2 mb-1 rounded transition-all duration-200 ${
                location.pathname.startsWith('/dashboard/settings')
                  ? "text-blue-300 bg-gray-700"
                  : "text-gray-400 hover:text-gray-300 hover:bg-gray-700"
              }`}
              title="Settings"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            </Link>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto bg-gray-900">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
