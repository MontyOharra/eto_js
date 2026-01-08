"""
Order Management Mappers
Convert between service domain types and API Pydantic models
"""
from typing import Dict, List, Optional

from features.order_management_old.service import (
    PendingOrderDetail as PendingOrderDetailDomain,
    FieldWithOptions,
    FieldOption,
    ContributingSource,
)
from server.src.api.schemas.order_management_old import (
    PendingOrderDetail as PendingOrderDetailSchema,
    FieldDetail,
    FieldSource,
    ConflictOption,
    ConflictOptionSource,
    ContributingSubRun,
)


def map_pending_order_detail_to_api(
    domain: PendingOrderDetailDomain,
) -> PendingOrderDetailSchema:
    """
    Convert service PendingOrderDetail to API schema.

    Handles:
    - datetime to ISO string conversion
    - float order number to int conversion (avoids precision issues)
    - Field options mapping based on state
    """
    return PendingOrderDetailSchema(
        id=domain.id,
        hawb=domain.hawb,
        customer_id=domain.customer_id,
        customer_name=domain.customer_name,
        status=domain.status,
        htc_order_number=int(domain.htc_order_number) if domain.htc_order_number is not None else None,
        htc_created_at=domain.htc_created_at.isoformat() if domain.htc_created_at else None,
        error_message=domain.error_message,
        error_at=domain.error_at.isoformat() if domain.error_at else None,
        fields=[_map_field_with_options(f) for f in domain.fields],
        contributing_sub_runs=[_map_contributing_source(s) for s in domain.contributing_sources],
        created_at=domain.created_at.isoformat(),
        updated_at=domain.updated_at.isoformat(),
    )


def _map_field_with_options(field: FieldWithOptions) -> FieldDetail:
    """Convert service FieldWithOptions to API FieldDetail."""
    conflict_options = None
    source = None

    # Check if there are multiple unique values in history
    unique_values = set(opt.value for opt in field.options) if field.options else set()
    has_multiple_values = len(unique_values) > 1

    # Always provide conflict_options when there are multiple unique values
    # This allows the frontend to show a dropdown even after a value is confirmed
    # Options are deduplicated by value, with all contributing sources grouped together
    if has_multiple_values:
        # Group options by value
        by_value: Dict[str, List[FieldOption]] = {}
        for opt in field.options:
            if opt.value not in by_value:
                by_value[opt.value] = []
            by_value[opt.value].append(opt)

        # Build deduplicated conflict options
        conflict_options = []
        for value, opts in by_value.items():
            # Sort sources by contributed_at (oldest first)
            sorted_opts = sorted(opts, key=lambda o: o.contributed_at)

            sources = [
                ConflictOptionSource(
                    history_id=opt.history_id,
                    sub_run_id=opt.sub_run_id,
                    contributed_at=opt.contributed_at.isoformat(),
                )
                for opt in sorted_opts
            ]

            conflict_options.append(ConflictOption(
                value=value,
                sources=sources,
                history_id=sorted_opts[0].history_id,  # Use first source's history_id for selection
            ))

    # Provide source info for set/confirmed states
    if field.state in ("set", "confirmed") and field.options:
        # Find the selected option or use the first one
        selected_opt = next(
            (opt for opt in field.options if opt.is_selected),
            field.options[0] if field.options else None
        )
        if selected_opt:
            source = FieldSource(
                history_id=selected_opt.history_id,
                sub_run_id=selected_opt.sub_run_id,
                contributed_at=selected_opt.contributed_at.isoformat(),
            )

    # Convert value to string if not None (schema expects str | None)
    value_str = str(field.current_value) if field.current_value is not None else None

    return FieldDetail(
        name=field.name,
        label=field.label,
        required=field.required,
        value=value_str,
        state=field.state,
        conflict_options=conflict_options,
        source=source,
    )


def _map_contributing_source(source: ContributingSource) -> ContributingSubRun:
    """Convert service ContributingSource to API ContributingSubRun."""
    return ContributingSubRun(
        sub_run_id=source.sub_run_id,
        run_id=source.run_id,
        source_type=source.source_type,
        source_identifier=source.source_identifier,
        pdf_filename=source.pdf_filename,
        template_name=source.template_name,
        fields_contributed=source.fields_contributed,
        contributed_at=source.processed_at.isoformat(),
    )
