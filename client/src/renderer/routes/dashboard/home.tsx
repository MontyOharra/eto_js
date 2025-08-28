import { createFileRoute } from "@tanstack/react-router";
import { useSystemStats, useEmailStatus, useEtoRuns, useServerHealth } from "../../hooks/useApi";

export const Route = createFileRoute("/dashboard/home")({
  component: Home,
});

function Home() {
  const { data: stats, loading: statsLoading, error: statsError } = useSystemStats(true, 30000);
  const { data: emailStatus, loading: emailLoading } = useEmailStatus(true, 10000);
  const { data: recentRuns } = useEtoRuns({ limit: 5 });
  const { isServerOnline } = useServerHealth();

  // Calculate recent activity (last 24 hours)
  const recentSuccessCount = recentRuns?.filter(run => run.status === 'success').length || 0;
  const recentFailureCount = recentRuns?.filter(run => run.status === 'failure').length || 0;
  const recentNeedsTemplateCount = recentRuns?.filter(run => run.status === 'needs_template').length || 0;
  const recentProcessingCount = recentRuns?.filter(run => run.status === 'processing').length || 0;
  const recentNotStartedCount = recentRuns?.filter(run => run.status === 'not_started').length || 0;

  return (
    <div className="flex-1 p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-blue-300 mb-2">
          Dashboard Overview
        </h1>
        <p className="text-gray-400">
          ETO System status and processing statistics
        </p>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Server Status */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Server Status</p>
              <p className={`text-lg font-semibold ${isServerOnline ? 'text-green-400' : 'text-red-400'}`}>
                {isServerOnline ? 'Online' : 'Offline'}
              </p>
            </div>
            <div className={`w-4 h-4 rounded-full ${isServerOnline ? 'bg-green-400' : 'bg-red-400'}`}></div>
          </div>
        </div>

        {/* Email Monitoring */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Email Monitoring</p>
              <p className={`text-lg font-semibold ${emailStatus?.monitoring ? 'text-green-400' : 'text-yellow-400'}`}>
                {emailLoading ? 'Loading...' : emailStatus?.monitoring ? 'Active' : 'Stopped'}
              </p>
              {emailStatus?.current_email && (
                <p className="text-xs text-gray-500 mt-1">{emailStatus.current_email}</p>
              )}
            </div>
            <div className={`w-4 h-4 rounded-full ${emailStatus?.monitoring ? 'bg-green-400' : 'bg-yellow-400'}`}></div>
          </div>
        </div>

        {/* Processing Success Rate */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div>
            <p className="text-sm text-gray-400 mb-1">Success Rate</p>
            {statsLoading ? (
              <p className="text-lg font-semibold text-gray-400">Loading...</p>
            ) : statsError ? (
              <p className="text-lg font-semibold text-red-400">Error</p>
            ) : (
              <p className="text-lg font-semibold text-blue-300">
                {stats ? `${(stats.processing.success_rate * 100).toFixed(1)}%` : 'N/A'}
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              {stats ? `${stats.processing.total_processed} total processed` : 'No data'}
            </p>
          </div>
        </div>

        {/* Storage Usage */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div>
            <p className="text-sm text-gray-400 mb-1">Storage</p>
            {statsLoading ? (
              <p className="text-lg font-semibold text-gray-400">Loading...</p>
            ) : statsError ? (
              <p className="text-lg font-semibold text-red-400">Error</p>
            ) : (
              <p className="text-lg font-semibold text-purple-300">
                {stats ? `${stats.storage.total_size_mb.toFixed(1)} MB` : 'N/A'}
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              {stats ? `${stats.storage.total_files} files` : 'No data'}
            </p>
          </div>
        </div>
      </div>

      {/* Database Statistics */}
      {!statsLoading && !statsError && stats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-300 mb-4">Database Statistics</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Total Emails</span>
                <span className="text-white font-medium">{stats.database.emails_count}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">PDF Files</span>
                <span className="text-white font-medium">{stats.database.pdf_files_count}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">ETO Runs</span>
                <span className="text-white font-medium">{stats.database.eto_runs_count}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Templates</span>
                <span className="text-white font-medium">{stats.database.templates_count}</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-300 mb-4">Recent Activity</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-green-400">Successful</span>
                <span className="text-white font-medium">{recentSuccessCount}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-red-400">Failed</span>
                <span className="text-white font-medium">{recentFailureCount}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-yellow-400">Needs Template</span>
                <span className="text-white font-medium">{recentNeedsTemplateCount}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-blue-400">Processing</span>
                <span className="text-white font-medium">{recentProcessingCount}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Not Started</span>
                <span className="text-white font-medium">{recentNotStartedCount}</span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-gray-600">
                <span className="text-gray-400">Total Recent</span>
                <span className="text-white font-medium">{recentRuns?.length || 0}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-300 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="p-4 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-left transition-colors">
            <div className="flex items-center space-x-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <div>
                <h4 className="font-medium">Email Settings</h4>
                <p className="text-sm text-blue-200">Configure monitoring</p>
              </div>
            </div>
          </button>
          
          <button className="p-4 bg-purple-600 hover:bg-purple-700 rounded-lg text-white text-left transition-colors">
            <div className="flex items-center space-x-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <div>
                <h4 className="font-medium">Templates</h4>
                <p className="text-sm text-purple-200">Manage templates</p>
              </div>
            </div>
          </button>
          
          <button className="p-4 bg-green-600 hover:bg-green-700 rounded-lg text-white text-left transition-colors">
            <div className="flex items-center space-x-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <div>
                <h4 className="font-medium">View Reports</h4>
                <p className="text-sm text-green-200">Processing results</p>
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
