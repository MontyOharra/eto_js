/**
 * SummarySuccessView
 * Displays success state for completed ETO sub-runs
 * Output execution details will be shown here once PipelineResultService is implemented
 */

export function SummarySuccessView() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <div className="text-green-400 mb-4">
        <svg
          className="mx-auto h-16 w-16"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
      <p className="text-green-400 font-medium text-lg mb-2">
        Pipeline Completed Successfully
      </p>
      <p className="text-gray-400 text-sm">
        Use the Detail view to see extraction results and pipeline execution steps
      </p>
    </div>
  );
}
