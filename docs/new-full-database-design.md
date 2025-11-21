````markdown
# ETO Multi-Template Matching & Sub-Run Redesign

This document describes the **new ETO processing model** we’ve been designing, so you (Claude) can reason about it, generate code, and help refactor the existing system.

The focus is on:

- How **template matching** works at the **overall PDF level**
- How **sub-runs** work per **page set** inside a PDF
- How **statuses and workers** should behave
- How the new design maps to the **database schema** (dbdiagram + SQLAlchemy models)

---

## 1. High-Level Goals

1. **One top-level run per PDF**  
   Each PDF gets a single `eto_run` record that represents the **overall orchestration**:
   - Run template matching over the **entire document**
   - Spawn **sub-runs** for each logical embedded document (page set)
   - Drive the process until all sub-runs are finalized

2. **Multiple sub-runs per PDF**  
   Each **sub-run** (`eto_sub_run`) represents a group of pages:
   - Either matched to a known template
   - Or an “unmatched group” of pages that still need a template
   - Each sub-run has its **own status and processing**

3. **Sub-runs are the unit of reprocessing**  
   - We **do not** reprocess the entire ETO run anymore.
   - We reprocess **individual sub-runs** (e.g., after fixing a template or code).

4. **Parent run status ≠ sub-run status**  
   - **Parent (`eto_run`) status** answers:  
     “Did the orchestration and system-level work complete successfully, or did something critical fail?”
   - **Sub-run (`eto_sub_run`) status** answers:  
     “For this page set, did we successfully run extraction + pipeline, or did it fail / need template / get skipped?”

5. **Template matching runs once per PDF**  
   - Template matching is **only** done at the parent run level, over the full PDF.
   - Sub-runs, once created, do **not** perform template matching again—they only handle extraction + pipeline.

---

## 2. Key Entities & Relationships

### 2.1 Parent run: `eto_runs` (one per PDF)

- **Purpose:** Orchestrates the entire life cycle of ETO processing for a single `pdf_files` row.
- **Key relationships:**
  - `eto_runs.pdf_file_id → pdf_files.id`
  - `eto_runs` has many `eto_sub_runs`

**Fields (conceptual):**

- `id` – primary key, one per ETO run
- `pdf_file_id` – FK to the PDF being processed
- `status` – **orchestration-level status** (see enums)
- `processing_step` – which stage we’re in:
  - `template_matching`
  - `sub_runs`
- `error_type`, `error_message`, `error_details` – system-level failure info
- `started_at`, `completed_at`, `created_at`, `updated_at`

**Semantic rules:**

- `status` is about **system/orchestration health**, not whether business logic “succeeded” for each page.
- Even if **every sub-run fails**, the parent ETO run can still end with `status = success` (meaning: “we did the job and recorded all failures”).

---

### 2.2 Sub-runs: `eto_sub_runs` (one per page set)

- **Purpose:** Represent the ETO process for a **subset of pages** in a PDF.
- **Key relationships:**
  - `eto_sub_runs.eto_run_id → eto_runs.id`
  - `eto_sub_runs.template_version_id → pdf_template_versions.id` (optional)

**Fields (conceptual):**

- `id` – primary key
- `eto_run_id` – FK to parent `eto_runs`
- `matched_pages` – JSON-encoded list of page numbers (e.g., `"[1,2,3]"`)
- `template_version_id` – FK to matched template version (nullable)
  - `NULL` in the “needs template” unmatched group
- `status` – **sub-run status** (see enums)
- `sequence` – optional ordering within the parent run
- `is_unmatched_group` – `true` for the **single unmatched pages group**
- `error_type`, `error_message`, `error_details`
- `started_at`, `completed_at`, `created_at`, `updated_at`

**Important behaviors:**

- **Matched pages:**  
  Sub-runs with a template:
  - `template_version_id` is set
  - `status` initially `not_started`
- **Unmatched group:**
  - All unmatched pages are grouped into **one** sub-run
  - `matched_pages` contains all unmatched pages, e.g. `"[2,5,6]"`
  - `template_version_id = NULL`
  - `status = needs_template`
  - `is_unmatched_group = true`
