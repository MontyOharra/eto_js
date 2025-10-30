/**
 * Modules API Types
 * Type definitions for the modules catalog API
 */

import type { ModuleTemplate } from "../types";

/**
 * Response from GET /modules endpoint
 */
export interface ModuleCatalogResponse {
  modules: ModuleTemplate[];
}

/**
 * Query parameters for filtering modules
 */
export interface ModulesQueryParams {
  module_kind?: "transform" | "action" | "logic" | "entry_point";
  category?: string;
  search?: string;
}

/**
 * Module execution request (for testing modules)
 */
export interface ModuleExecuteRequest {
  module_id: string;
  inputs: Record<string, any>;
  config: Record<string, any>;
  use_cache?: boolean;
}

/**
 * Module execution response
 */
export interface ModuleExecuteResponse {
  success: boolean;
  module_id: string;
  outputs: Record<string, any>;
  error: string | null;
  performance_ms: number;
  cache_used: boolean;
}
