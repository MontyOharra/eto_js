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
  | 'incomplete'  // Missing required fields or has unresolved conflicts
  | 'ready'       // Has all required fields, can be created
  | 'processing'  // Being processed by HTC worker
  | 'created'     // Created in HTC database
  | 'failed'      // HTC creation failed
  | 'rejected';   // User rejected (will not be created in HTC)

/**
 * Status of a pending update
 */
export type PendingUpdateStatus =
  | 'pending'        // Awaiting user review
  | 'approved'       // User approved, applied to HTC
  | 'rejected'       // User rejected
  | 'superseded'     // Another update for same field was approved
  | 'manual_review'; // Requires manual intervention (e.g., duplicate HTC orders)

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
 * Summary of field completeness for a pending order (counts)
 */
export interface PendingOrderFieldCounts {
  /** Total required fields */
  required_field_count: number;
  /** Number of required fields that have values */
  required_fields_present: number;
  /** Total optional fields */
  optional_field_count: number;
  /** Number of optional fields that have values */
  optional_fields_present: number;
  /** Number of fields with conflicts */
  conflict_count: number;
}


/**
 * Pending order list item (for table display)
 */
export interface PendingOrderListItem {
  id: number;
  hawb: string;
  customer_id: number;
  customer_name: string | null;
  status: PendingOrderStatus;

  /** HTC order number (only set if status === 'created') */
  htc_order_number: number | null;

  /** Field completeness counts */
  required_field_count: number;
  required_fields_present: number;
  optional_field_count: number;
  optional_fields_present: number;
  conflict_count: number;

  /** Count of sub-runs that contributed */
  contributing_sub_run_count: number;

  /** Timestamps */
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601

  /** If created, when */
  htc_created_at: string | null; // ISO 8601
}

/**
 * Source information for a field value
 */
export interface FieldSource {
  history_id: number;
  sub_run_id: number | null;
  contributed_at: string; // ISO 8601
}

/**
 * A conflict option when multiple values exist for a field
 */
export interface ConflictOption {
  history_id: number;
  value: string;
  sub_run_id: number | null;
  contributed_at: string; // ISO 8601
}

/**
 * Field state type
 */
export type FieldState = 'empty' | 'set' | 'confirmed' | 'conflict';

/**
 * Detailed field information for pending order detail view
 */
export interface FieldDetail {
  name: string;
  label: string;
  required: boolean;
  value: string | null;
  state: FieldState;
  /** Present when multiple unique values exist in history (conflict or confirmed with options) */
  conflict_options: ConflictOption[] | null;
  /** Source info (for set/confirmed states) */
  source: FieldSource | null;
}

/**
 * Information about a sub-run that contributed to an order
 */
export interface ContributingSubRun {
  sub_run_id: number | null; // null for mock/test data
  run_id: number | null; // null for mock/test data
  source_type: string; // "email", "manual", or "mock"
  source_identifier: string; // email sender, "Manual Upload", or "Mock Test Data"
  pdf_filename: string;
  template_name: string | null;
  fields_contributed: string[];
  contributed_at: string; // ISO 8601
}

/**
 * Pending order detail (full view)
 */
export interface PendingOrderDetail {
  id: number;
  hawb: string;
  customer_id: number;
  customer_name: string | null;
  status: PendingOrderStatus;
  htc_order_number: number | null;

  /** All fields with their states */
  fields: FieldDetail[];

  /** Contributing sources */
  contributing_sub_runs: ContributingSubRun[];

  /** Timestamps */
  created_at: string;
  updated_at: string;
  htc_created_at: string | null;
}

// =============================================================================
// Pending Update Types (New Schema - mirrors PendingOrder)
// =============================================================================

/**
 * Pending update list item (for table display)
 * Now mirrors PendingOrderListItem - one record per HAWB
 */
export interface PendingUpdateListItem {
  id: number;
  hawb: string;
  customer_id: number;
  customer_name: string | null;
  htc_order_number: number | null; // null when multiple HTC orders exist (manual_review)
  status: PendingUpdateStatus;

  /** Field summary - count of fields being changed */
  fields_with_changes: number;
  conflict_count: number;

  /** Source tracking */
  contributing_sub_run_count: number;

  /** Timestamps */
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
  reviewed_at: string | null; // ISO 8601
}

/**
 * Detail for a single field in a pending update
 */
export interface PendingUpdateFieldDetail {
  name: string;
  label: string;
  /** Current value in HTC (for comparison) */
  current_value: string | null;
  /** Proposed new value from pipeline */
  proposed_value: string | null;
  state: FieldState;
  conflict_options: ConflictOption[] | null;
  source: FieldSource | null;
}

/**
 * Full pending update detail
 */
export interface PendingUpdateDetail {
  id: number;
  hawb: string;
  customer_id: number;
  customer_name: string | null;
  htc_order_number: number | null; // null when multiple HTC orders exist (manual_review)
  status: PendingUpdateStatus;

  /** All fields with their proposed changes */
  fields: PendingUpdateFieldDetail[];

  /** Contributing sources */
  contributing_sub_runs: ContributingSubRun[];

  /** Timestamps */
  created_at: string;
  updated_at: string;
  reviewed_at: string | null;
}

/**
 * Legacy: Grouped pending updates by order (for old UI - deprecated)
 * @deprecated Use PendingUpdateListItem[] instead
 */
export interface PendingUpdatesByOrder {
  htc_order_number: number | null;
  hawb: string;
  customer_name: string;
  updates: LegacyPendingUpdateItem[];
}