- **Reprocessing:**
  - Only sub-runs are reprocessed (by toggling their status back to `not_started`).
  - Parent run is not reprocessed.

---

### 2.3 Stage tables per sub-run

We keep per-sub-run stage tables that mirror the existing design but hang off `eto_sub_runs` instead of `eto_runs`:

1. **Extraction:**

   - Table: `eto_sub_run_extractions`
   - FK: `sub_run_id → eto_sub_runs.id`
   - Fields: `status` (`processing`, `success`, `failure`), `extracted_data`, `error_message`, timestamps.

2. **Pipeline execution:**

   - Table: `eto_sub_run_pipeline_executions`
   - FK: `sub_run_id → eto_sub_runs.id`
   - Fields: `status`, `executed_actions`, `error_message`, timestamps.

3. **Pipeline steps:**

   - Table: `eto_sub_run_pipeline_execution_steps`
   - FK: `pipeline_execution_id → eto_sub_run_pipeline_executions.id`
   - Fields: `module_instance_id`, `step_number`, `inputs`, `outputs`, `error`, timestamps.

These correspond to the current `eto_run_extractions`, `eto_run_pipeline_executions`, and `eto_run_pipeline_execution_steps`, but **scoped to sub-runs**.

---

## 3. Status Enums & Semantics

### 3.1 Parent orchestration status: `ETO_MASTER_STATUS`

Used by `eto_runs.status`:

- `not_started`  
  PDF received, template matching not yet started.
- `processing`  
  Template matching and/or sub-run processing currently in progress.
- `success`  
  Orchestration completed:
  - Template matching ran successfully.
  - All sub-runs are in terminal states (no `not_started` or `processing` remaining).
- `failure`  
  **Critical** orchestration failure:
  - Template matcher crashed irrecoverably.
  - DB or infrastructure error prevented the job from finishing.
  - Invariant problems (e.g., invalid page coverage) caused an intentional abort.

> **Note:** *Cancelled* runs are not tracked as an enum. They are simply **deleted from the DB** when the user decides a PDF/run is irrelevant.

---

### 3.2 Parent processing step: `ETO_RUN_PROCESSING_STEP`

Used by `eto_runs.processing_step`:

- `template_matching`  
  The system is running the template-matching algorithm over the entire PDF.
- `sub_runs`  
  Template matching has completed and sub-runs have been created. The system is now processing sub-runs (extraction + pipeline per page set).

This is a “stage hint” to help the worker logic and UI, not a complex state machine.

---

### 3.3 Sub-run status: `ETO_RUN_STATUS`

Used by `eto_sub_runs.status`. This is basically the original ETO run status semantics, now scoped to page sets:

- `not_started`  
  Sub-run is ready to be picked up by workers.
- `processing`  
  Extraction and/or pipeline execution running for this sub-run.
- `success`  
  Sub-run completed successfully.
- `failure`  
  Sub-run failed (e.g., extraction or pipeline error).  
  This is a **business-level failure**, not necessarily a critical system failure.
- `needs_template`  
  Sub-run represents pages that don’t match any known template.  
  Requires a user to design a template (e.g., using one of the pages).
- `skipped`  
  User explicitly skipped this sub-run (e.g., not relevant for the business).

---

### 3.4 Stage status: `ETO_STEP_STATUS`

Used by:

- `eto_sub_run_extractions.status`
- `eto_sub_run_pipeline_executions.status`

Values:

- `processing`
- `success`
- `failure`

These are **stage-level** statuses, not orchestration statuses.

---

## 4. End-to-End Processing Flow

### 4.1 Step 1 – PDF ingest

