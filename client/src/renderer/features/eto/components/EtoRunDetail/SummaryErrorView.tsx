/**
 * SummaryErrorView
 * Displays error information for failed ETO runs
 */

interface SummaryErrorViewProps {
  errorType: string | null;
  errorMessage: string | null;
  errorDetails: string | null;
}

export function SummaryErrorView({
  errorType,
  errorMessage,
  errorDetails,
}: SummaryErrorViewProps) {
  return (
    <div className="text-red-300 font-mono text-xs">
      <p className="font-bold mb-2">Error Type: {errorType || "Unknown"}</p>
      <p className="mb-2">
        Message: {errorMessage || "No error message available"}
      </p>
      {errorDetails && (
        <>
          <p className="font-bold mb-2 mt-4">Error Details:</p>
          <pre className="text-xs whitespace-pre-wrap">{errorDetails}</pre>
        </>
      )}
    </div>
  );
}
