# Feature: Improved Attachment Handling

## Overview

Change attachment logic to capture ALL PDFs from source emails, not just the ones that contributed extracted data. This ensures forms like BOLs, PODs, and commercial invoices get attached even if they didn't have data extracted.

## Current Behavior (Problem)

```
_get_pdf_sources_for_action():
    pending_action_fields → output_execution → sub_run → run → pdf_file
```

**Problem:** Only attaches PDFs that contributed field data. Misses other attachments from the same email that may be relevant (e.g., a BOL that didn't have a matching template but should still be attached).

## Desired Behavior

```
_get_pdf_sources_for_action():
    1. pending_action_fields → output_execution → sub_run → run
    2. For each run with source_email_id:
       - Get ALL runs with that same source_email_id
       - Get ALL pdf_files from those runs
    3. Return deduplicated list of all PDFs from contributing emails
```

**Result:** If an email had 5 PDF attachments but only 2 matched templates and contributed data, all 5 PDFs get attached to the HTC order.

## Implementation

### 1. Add Repository Method

**File:** `server/src/features/eto_runs/repository.py`

```python
def get_by_source_email_id(self, source_email_id: int) -> list[EtoRunModel]:
    """Get all runs that came from a specific email."""
    return self._session.query(EtoRunModel).filter(
        EtoRunModel.source_email_id == source_email_id
    ).all()
```

### 2. Update `_get_pdf_sources_for_action`

**File:** `server/src/features/order_management/service.py`

```python
def _get_pdf_sources_for_action(self, pending_action_id: int) -> list[PdfSource]:
    """
    Get PDF file information from all emails that contributed to this pending action.

    Changed from previous behavior: Now returns ALL PDFs from contributing emails,
    not just the ones that had data extracted. This ensures forms like BOLs, PODs,
    etc. get attached even if they didn't match a template.

    Data path:
      pending_action_fields → output_execution → sub_run → run → source_email
      → ALL runs with that email → ALL pdf_files

    Args:
        pending_action_id: ID of the pending action

    Returns:
        List of PdfSource objects with PDF file info (deduplicated by pdf_file_id)
    """
    # Get all fields for this action
    fields = self.pending_action_field_repo.get_fields_for_action(pending_action_id)

    # Get unique output_execution_ids (excluding None for user-provided values)
    output_execution_ids = set(
        f.output_execution_id for f in fields if f.output_execution_id is not None
    )

    # Collect unique source_email_ids from contributing runs
    source_email_ids: set[int] = set()

    for output_execution_id in output_execution_ids:
        output_execution = self.output_execution_repo.get_by_id(output_execution_id)
        if not output_execution:
            continue

        sub_run = self.eto_sub_run_repo.get_by_id(output_execution.sub_run_id)
        if not sub_run:
            continue

        run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)
        if not run or not run.source_email_id:
            continue

        source_email_ids.add(run.source_email_id)

    # Get ALL runs from contributing emails
    seen_pdf_ids: set[int] = set()
    pdf_sources: list[PdfSource] = []

    for email_id in source_email_ids:
        # Get all runs that came from this email
        email_runs = self.eto_run_repo.get_by_source_email_id(email_id)

        for run in email_runs:
            if run.pdf_file_id in seen_pdf_ids:
                continue
            seen_pdf_ids.add(run.pdf_file_id)

            pdf_file = self.pdf_file_repo.get_by_id(run.pdf_file_id)
            if not pdf_file:
                logger.warning(f"PDF file {run.pdf_file_id} not found for run {run.id}")
                continue

            pdf_sources.append(PdfSource(
                pdf_file_id=pdf_file.id,
                original_filename=pdf_file.original_filename,
                file_path=pdf_file.file_path,
            ))

    logger.debug(
        f"Found {len(pdf_sources)} PDF files from {len(source_email_ids)} emails "
        f"for pending action {pending_action_id}"
    )
    return pdf_sources
```

## Edge Cases

1. **Manual uploads**: No `source_email_id`, so no additional PDFs to collect. Only the directly contributing PDF is attached (current behavior preserved via fallback).

2. **Multiple emails contributing to same action**: All PDFs from all contributing emails are collected and attached.

3. **Email with many PDFs but only one matched**: All PDFs from the email are attached (desired behavior per user).

4. **Same PDF in multiple actions**: Each action attaches independently, HTC handles deduplication if needed.

## Checklist

### Backend
- [ ] Add `get_by_source_email_id()` method to `EtoRunRepository`
- [ ] Update `_get_pdf_sources_for_action()` to collect all PDFs from source emails
- [ ] Add fallback for manual uploads (no source_email_id)
- [ ] Update logging to show email count + PDF count

### Testing
- [ ] Test with email that has 1 PDF (baseline)
- [ ] Test with email that has multiple PDFs, only some matched templates
- [ ] Test with manual upload (should work as before)
- [ ] Test with multiple emails contributing to same action
- [ ] Verify HTC receives all expected attachments
