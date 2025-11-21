import { Link, Outlet, useLocation } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/dashboard")({
  component: DashboardLayout,
});

function DashboardLayout() {
  const location = useLocation();

  const tabs = [
    { name: "ETO Information", href: "/dashboard/eto" },
    { name: "Templates", href: "/dashboard/pdf-templates" },
    { name: "Transformation Pipeline", href: "/dashboard/pipelines" },
    { name: "Configurations", href: "/dashboard/configs" },
    { name: "Test", href: "/dashboard/test" },
  ];

  return (
    <div className="flex h-screen bg-gray-900">
      <div className="flex-1 flex flex-col">
        {/* Tab Navigation */}
        <div
          className={"sticky top-0 z-20 bg-gray-800 border-b border-gray-600"}
          style={{ marginTop: "8px" }}
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
