import { Link, Outlet } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/transformation_pipeline")({
  component: TransformationPipelineLayout,
});

function TransformationPipelineLayout() {
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
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto bg-gray-900">
          <Outlet />
        </div>
      </div>
    </div>
  );
}