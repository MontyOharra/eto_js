import { Link, Outlet, redirect, useLocation } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";
import { isAuthenticated } from "../../helpers/auth";

export const Route = createFileRoute("/dashboard")({
  loader: async ({ location }) => {
    if (!isAuthenticated()) {
      throw redirect({ to: "/login" });
    }
    // Redirect if exactly on /dashboard
    if (location.pathname === "/dashboard") {
      throw redirect({ to: "/dashboard/eto-info" });
    }
  },
  component: DashboardLayout,
});

function DashboardLayout() {
  const location = useLocation();

  const tabs = [
    { name: "ETO Information", href: "/dashboard/eto-info" },
    { name: "Templates", href: "/dashboard/templates" },
    { name: "Transformation Pipeline", href: "/transformation_pipeline/graph" },
  ];

  return (
    <div className="flex h-screen bg-gray-900">
      <div className="flex-1 flex flex-col">
        {/* Tab Navigation */}
        <div
          className={`sticky top-0 z-20 bg-gray-800 ${location.pathname === "/dashboard/eto-info" || location.pathname === "/dashboard/templates" || location.pathname === "/transformation_pipeline/graph" ? "" : "border-b border-gray-600"}`}
          style={{ marginTop: "8px" }}
        >
          <div className="flex items-end justify-between px-2">
            <div className="flex">
              {tabs.map((tab, index) => {
                const isActive = location.pathname === tab.href;
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

            <div className="flex items-center space-x-2">
              {/* Settings Gear Icon */}
              <Link
                to="/dashboard/settings"
                className="p-3 text-gray-400 hover:text-blue-300 transition-colors mb-1"
                title="Settings"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
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
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto bg-gray-900">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
