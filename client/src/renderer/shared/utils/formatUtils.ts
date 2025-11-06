/**
 * Formatting Utilities
 * Shared utilities for formatting file sizes, durations, and other common display values
 */

/**
 * Format file size in bytes to human-readable string with appropriate units
 *
 * @param bytes - File size in bytes (null returns "Unknown")
 * @returns Formatted string like "1.5 MB", "234 KB", "5 Bytes"
 *
 * @example
 * formatFileSize(1536) // "1.5 KB"
 * formatFileSize(2097152) // "2 MB"
 * formatFileSize(null) // "Unknown"
 */
export function formatFileSize(bytes: number | null): string {
  if (bytes === null) return 'Unknown';
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const value = bytes / Math.pow(k, i);

  // Round to 2 decimal places
  return `${Math.round(value * 100) / 100} ${sizes[i]}`;
}

/**
 * Format duration between two timestamps to human-readable string
 *
 * @param startedAt - ISO 8601 start timestamp (null returns "N/A")
 * @param completedAt - ISO 8601 end timestamp (null returns "N/A")
 * @returns Formatted string like "5m 23s" or "45s"
 *
 * @example
 * formatDuration("2025-01-01T12:00:00Z", "2025-01-01T12:05:23Z") // "5m 23s"
 * formatDuration("2025-01-01T12:00:00Z", "2025-01-01T12:00:45Z") // "45s"
 * formatDuration(null, null) // "N/A"
 */
export function formatDuration(
  startedAt: string | null,
  completedAt: string | null
): string {
  if (!startedAt || !completedAt) return 'N/A';

  const start = new Date(startedAt).getTime();
  const end = new Date(completedAt).getTime();
  const durationMs = end - start;

  const seconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  return `${seconds}s`;
}

/**
 * Format timestamp to localized date/time string
 *
 * @param timestamp - ISO 8601 timestamp (null returns "N/A")
 * @param options - Optional Intl.DateTimeFormatOptions for custom formatting
 * @returns Formatted localized string
 *
 * @example
 * formatTimestamp("2025-01-05T14:30:45Z") // "Jan 5, 2025, 02:30:45 PM"
 * formatTimestamp("2025-01-05T14:30:45Z", { dateStyle: 'short' }) // "1/5/25"
 * formatTimestamp(null) // "N/A"
 */
export function formatTimestamp(
  timestamp: string | null,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!timestamp) return 'N/A';

  const date = new Date(timestamp);

  const defaultOptions: Intl.DateTimeFormatOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  };

  return date.toLocaleString('en-US', options || defaultOptions);
}

/**
 * Format timestamp to short localized date/time string (no year, no seconds)
 *
 * @param timestamp - ISO 8601 timestamp (null returns "N/A")
 * @returns Formatted string like "Jan 5, 02:30 PM"
 *
 * @example
 * formatTimestampShort("2025-01-05T14:30:45Z") // "Jan 5, 02:30 PM"
 * formatTimestampShort(null) // "N/A"
 */
export function formatTimestampShort(timestamp: string | null): string {
  return formatTimestamp(timestamp, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
