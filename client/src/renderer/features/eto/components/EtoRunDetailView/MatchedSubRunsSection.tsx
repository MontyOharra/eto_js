import { EtoSubRunSummary, EtoSubRunStatus } from '../../types';

/**
 * Check if a string is an ISO datetime format
 */
function isISODateTime(value: string): boolean {
  const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
  return isoPattern.test(value);
}

/**
 * Format ISO datetime string to human readable format
 */
function formatISODateTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    return date.toLocaleString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return isoString;
  }
}

/**
 * Check if value is a dim object (has height, length, width, qty, weight)
 */
function isDimObject(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    "height" in value &&
    "length" in value &&
    "width" in value &&
    "qty" in value &&
    "weight" in value
  );
}

/**
 * Format a single dim object as "qty - HxLxW @weightlbs"
 */
function formatDim(dim: Record<string, unknown>): string {
  const h = dim.height ?? 0;
  const l = dim.length ?? 0;
  const w = dim.width ?? 0;
  const qty = dim.qty ?? 1;
  const weight = dim.weight ?? 0;
  return `${qty} - ${h}x${l}x${w} @${weight}lbs`;
}

/**
 * Try to parse a value as JSON, handling Python-style single quotes
 */
function tryParseJson(value: string): unknown | null {
  // First try standard JSON parse
  try {
    return JSON.parse(value);
  } catch {
    // Try converting Python-style single quotes to double quotes
    try {
      // Replace single quotes with double quotes (but not escaped ones or apostrophes in text)
      const jsonified = value.replace(/'/g, '"');
      return JSON.parse(jsonified);
    } catch {
      return null;
    }
  }
}

/**
 * Format a value for display, handling datetime strings and dim objects
 */
function formatValue(value: string): string {
  if (!value) return value;

  // Check for ISO datetime string
  if (isISODateTime(value)) {
    return formatISODateTime(value);
  }

  // Try to parse as JSON for dim objects
  const parsed = tryParseJson(value);
  if (parsed !== null) {
    // Check for dim object
    if (isDimObject(parsed)) {
      return formatDim(parsed as Record<string, unknown>);
    }

    // Check for list[dim] - array of dim objects
    if (Array.isArray(parsed) && parsed.length > 0 && isDimObject(parsed[0])) {
      return "[" + parsed.map((d) => formatDim(d as Record<string, unknown>)).join(", ") + "]";
    }
  }

  return value;
}

interface MatchedSubRunsSectionProps {
  subRuns: EtoSubRunSummary[];
  onViewDetails: (subRunId: number) => void;
  onReprocess: (subRunId: number) => void;
  onSkip: (subRunId: number) => void;
}

function getStatusColor(status: EtoSubRunStatus): string {
  switch (status) {
    case 'success':
      return 'text-green-400 bg-green-400/10';
    case 'processing':
      return 'text-blue-400 bg-blue-400/10';
    case 'failure':
      return 'text-red-400 bg-red-400/10';
    case 'needs_template':
      return 'text-yellow-400 bg-yellow-400/10';
    default:
      return 'text-gray-400 bg-gray-400/10';
  }
}

function getStatusIcon(status: EtoSubRunStatus): string {
  switch (status) {
    case 'success':
      return '✓';
    case 'failure':
      return '✗';
    case 'needs_template':
      return '!';
    case 'processing':
      return '⟳';
    default:
      return '◦';
  }
}

export function MatchedSubRunsSection({
  subRuns,
  onViewDetails,
  onReprocess,
  onSkip,
}: MatchedSubRunsSectionProps) {
  if (subRuns.length === 0) return null;

  const successCount = subRuns.filter(sr => sr.status === 'success').length;
  const failureCount = subRuns.filter(sr => sr.status === 'failure').length;

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-white">Matched Templates ({subRuns.length})</h2>
        <span className="text-gray-400 text-sm">
          {successCount} successful, {failureCount} failed
        </span>
      </div>

      <div className="space-y-3">
        {subRuns.map((subRun) => (
          <div
            key={subRun.id}
            className={`rounded-lg p-4 border transition-colors ${
              subRun.status === 'failure'
                ? 'bg-red-900/10 border-red-700/50 hover:border-red-600'
                : 'bg-gray-700/30 border-gray-700 hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${getStatusColor(subRun.status)}`}>
                  {getStatusIcon(subRun.status)}
                </span>
                <h3 className="text-white font-semibold">
                  Pages {subRun.matched_pages.join(', ')} • {subRun.template?.name ?? 'Unknown Template'}
                  {subRun.template?.customer_name && (
                    <span className="text-gray-400 font-normal"> · {subRun.template.customer_name}</span>
                  )}
                </h3>
              </div>

              <div className="flex gap-2">
                {subRun.status === 'success' && (
                  <>
                    <button
                      onClick={() => onViewDetails(subRun.id)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                    >
                      View Details
                    </button>
                    <button
                      onClick={() => onReprocess(subRun.id)}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                    >
                      Reprocess
                    </button>
                  </>
                )}
                {subRun.status === 'failure' && (
                  <>
                    <button
                      onClick={() => onViewDetails(subRun.id)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                    >
                      View Details
                    </button>
                    <button
                      onClick={() => onReprocess(subRun.id)}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                    >
                      Reprocess
                    </button>
                    <button
                      onClick={() => onSkip(subRun.id)}
                      className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-md text-sm font-medium transition-colors whitespace-nowrap"
                    >
                      Skip
                    </button>
                  </>
                )}
              </div>
            </div>

            {subRun.status === 'success' && subRun.transform_results.length > 0 && (
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm ml-11 mt-2 p-3 bg-gray-800/50 rounded-lg">
                {subRun.transform_results.map((result, index) => (
                  <div key={`${result.field_name}-${index}`} className="flex gap-2 overflow-hidden">
                    <span className="text-gray-400 font-medium whitespace-nowrap">{result.field_name}:</span>
                    <span className="text-gray-200 truncate" title={formatValue(result.value)}>{formatValue(result.value)}</span>
                  </div>
                ))}
              </div>
            )}

            {subRun.status === 'failure' && subRun.error_message && (
              <div className="p-3 bg-red-900/20 border border-red-700/30 rounded text-sm">
                <p className="text-red-300">{subRun.error_message}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
