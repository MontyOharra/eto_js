/**
 * SummarySuccessView
 * Displays executed actions in JSON format for successful ETO runs
 */

interface SummarySuccessViewProps {
  executedActions: Record<string, any> | null;
}

export function SummarySuccessView({ executedActions }: SummarySuccessViewProps) {
  if (!executedActions) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400">No executed actions available</p>
      </div>
    );
  }

  return (
    <pre className="text-gray-300 whitespace-pre-wrap break-words font-mono text-xs">
      {JSON.stringify(executedActions, null, 2)}
    </pre>
  );
}