/**
 * Legacy: Old pending update item format
 * @deprecated
 */
export interface LegacyPendingUpdateItem {
  id: number;
  customer_id: number;
  hawb: string;
  htc_order_number: number | null;
  customer_name: string | null;
  field_name: string;
  field_label: string;
  proposed_value: string;
  sub_run_id: number | null;
  status: PendingUpdateStatus;
  proposed_at: string;
  reviewed_at: string | null;
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

// =============================================================================
// Unified Action Types (Pending Actions)
// =============================================================================

/**
 * Action type for pending actions
 */
export type ActionType = 'create' | 'update' | 'ambiguous';

/**
 * Status for pending actions
 */
export type PendingActionStatus =
  | 'incomplete'   // Missing required fields
  | 'conflict'     // Has unresolved field conflicts
  | 'ambiguous'    // Multiple HTC orders exist (action_type='ambiguous')
  | 'ready'        // Ready for execution
  | 'processing'   // Currently executing against HTC
  | 'completed'    // Successfully executed
  | 'failed'       // Execution failed (retryable)
  | 'rejected';    // User rejected the action

/**
 * Pending action list item from GET /api/pending-actions
 */
export interface PendingActionListItem {
  id: number;
  customer_id: number;
  customer_name: string | null;
  hawb: string;
  htc_order_number: number | null;
  action_type: ActionType;
  status: PendingActionStatus;
  required_fields_present: number;
  required_fields_total: number;
  optional_fields_present: number;
  optional_fields_total: number;
  field_names: string[];  // List of field names being updated
  conflict_count: number;
  error_message: string | null;  // Error message for failed actions
  is_read: boolean;
  created_at: string;
  updated_at: string;
  last_processed_at: string | null;
}

/**
 * Response from pending actions endpoint
 */
export interface PendingActionListResponse {
  items: PendingActionListItem[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Field value for pending action detail view.
 * Links to sub_run_id for cross-highlighting between field rows and source cards.
 */
export interface PendingActionFieldItem {
  id: number;
  field_name: string;
  value: unknown;
  is_selected: boolean;
  is_approved_for_update: boolean;
  sub_run_id: number | null; // null for user-provided values
}

/**
 * A source (sub-run) that contributed field values.
 * Used for displaying source cards and cross-highlighting with fields.
 */
export interface ContributingSourceItem {
  sub_run_id: number;
  pdf_filename: string;
  template_name: string | null;
  source_type: string; // "email", "manual", or "mock"
  source_identifier: string; // Email address or "Manual Upload"
  fields_contributed: string[];
  contributed_at: string;
}

/**
 * Data type for order fields.
 */
export type OrderFieldDataType = 'string' | 'location' | 'dims' | 'datetime_range';

/**
 * Value structure for datetime_range fields.
 * Contains date, time_start, and time_end as separate strings.
 */
export interface DatetimeRangeValue {
  date: string;        // "2024-01-15"
  time_start: string;  // "09:00"
  time_end: string;    // "17:00"
}

/**
 * Metadata for an order field.
 * Sent from backend so frontend knows how to display each field.
 */
export interface FieldMetadataItem {
  name: string;              // Field identifier (e.g., "pickup_location")
  label: string;             // Human-readable label (e.g., "Pickup Location")
  data_type: OrderFieldDataType;  // "string", "location", or "dims"
  required: boolean;         // Required for order creation?
  display_order: number;     // Order in which to display the field
}

/**
 * Execution result snapshot for completed actions.
 * Shows what values were changed when the action was executed.
 */
export interface ExecutionResult {
  action_type: ActionType;
  executed_at: string;
  approver_user_id: string | null;
  htc_order_number: number | null;
  fields_updated: string[];
  old_values: Record<string, unknown> | null;  // null for creates
  new_values: Record<string, unknown>;
}

/**
 * Full pending action detail (for both creates and updates)
 */
export interface PendingActionDetail {
  id: number;
  customer_id: number;
  customer_name: string | null;
  hawb: string;
  htc_order_number: number | null;
  action_type: ActionType;
  status: PendingActionStatus;
  required_fields_present: number;
  required_fields_total: number;
  optional_fields_present: number;
  optional_fields_total: number;
  conflict_count: number;
  error_message: string | null;
  error_at: string | null;
  is_read: boolean;
  created_at: string;
  updated_at: string;
  last_processed_at: string | null;

  /** Field values grouped by field_name */
  fields: Record<string, PendingActionFieldItem[]>;

  /** Field metadata for display (labels, required, data_type, display_order) */
  field_metadata: Record<string, FieldMetadataItem>;

  /** Contributing sources for cross-highlighting */
  contributing_sources: ContributingSourceItem[];

  /** Current HTC values for updates (null for creates) */
  current_htc_values: Record<string, unknown> | null;

  /** Execution result snapshot (for completed actions) */
  execution_result: ExecutionResult | null;
}

// Backward compatibility aliases
export type UnifiedActionListItem = PendingActionListItem;
export type UnifiedActionListResponse = PendingActionListResponse;

/**
 * Request to mark an item as read/unread
 */
export interface MarkReadRequest {
  /** The pending action ID */
  id: number;
  /** Whether to mark as read (true) or unread (false) */
  is_read: boolean;
}

/**
 * Response from mark-read endpoint
 */
export interface MarkReadResponse {
  id: number;
  is_read: boolean;
}
