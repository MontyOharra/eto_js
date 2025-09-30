/**
 * Utility for generating unique 4-character alphanumeric IDs
 */

// Track all used IDs to ensure uniqueness
const usedIds = new Set<string>();

/**
 * Generate a unique 4-character alphanumeric ID
 * @param prefix Optional prefix (not counted in the 4 characters)
 * @returns Unique ID string
 */
export function generateUniqueId(prefix: string = ''): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let id: string;

  // Keep generating until we get a unique ID
  do {
    id = prefix;
    for (let i = 0; i < 4; i++) {
      id += chars[Math.floor(Math.random() * chars.length)];
    }
  } while (usedIds.has(id));

  usedIds.add(id);
  return id;
}

/**
 * Clear all tracked IDs (useful for testing or resetting)
 */
export function clearUsedIds(): void {
  usedIds.clear();
}

/**
 * Check if an ID is already in use
 */
export function isIdUsed(id: string): boolean {
  return usedIds.has(id);
}

/**
 * Manually register an ID as used (useful when loading existing pipelines)
 */
export function registerUsedId(id: string): void {
  usedIds.add(id);
}