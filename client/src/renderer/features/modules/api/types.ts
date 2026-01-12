/**
 * Modules API Types
 * Backend response types for the modules catalog API
 */

/**
 * Module catalog entry from backend API
 * Matches server/src/api/schemas/modules.py::ModuleResponse
 */
export interface Module {
  id: number;  // Database primary key
  identifier: string;  // e.g., "text_cleaner"
  version: string;
  name: string;
  description: string | null;
  module_kind: string;  // "transform", "action", "logic", "comparator"
  meta: any;  // Module I/O metadata
  config_schema: any;  // JSON schema for module configuration
  color: string;
  category: string;
}

/**
 * Query parameters for filtering modules
 * Used with GET /modules endpoint
 */
export interface ModulesQueryParams {
  module_kind?: "transform" | "action" | "logic" | "entry_point";
  category?: string;
  search?: string;
}
