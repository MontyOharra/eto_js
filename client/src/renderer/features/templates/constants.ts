/**
 * Template Constants
 * Centralized configuration for PDF object types including display names and colors
 */

// Object type display names
export const OBJECT_TYPE_NAMES: Record<string, string> = {
  text_word: 'Text Words',
  graphic_rect: 'Rectangles',
  graphic_line: 'Lines',
  graphic_curve: 'Curves',
  image: 'Images',
  table: 'Tables',
};

// Object type colors (hex format - single source of truth)
// Using Tailwind color palette for consistency
export const OBJECT_TYPE_COLORS: Record<string, string> = {
  text_word: '#3b82f6',    // blue-500
  graphic_rect: '#f59e0b', // amber-500
  graphic_line: '#ef4444', // red-500
  graphic_curve: '#8b5cf6', // purple-500
  image: '#ec4899',        // pink-500
  table: '#06b6d4',        // cyan-500
};

/**
 * Helper function to convert hex color to rgba with specified opacity
 */
export function hexToRgba(hex: string, opacity: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

// Pre-computed rgba colors for PDF overlays (background fill)
export const OBJECT_FILL_COLORS: Record<string, string> = {
  text_word: hexToRgba(OBJECT_TYPE_COLORS.text_word, 0.2),
  graphic_rect: hexToRgba(OBJECT_TYPE_COLORS.graphic_rect, 0.2),
  graphic_line: hexToRgba(OBJECT_TYPE_COLORS.graphic_line, 0.3),
  graphic_curve: hexToRgba(OBJECT_TYPE_COLORS.graphic_curve, 0.2),
  image: hexToRgba(OBJECT_TYPE_COLORS.image, 0.2),
  table: hexToRgba(OBJECT_TYPE_COLORS.table, 0.3),
};

// Pre-computed rgba colors for PDF overlays (border color)
export const OBJECT_BORDER_COLORS: Record<string, string> = {
  text_word: hexToRgba(OBJECT_TYPE_COLORS.text_word, 0.6),
  graphic_rect: hexToRgba(OBJECT_TYPE_COLORS.graphic_rect, 0.6),
  graphic_line: hexToRgba(OBJECT_TYPE_COLORS.graphic_line, 0.8),
  graphic_curve: hexToRgba(OBJECT_TYPE_COLORS.graphic_curve, 0.6),
  image: hexToRgba(OBJECT_TYPE_COLORS.image, 0.6),
  table: hexToRgba(OBJECT_TYPE_COLORS.table, 0.7),
};
