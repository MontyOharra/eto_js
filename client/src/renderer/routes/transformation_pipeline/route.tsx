import { Link, Outlet, useLocation } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/transformation_pipeline")({
  component: TransformationPipelineLayout,
});

function TransformationPipelineLayout() {
  const location = useLocation();
  
  const tabs = [
    { id: 'graph', label: 'Graph Testing', path: '/transformation_pipeline/graph' },
    { id: 'modules', label: 'Module Management', path: '/transformation_pipeline/modules' }
  ];
  
  return (
    <div className="flex h-screen bg-gray-900">
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="sticky top-0 z-20 bg-gray-800 border-b border-gray-600">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center space-x-4">
              {/* Back to Dashboard Link */}
              <Link
                to="/dashboard"
                className="text-gray-400 hover:text-blue-300 transition-colors"
                title="Back to Dashboard"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              
              <h1 className="text-xl font-semibold text-white">
                Transformation Pipeline
              </h1>
            </div>
          </div>
          
          {/* Navigation Tabs */}
          <div className="px-4 pb-3">
            <nav className="flex space-x-1">
              {tabs.map((tab) => {
                const isActive = location.pathname === tab.path;
                return (
                  <Link
                    key={tab.id}
                    to={tab.path}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-300 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    {tab.label}
                  </Link>
                );
              })}
            </nav>
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