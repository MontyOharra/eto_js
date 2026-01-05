"""
Database VIEW definitions.

Views are defined as raw SQL strings for simplicity.
These are executed by database_creator.py after tables are created.
"""

# =============================================================================
# Unified Actions View
# =============================================================================
# Combines pending_orders (creates) and pending_updates (updates) into a single
# queryable view for the Orders page unified list.
#
# This enables efficient filtering, sorting, and pagination across both tables
# using a single SQL query instead of fetching from both tables separately.

UNIFIED_ACTIONS_VIEW = """
CREATE OR ALTER VIEW unified_actions_view AS

-- Pending Orders (type = 'create')
SELECT
    'create' AS type,
    id,
    customer_id,
    hawb,
    htc_order_number,
    status,
    is_read,
    error_message,
    last_processed_at,
    created_at,
    updated_at
FROM pending_orders

UNION ALL

-- Pending Updates (type = 'update')
SELECT
    'update' AS type,
    id,
    customer_id,
    hawb,
    htc_order_number,
    status,
    is_read,
    NULL AS error_message,
    last_processed_at,
    created_at,
    updated_at
FROM pending_updates
"""

# List of all views to create (in order)
ALL_VIEWS = [
    ("unified_actions_view", UNIFIED_ACTIONS_VIEW),
]
