/**
 * Date Utility Functions
 * Handles timezone conversion and formatting for timestamps
 */

/**
 * Formats a UTC ISO timestamp string to the user's local timezone
 * @param utcDateString - ISO 8601 UTC timestamp (e.g., "2025-01-16T14:30:00Z")
 * @param options - Intl.DateTimeFormat options for customization
 * @returns Formatted date string in user's local timezone, or 'Never' if null/invalid
 */
export function formatUtcToLocal(
  utcDateString: string | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!utcDateString) return 'Never';

  try {
    // Fix: If the timestamp doesn't end with 'Z', add it to explicitly mark it as UTC
    // Backend sends "2025-10-24T22:17:33.114862" but JavaScript interprets it as local time
    // without the 'Z' suffix. We add 'Z' to ensure proper UTC parsing.
    let dateStringToParseAsUtc = utcDateString;
    if (!utcDateString.endsWith('Z') && !utcDateString.includes('+') && !utcDateString.includes('-', 10)) {
      // No timezone indicator present, assume UTC and add 'Z'
      dateStringToParseAsUtc = utcDateString + 'Z';
    }

    // Parse the UTC date string - JavaScript automatically converts to local time
    const date = new Date(dateStringToParseAsUtc);

    // Check if date is valid
    if (isNaN(date.getTime())) {
      console.warn(`Invalid date string: ${utcDateString}`);
      return 'Invalid Date';
    }

    // Use toLocaleString() to format in browser's local timezone
    // The Date object already represents the moment in time correctly,
    // and toLocaleString() will display it in the user's local timezone by default
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    };

    return date.toLocaleString(undefined, options || defaultOptions);
  } catch (error) {
    console.error(`Error formatting date: ${error}`);
    return 'Invalid Date';
  }
}

/**
 * Formats a UTC ISO timestamp to a short format (date only)
 * @param utcDateString - ISO 8601 UTC timestamp
 * @returns Formatted date string (e.g., "1/16/2025")
 */
export function formatUtcToLocalDate(
  utcDateString: string | null | undefined
): string {
  return formatUtcToLocal(utcDateString, {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  });
}

/**
 * Formats a UTC ISO timestamp to a relative time string (e.g., "2 hours ago")
 * @param utcDateString - ISO 8601 UTC timestamp
 * @returns Relative time string or formatted date if old
 */
export function formatUtcToRelative(
  utcDateString: string | null | undefined
): string {
  if (!utcDateString) return 'Never';

  try {
    const date = new Date(utcDateString);

    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    // Less than 1 minute
    if (diffSeconds < 60) {
      return 'Just now';
    }

    // Less than 1 hour
    if (diffMinutes < 60) {
      return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
    }

    // Less than 24 hours
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    }

    // Less than 7 days
    if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    }

    // Older than 7 days - show full date
    return formatUtcToLocal(utcDateString);
  } catch (error) {
    console.error(`Error formatting relative date: ${error}`);
    return 'Invalid Date';
  }
}
