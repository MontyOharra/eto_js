/**
 * Module Catalog Types
 * Domain types for module templates and their metadata
 */

// ============================================================================
// I/O Shape System
// ============================================================================

/**
 * Type rule for a node group
 * Defines allowed types and type variables for type unification
 */
export interface NodeTypeRule {
  allowed_types?: string[];  // per-pin whitelist; user picks independently
  type_var?: string;         // e.g., "T" (unifies across pins)
}

/**
 * Node group definition
 * Describes a collection of related input/output nodes
 *
 * Static nodes: min_count === max_count === 1
 * Dynamic nodes: max_count > 1 or undefined (unlimited)
 */
export interface NodeGroup {
  label: string;
  min_count: number;
  max_count?: number;        // undefined = unlimited
  typing: NodeTypeRule;
}

/**
 * I/O side shape (inputs or outputs)
 * Ordered array of node groups
 */
export interface IOSideShape {
  nodes: NodeGroup[];
}

/**
 * Complete I/O shape for a module
 * Defines the module's input and output signature
 */
export interface IOShape {
  inputs: IOSideShape;
  outputs: IOSideShape;
  type_params: Record<string, string[]>; // declare domains for type variables
}

/**
 * Module metadata
 * Contains I/O shape and other module-level metadata
 */
export interface ModuleMeta {
  io_shape: IOShape;
}

// ============================================================================
// Module Template
// ============================================================================

/**
 * Module template definition
 * Represents a module type available in the catalog
 * This is the frontend representation of backend Module type
 */
export interface ModuleTemplate {
  id: string;  // Identifier (e.g., "text_cleaner") - used for display/lookup
  module_id: number;  // Database PK - sent to backend when creating module instances
  version: string;
  title: string;
  description: string;
  kind: string;
  color: string;
  category: string;
  meta: ModuleMeta;
  config_schema: any;
}

// ============================================================================
// Output Channel Types
// ============================================================================

/**
 * Output channel type definition
 * Represents an output channel available for pipeline outputs
 */
export interface OutputChannelType {
  name: string;
  label: string;
  data_type: string;  // "str", "int", "float", "datetime", "list[str]"
  category: string;   // "identification", "pickup", "delivery", "cargo", "other"
  description?: string;
  is_required: boolean;
}