1. A PDF is received by the system (from an email attachment, etc.).
2. System creates a `pdf_files` record.
3. System creates a new **parent ETO run**:

   ```text
   eto_runs:
     pdf_file_id = <pdf.id>
     status = not_started
     processing_step = template_matching
````

This is the only place a new `eto_runs` record is created.

---

### 4.2 Step 2 – Template matching worker

A **template-matching worker** finds ETO runs that need template matching:

* Query: `SELECT * FROM eto_runs WHERE status = 'not_started' AND processing_step = 'template_matching'`

For each run:

1. Set `status = processing`.
2. Run the template-matching algorithm over the **entire PDF** (all pages).

Based on the result, it builds:

* A set of **matched segments** (page lists + chosen template versions).
* A set of **unmatched pages**.

---

### 4.3 Step 3 – Creating sub-runs (matched + unmatched)

For each **matched** page set:

* Create a sub-run:

  ```text
  eto_sub_runs:
    eto_run_id = <eto_run.id>
    matched_pages = "[...]"          // JSON array of pages
    template_version_id = <template_version.id>
    status = not_started
    is_unmatched_group = false
  ```

For all **unmatched** pages:

* Create exactly **one** “unmatched group” sub-run:

  ```text
  eto_sub_runs:
    eto_run_id = <eto_run.id>
    matched_pages = "[<all unmatched pages>]"
    template_version_id = NULL
    status = needs_template
    is_unmatched_group = true
  ```

After sub-runs are created:

* `eto_runs.processing_step = sub_runs`
* `eto_runs.status` remains `processing`.

**Important invariants:**

* At most **one** sub-run per `eto_run` has `is_unmatched_group = true`.
* That sub-run aggregates **all unmatched pages** at the time of template matching.

---

### 4.4 Step 4 – Sub-run processing

#### 4.4.1 For matched sub-runs

Workers responsible for extraction + pipeline look for:

* `eto_sub_runs.status = 'not_started'`
* `template_version_id IS NOT NULL`

When they pick up a sub-run:

1. Set `status = processing`.
2. Create an `eto_sub_run_extractions` record and run extraction.
3. Create an `eto_sub_run_pipeline_executions` record and run the pipeline, logging steps in `eto_sub_run_pipeline_execution_steps`.
4. Set sub-run `status` to either:

   * `success`
   * `failure`

**Reprocessing**:

* If a sub-run failed, a user or system can set `status` back to `not_started`.
* The worker picks it up again.
* Parent `eto_runs` does not need to change statuses for normal reprocessing.

#### 4.4.2 For needs-template sub-run

The UI shows the unmatched group as a single sub-run:

* `status = needs_template`
* `matched_pages` contains all unmatched pages.
* `is_unmatched_group = true`

User interaction:

1. The user selects one or more pages from the unmatched group to design a new template.
2. After a template is created and activated:

   * Create new **matched sub-runs** for the pages that now have a template.
   * Update the unmatched group’s `matched_pages` to exclude those pages.
   * If no pages remain unmatched, you can:

     * Set the unmatched group to `skipped`, or
     * Delete the unmatched sub-run.

Later, the newly created matched sub-runs (with `status = not_started`) are picked up by the sub-run workers like any other.

---

### 4.5 Step 5 – Parent run completion

The parent ETO run’s `status` is about orchestration:

* Parent is **complete** when:

  * Template matching has been performed (we are in the `sub_runs` stage).
  * **All** sub-runs are in **terminal** states:

    * `success`, `failure`, `needs_template`, or `skipped`
    * No `not_started` or `processing` remain.

At that point, the system sets:

* `eto_runs.status = success`
* `eto_runs.completed_at = NOW()`

Even if some sub-runs are `failure` or `needs_template`, the parent `status = success` simply means:

> *“We orchestrated everything and recorded the results; nothing critical crashed.”*

If something critical happens (e.g. template matching crashes, invariant failure, etc.):

* `eto_runs.status = failure`
* `error_*` fields are set.

---

## 5. Deletion & “Useless Templates”

### 5.1 Deleting ETO runs

If a user decides a particular PDF/run is irrelevant:

* They may delete the parent `eto_run`.
* This should cascade to:

  * `eto_sub_runs`
  * `eto_sub_run_extractions`
  * `eto_sub_run_pipeline_executions`
  * `eto_sub_run_pipeline_execution_steps`

We do **not** track a special “cancelled” state in the enums; deletion is the signal.

---

### 5.2 “Useless templates” (future feature)

Later, we may add a notion of **“ignore” templates**, e.g., forms that are routinely received but never used.

Conceptual extension:

```text
pdf_templates.behavior:
  - normal
  - ignore  // matched, but we don’t want to process it
