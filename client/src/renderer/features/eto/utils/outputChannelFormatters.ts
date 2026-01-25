/**
 * Output Channel Formatting Utilities
 * Shared utilities for formatting and displaying output channel values
 * Used by SummarySuccessView and TestingStep components
 */

import type { OutputChannelType } from '../../modules/types';

// =============================================================================
// Types
// =============================================================================

export interface OutputChannelResult {
  label: string;
  channelType: string;
  value: unknown;
}

// =============================================================================
// Category Ordering
// =============================================================================

/**
 * Display order for output channel categories
 */
const CATEGORY_ORDER: string[] = ['identification', 'pickup', 'delivery', 'other'];

/**
 * Sort order for channels within each category
 * Ensures logical ordering (e.g., start before end, company before address)
 */
const CHANNEL_SORT_ORDER: Record<string, number> = {
  // Identification
  hawb: 1,
  hawb_list: 2,
  mawb: 3,
  // Pickup
  pickup_company_name: 1,
  pickup_address: 2,
  pickup_time_start: 3,
  pickup_time_end: 4,
  pickup_notes: 5,
  // Delivery
  delivery_company_name: 1,
  delivery_address: 2,
  delivery_time_start: 3,
  delivery_time_end: 4,
  delivery_notes: 5,
  // Other
  dims: 1,
  order_notes: 2,
};

/**
 * Sort output channel results by category, then by logical order within category
 */
export function sortOutputChannelsByCategory(
  channels: OutputChannelResult[],
  outputChannelTypes: OutputChannelType[] | undefined
): OutputChannelResult[] {
  if (!outputChannelTypes) return channels;

  // Build a map of channel type -> category
  const categoryMap = new Map<string, string>();
  outputChannelTypes.forEach((oct) => {
    categoryMap.set(oct.name, oct.category);
  });

  return [...channels].sort((a, b) => {
    const categoryA = categoryMap.get(a.channelType) || 'other';
    const categoryB = categoryMap.get(b.channelType) || 'other';

    // Sort by category first
    const categoryIndexA = CATEGORY_ORDER.indexOf(categoryA);
    const categoryIndexB = CATEGORY_ORDER.indexOf(categoryB);
    const effectiveCategoryIndexA = categoryIndexA === -1 ? CATEGORY_ORDER.length : categoryIndexA;
    const effectiveCategoryIndexB = categoryIndexB === -1 ? CATEGORY_ORDER.length : categoryIndexB;

    if (effectiveCategoryIndexA !== effectiveCategoryIndexB) {
      return effectiveCategoryIndexA - effectiveCategoryIndexB;
    }

    // Within same category, sort by defined order or alphabetically
    const orderA = CHANNEL_SORT_ORDER[a.channelType] ?? 999;
    const orderB = CHANNEL_SORT_ORDER[b.channelType] ?? 999;

    if (orderA !== orderB) {
      return orderA - orderB;
    }

    // Fallback to alphabetical
    return a.channelType.localeCompare(b.channelType);
  });
}

// =============================================================================
// Value Formatting
// =============================================================================

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

    return date.toLocaleString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
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
    typeof value === 'object' &&
    value !== null &&
    'height' in value &&
    'length' in value &&
    'width' in value &&
    'qty' in value &&
    'weight' in value
  );
}

/**
 * Format a single dim object as "qty - LxWxH @weightlbs"
 */
function formatDim(dim: Record<string, unknown>): string {
  const h = dim.height ?? 0;
  const l = dim.length ?? 0;
  const w = dim.width ?? 0;
  const qty = dim.qty ?? 1;
  const weight = dim.weight ?? 0;
  return `${qty} - ${l}x${w}x${h} @${weight}lbs`;
}

/**
 * Format a value for display, handling datetime objects, ISO strings, and dims
 */
export function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '-';
  }

  // Check if it's an ISO datetime string
  if (typeof value === 'string') {
    if (isISODateTime(value)) {
      return formatISODateTime(value);
    }
    return value;
  }

  // Check if it's a datetime object (has year, month, day properties)
  if (typeof value === 'object' && value !== null) {
    const obj = value as Record<string, unknown>;

    // Check for dim object
    if (isDimObject(value)) {
      return formatDim(obj);
    }

    // Check for list[dim] - array of dim objects
    if (Array.isArray(value) && value.length > 0 && isDimObject(value[0])) {
      return '[' + value.map((d) => formatDim(d as Record<string, unknown>)).join(', ') + ']';
    }

    if ('year' in obj && 'month' in obj && 'day' in obj) {
      const year = obj.year as number;
      const month = obj.month as number;
      const day = obj.day as number;

      // Format date part
      let result = `${month}/${day}/${year}`;

      // Add time if present
      if ('hour' in obj && 'minute' in obj) {
        const hour = obj.hour as number;
        const minute = obj.minute as number;
        const period = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour % 12 || 12;
        result += ` ${displayHour}:${String(minute).padStart(2, '0')} ${period}`;
      }

      return result;
    }

    // For other objects, stringify nicely
    return JSON.stringify(value);
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  return String(value);
}

/**
 * Format channel type to human-readable label
 */
export function formatChannelLabel(channelType: string): string {
  return channelType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// =============================================================================
// Styling
// =============================================================================

/**
 * Get consistent color classes for output channel display
 * Uses a single blue color for all channels for simplicity
 */
export function getChannelColor(): { bg: string; border: string; text: string } {
  return {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-300',
  };
}
