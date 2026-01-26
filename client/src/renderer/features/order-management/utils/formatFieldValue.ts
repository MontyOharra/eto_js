/**
 * Field Value Formatters
 *
 * Utilities for formatting order field values for human-readable display.
 * Handles the different data types: string, location, datetime_range, dims.
 */

import type { OrderFieldDataType } from '../types';

// =============================================================================
// Type Definitions for Field Values
// =============================================================================

/**
 * Location field value structure
 */
interface LocationValue {
  address_id: number | null;
  name: string;
  address: string;
}

/**
 * Datetime range field value structure
 */
interface DatetimeRangeValue {
  date: string;       // "2024-01-15"
  time_start: string; // "09:00"
  time_end: string;   // "17:00"
}

/**
 * Single dimension entry
 */
interface DimObject {
  length: number;
  width: number;
  height: number;
  qty: number;
  weight: number;
  dim_weight: number;
}

// =============================================================================
// Type Guards
// =============================================================================

function isLocationValue(value: unknown): value is LocationValue {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return 'name' in obj && 'address' in obj && typeof obj.name === 'string' && typeof obj.address === 'string';
}

function isDatetimeRangeValue(value: unknown): value is DatetimeRangeValue {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return 'date' in obj && 'time_start' in obj && 'time_end' in obj &&
    typeof obj.date === 'string' && typeof obj.time_start === 'string' && typeof obj.time_end === 'string';
}

function isDimObject(value: unknown): value is DimObject {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return 'length' in obj && 'width' in obj && 'height' in obj && 'qty' in obj;
}

function isDimsArray(value: unknown): value is DimObject[] {
  return Array.isArray(value) && value.length > 0 && isDimObject(value[0]);
}

// =============================================================================
// Formatters
// =============================================================================

/**
 * Format a location value for display
 * Example: "WALGREENS 3803 (22036) 2141 NORTH JOSEY LANE, CARROLLTON, TX 75006"
 * If address_id is null, shows "(NEW)" instead
 */
function formatLocation(value: LocationValue): string {
  const parts: string[] = [];

  // Company name
  if (value.name) {
    parts.push(value.name);
  }

  // Address ID - show (NEW) if null, otherwise show the ID
  if (value.address_id !== null) {
    parts.push(`(${value.address_id})`);
  } else {
    parts.push('(NEW)');
  }

  // Address - normalize newlines to comma-space
  if (value.address) {
    const normalizedAddress = value.address
      .replace(/\n/g, ', ')
      .replace(/,\s*,/g, ',')
      .trim();
    parts.push(normalizedAddress);
  }

  return parts.join(' ');
}

/**
 * Format a datetime range value for display
 * Example: "12/15/25 17:00 - 18:00"
 */
function formatDatetimeRange(value: DatetimeRangeValue): string {
  // Parse the date and format as MM/DD/YY
  const dateParts = value.date.split('-');
  if (dateParts.length === 3) {
    const year = dateParts[0].slice(-2); // Last 2 digits of year
    const month = dateParts[1];
    const day = dateParts[2];
    const formattedDate = `${month}/${day}/${year}`;

    // Format time range - always show both start and end
    return `${formattedDate} ${value.time_start} - ${value.time_end}`;
  }

  // Fallback if date parsing fails
  return `${value.date} ${value.time_start} - ${value.time_end}`;
}

/**
 * Format a single dimension object
 * Example: "2x 12x10x8 @25lbs"
 */
function formatDimObject(dim: DimObject): string {
  const qty = dim.qty ?? 1;
  const l = dim.length ?? 0;
  const w = dim.width ?? 0;
  const h = dim.height ?? 0;
  const weight = dim.weight ?? 0;

  return `${qty}x ${l}x${w}x${h} @${weight}lbs`;
}

/**
 * Format dims array for display
 * Shows each dimension on its own line (or comma-separated if compact)
 */
function formatDims(dims: DimObject[], compact = true): string {
  if (dims.length === 0) return '';

  const formatted = dims.map(formatDimObject);
  return compact ? formatted.join(', ') : formatted.join('\n');
}

// =============================================================================
// Main Formatter Function
// =============================================================================

/**
 * Format a field value for display based on its data type.
 *
 * @param value - The raw field value (can be object, string, or other)
 * @param dataType - The field's data type from metadata
 * @returns Human-readable string representation
 */
export function formatFieldValue(
  value: unknown,
  dataType?: OrderFieldDataType
): string {
  if (value === null || value === undefined) {
    return '';
  }

  // If value is already a string, try to parse it as JSON first
  let parsedValue = value;
  if (typeof value === 'string') {
    // Handle empty string
    if (value === '') {
      return '';
    }
    try {
      parsedValue = JSON.parse(value);
    } catch {
      // Not JSON, use as-is
      return value;
    }
  }

  // Handle based on detected type (or explicit dataType if provided)
  if (dataType === 'location' || isLocationValue(parsedValue)) {
    return formatLocation(parsedValue as LocationValue);
  }

  if (dataType === 'datetime_range' || isDatetimeRangeValue(parsedValue)) {
    return formatDatetimeRange(parsedValue as DatetimeRangeValue);
  }

  if (dataType === 'dims' || isDimsArray(parsedValue)) {
    return formatDims(parsedValue as DimObject[]);
  }

  // For string type or unknown, return string representation
  if (typeof parsedValue === 'string') {
    return parsedValue;
  }

  // Fallback: stringify the object
  return JSON.stringify(parsedValue);
}

/**
 * Format a field value using field metadata lookup.
 *
 * @param fieldName - The field name to look up
 * @param value - The raw field value
 * @param fieldMetadata - Map of field name to metadata
 * @returns Human-readable string representation
 */
export function formatFieldValueWithMetadata(
  fieldName: string,
  value: unknown,
  fieldMetadata?: Record<string, { data_type: OrderFieldDataType }>
): string {
  const dataType = fieldMetadata?.[fieldName]?.data_type;
  return formatFieldValue(value, dataType);
}

// Re-export for backwards compatibility
export default formatFieldValue;