```

* If a template with `behavior = ignore` matches a page set:

  * Either:

    * Automatically create a sub-run and mark it `skipped`, or
    * Don’t create a sub-run at all, depending on how much auditability is desired.

This is not required for the first iteration, but the schema design is compatible with it.

---

## 6. DB Schema Overview (ETO-related Tables Only)

For quick reference, here’s the conceptual dbdiagram-style view of **ETO tables only** (names and enums may be slightly adapted in final implementation):

```dbml
Enum ETO_MASTER_STATUS {
  not_started
  processing
  success
  failure
}

Enum ETO_RUN_PROCESSING_STEP {
  template_matching
  sub_runs
}

Enum ETO_RUN_STATUS {
  not_started
  processing
  success
  failure
  needs_template
  skipped
}

Enum ETO_STEP_STATUS {
  processing
  success
  failure
}

Table eto_runs {
  id              int [pk, increment]
  pdf_file_id     int [not null, ref: > pdf_files.id]
  status          ETO_MASTER_STATUS [not null, default: 'not_started']
  processing_step ETO_RUN_PROCESSING_STEP
  error_type      varchar(50)
  error_message   text
  error_details   text
  started_at      datetime
  completed_at    datetime
  created_at      datetime [not null]
  updated_at      datetime [not null]
}

Table eto_sub_runs {
  id                  int [pk, increment]
  eto_run_id          int [not null, ref: > eto_runs.id]
  matched_pages       text [not null]           // JSON array
  template_version_id int [ref: > pdf_template_versions.id]
  status              ETO_RUN_STATUS [not null, default: 'not_started']
  sequence            int
  is_unmatched_group  boolean [default: false]
  error_type          varchar(50)
  error_message       text
  error_details       text
  started_at          datetime
  completed_at        datetime
  created_at          datetime [not null]
  updated_at          datetime [not null]
}

Table eto_sub_run_extractions {
  id             int [pk, increment]
  sub_run_id     int [not null, ref: > eto_sub_runs.id]
  status         ETO_STEP_STATUS [not null, default: 'processing']
  extracted_data text
  error_message  text
  started_at     datetime
  completed_at   datetime
  created_at     datetime [not null]
  updated_at     datetime [not null]
}

Table eto_sub_run_pipeline_executions {
  id               int [pk, increment]
  sub_run_id       int [not null, ref: > eto_sub_runs.id]
  status           ETO_STEP_STATUS [not null, default: 'processing']
  executed_actions text
  error_message    text
  started_at       datetime
  completed_at     datetime
  created_at       datetime [not null]
  updated_at       datetime [not null]
}

Table eto_sub_run_pipeline_execution_steps {
  id                    int [pk, increment]
  pipeline_execution_id int [not null, ref: > eto_sub_run_pipeline_executions.id]
  module_instance_id    varchar(100) [not null]
  step_number           int [not null]
  inputs                text
  outputs               text
  error                 text
  created_at            datetime [not null]
  updated_at            datetime [not null]
}
```

---

## 7. What Claude Should Do With This

When helping with code or migration, key expectations:

1. **SQLAlchemy models** should be updated to match:

   * `EtoRunModel` (parent) with `ETO_MASTER_STATUS` and `ETO_RUN_PROCESSING_STEP`.
   * `EtoSubRunModel` (new) with `ETO_RUN_STATUS`, `matched_pages`, `is_unmatched_group`.
   * Extraction / pipeline models updated to reference `eto_sub_runs` instead of `eto_runs`.

2. **Worker logic** should be designed around:

   * Parent TM worker scanning `eto_runs` where `status='not_started'`.
   * Sub-run workers scanning `eto_sub_runs` where `status='not_started'` and `template_version_id IS NOT NULL`.

3. **Reprocessing** should operate on **sub-runs**, not `eto_runs`.

4. **Invariants** to uphold:

   * Exactly one `eto_runs` per `pdf_files` row.
   * At most one `eto_sub_runs` row with `is_unmatched_group = true` per `eto_run`.
   * When `eto_runs.status = 'success'`, no `eto_sub_runs` are in `not_started` or `processing`.

This doc is meant as the authoritative description of the new design so Claude can safely generate migrations, updated models, and service logic without misinterpreting the intent.

```
```
