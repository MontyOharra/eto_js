/**
 * ID Generator Utilities
 * Generates short, readable IDs for pipeline elements
 */

const ALPHANUMERIC = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';

/**
 * Generate a random alphanumeric string of specified length
 */
function generateRandomString(length: number): string {
  let result = '';
  for (let i = 0; i < length; i++) {
    result += ALPHANUMERIC.charAt(Math.floor(Math.random() * ALPHANUMERIC.length));
  }
  return result;
}

/**
 * Generate a module ID in format M{xx}
 * Example: Mab, M3x, MZq
 */
export function generateModuleId(): string {
  return `M${generateRandomString(2)}`;
}

/**
 * Generate an entry point ID in format E{xx}
 * Example: Eab, E3x, EZq
 */
export function generateEntryPointId(): string {
  return `E${generateRandomString(2)}`;
}

/**
 * Generate a node (pin) ID in format N{xxx}
 * Example: Nabc, N3xz, NZqW
 */
export function generateNodeId(): string {
  return `N${generateRandomString(3)}`;
}
