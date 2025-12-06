/**
 * Domain types for Order Management feature
 *
 * Handles:
 * - Pending Orders (incomplete orders awaiting more data)
 * - Pending Updates (changes to existing orders awaiting approval)
 * - Order History (timeline of how runs contributed to an order)
 */

// =============================================================================
// Enums & Status Types
// =============================================================================

/**
 * Status of a pending order
 */
export type PendingOrderStatus =
  | 'incomplete'  // Missing required fields
  | 'ready'       // Has all required fields, can be created
  | 'created';    // Created in HTC database

/**
 * Status of a pending update
 */
export type PendingUpdateStatus =
  | 'pending'     // Awaiting user review
  | 'approved'    // User approved, applied to HTC
  | 'rejected'    // User rejected
  | 'superseded'; // Another update for same field was approved

/**
 * Type of contribution a run made to an order
 */
export type ContributionType =
  | 'created_pending'   // Run created the pending order
  | 'added_fields'      // Run added fields to pending order
  | 'overwrote_fields'  // Run overwrote fields in pending order
  | 'triggered_creation'// Run completed the order, triggering HTC creation
  | 'proposed_update';  // Run proposed an update to existing HTC order

// =============================================================================
// Pending Order Types
// =============================================================================

/**
 * Summary of which fields are present/missing on a pending order
 */
export interface PendingOrderFieldStatus {
  /** Fields that have been provided */
  present: string[];
  /** Required fields that are still missing */
  missing_required: string[];
  /** Optional fields that are missing (informational) */
  missing_optional: string[];
}

/**
 * A run that contributed data to a pending order
 */
export interface ContributingRun {
  run_id: number;
  sub_run_id: number;
  contributed_at: string; // ISO 8601
  fields_contributed: string[];
  contribution_type: ContributionType;
  /** Template name used for extraction */
  template_name: string | null;
  /** PDF filename */
  pdf_filename: string;
}

/**
 * Pending order list item (for table display)
 */
export interface PendingOrderListItem {
  id: number;
  hawb: string;
  customer_id: number;
  customer_name: string;
  status: PendingOrderStatus;

  /** HTC order number (only set if status === 'created') */
  htc_order_number: number | null;

  /** Field completeness info */
  field_status: PendingOrderFieldStatus;

  /** Count of runs that contributed */
  contributing_run_count: number;

  /** Timestamps */
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601

  /** If created, when */
  htc_created_at: string | null; // ISO 8601
}

/**
 * Pending order detail (full view)
 */
export interface PendingOrderDetail {
  id: number;
  hawb: string;
  customer_id: number;
  customer_name: string;
  status: PendingOrderStatus;
  htc_order_number: number | null;

  /** All field values currently set */
  field_values: Record<string, unknown>;

  /** Field completeness info */
  field_status: PendingOrderFieldStatus;

  /** All runs that contributed to this order */
  contributing_runs: ContributingRun[];

  /** Timestamps */
  created_at: string;
  updated_at: string;
  htc_created_at: string | null;
}

// =============================================================================
// Pending Update Types
// =============================================================================

/**
 * Pending update list item (for table display)
 */
export interface PendingUpdateListItem {
  id: number;

  /** The HTC order being updated */
  htc_order_number: number;
  hawb: string;

  /** The field being updated */
  field_name: string;
  field_label: string; // Human-readable label

  /** Values */
  current_value: string | null;
  proposed_value: string;

  /** Source run info */
  source_run_id: number;
  source_sub_run_id: number;
  source_pdf_filename: string;
  source_template_name: string | null;

  /** Timestamps */
  proposed_at: string; // ISO 8601 - when the form was received

  /** Status */
  status: PendingUpdateStatus;

  /** Review info (if reviewed) */
  reviewed_by: string | null;
  reviewed_at: string | null; // ISO 8601
}

/**
 * Grouped pending updates by order (for UI)
 */
export interface PendingUpdatesByOrder {
  htc_order_number: number;
  hawb: string;
  customer_name: string;
  updates: PendingUpdateListItem[];
}

// =============================================================================
// Order History Types
// =============================================================================

/**
 * A single event in the order history timeline
 */
export interface OrderHistoryEvent {
  id: number;
  event_type: ContributionType;
  timestamp: string; // ISO 8601

  /** Run that caused this event */
  run_id: number;
  sub_run_id: number;
  pdf_filename: string;
  template_name: string | null;

  /** What changed */
  fields_affected: string[];

  /** For overwrites, what was the previous value */
  previous_values: Record<string, unknown> | null;
  new_values: Record<string, unknown>;

  /** Additional context */
  notes: string | null;
}

/**
 * Full order history (timeline view)
 */
export interface OrderHistory {
  /** Order identifiers */
  hawb: string;
  htc_order_number: number | null;
  customer_id: number;
  customer_name: string;

  /** Current status */
  status: PendingOrderStatus;

  /** Timeline of events */
  events: OrderHistoryEvent[];

  /** Current field values */
  current_field_values: Record<string, unknown>;

  /** Pending updates awaiting approval */
  pending_updates: PendingUpdateListItem[];
}

// =============================================================================
// Filter & Sort Types
// =============================================================================

export type PendingOrderSortOption =
  | 'created_at-desc'
  | 'created_at-asc'
  | 'updated_at-desc'
  | 'updated_at-asc'
  | 'hawb-asc'
  | 'hawb-desc';

export type PendingUpdateSortOption =
  | 'proposed_at-desc'
  | 'proposed_at-asc'
  | 'order_number-asc'
  | 'order_number-desc';
