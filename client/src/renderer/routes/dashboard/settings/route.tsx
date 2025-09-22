import { Outlet, useLocation } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsLayout,
});

function SettingsLayout() {
  const location = useLocation();

  // If we're exactly on /dashboard/settings, show the main settings page
  if (location.pathname === "/dashboard/settings") {
    return (
      <div className="flex-1 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-blue-300 mb-2">Settings</h1>
          <p className="text-gray-400">Configure application settings and preferences</p>
        </div>

        <div className="space-y-4">
          {/* Email Ingestion Configuration */}
          <Link
            to="/dashboard/settings/email-configs"
            className="block bg-gray-800 hover:bg-gray-750 rounded-lg p-4 transition-colors group"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="text-white font-medium group-hover:text-blue-300 transition-colors">
                  Email Ingestion Configuration
                </h3>
                <p className="text-gray-400 text-sm mt-1">
                  Configure email monitoring and processing settings
                </p>
              </div>
              <svg className="w-5 h-5 text-gray-400 group-hover:text-blue-300 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </Link>

          {/* Placeholder for future settings */}
          <div className="bg-gray-800 rounded-lg p-4 opacity-50">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="text-gray-400 font-medium">
                  General Settings
                </h3>
                <p className="text-gray-500 text-sm mt-1">
                  Application preferences and general configuration (Coming Soon)
                </p>
              </div>
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 opacity-50">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="text-gray-400 font-medium">
                  Notification Settings
                </h3>
                <p className="text-gray-500 text-sm mt-1">
                  Configure alerts and notifications (Coming Soon)
                </p>
              </div>
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-4 opacity-50">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="text-gray-400 font-medium">
                  Advanced Settings
                </h3>
                <p className="text-gray-500 text-sm mt-1">
                  Advanced configuration options (Coming Soon)
                </p>
              </div>
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // For subroutes, show the outlet
  return (
    <div className="flex-1">
      <Outlet />
    </div>
  );
}