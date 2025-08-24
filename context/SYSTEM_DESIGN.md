## ETO – System Design and Implementation Plan

### 1. Overview

- On‑premise solution: all backend processes run on a Windows server.
- Electron client UI for review and authoring of signatures and extraction rules.
- Node.js server as a modular monolith with a Python runtime (pdfplumber) for PDF object extraction.
- SQL Server as the database. Raw PDFs stored on filesystem.

### 2. Current implementation status

- Electron main invokes Python to extract PDF objects.
- Robust error handling added (spawn diagnostics, exit codes, stderr JSON, serialization fallbacks).
- Python accepts a file path (preferred) or base64; non‑serializable types are coerced safely.
- Dev uses a local venv; Electron prefers `.venv` Python automatically.

### 3. Architecture (prototype)

- Processes
  - Electron app (UI)
  - Node server: REST API + background jobs (modular monolith)
  - Python runtime: invoked by server for extraction (local venv)
- Storage
  - SQL Server for app data
  - Filesystem for raw PDFs (content‑addressed by SHA‑256)
- Communication
  - Client → Server via HTTP API (preferred). Optionally proxy via Electron main/preload.

### 4. Server modules

- Email ingest: poll mailbox (Graph/Exchange), save attachments, compute SHA‑256, persist file record
- PDF processor: call Python to extract objects; normalize/round; persist per file (or per page JSON blobs)
- Signature matcher: exact subset matching (per current plan) against normalized anchors
- Extraction runner: apply rules to produce fields; methods supported:
  - text_in_bbox (fixed regions)
  - text_from_anchor (variable‑length text; capture relative to label/anchor)
- Review API: list tasks, view objects and extracted fields, submit corrections
- Jobs: DB‑backed job table → email_ingested → objects_extracted → signature_matched → extraction_attempted → extracted|needs_review (with retries/backoff)

### 5. Data model (SQL Server)

- Tables (concise)
  - `pdf_files(id, sha256 VARBINARY(32)|CHAR(64), path NVARCHAR(512), received_at DATETIME2, source_message_id NVARCHAR(255))`
  - `pdf_signatures(id, name, customer_id, version INT, active BIT, anchors_json NVARCHAR(MAX), anchors_hash CHAR(64), created_at DATETIME2)`
  - `extraction_rules(id, signature_id, version INT, active BIT, spec_json NVARCHAR(MAX), created_at DATETIME2)`
  - `signature_matches(id, file_id, signature_id, score INT, decided_at DATETIME2)`
  - `extractions(id, file_id, signature_id, rule_id, status NVARCHAR(32), fields_json NVARCHAR(MAX), errors_json NVARCHAR(MAX), created_at DATETIME2)`
- JSON columns as `NVARCHAR(MAX)`; optional `CHECK (ISJSON(column)=1)` in migrations.
- Indexes: unique on `sha256`; nonclustered on `file_id`, `signature_id`, `status`.

### 6. JSON schemas (versioned)

- Signature anchors (exact matching)

```ts
// versioned payload stored in pdf_signatures.anchors_json
interface SignatureAnchor {
  type:
    | "word"
    | "text_line"
    | "table"
    | "rect"
    | "curve"
    | "graphic_line"
    | "image";
  page: number; // zero-based
  bbox: [number, number, number, number];
  text?: string; // for text-like objects
}

interface PdfSignatureJsonV1 {
  version: 1;
  name: string;
  customerId?: string;
  anchors: SignatureAnchor[];
}
```

- Extraction rules

```ts
// versioned payload stored in extraction_rules.spec_json
interface ExtractionFieldSpec_TextFromAnchor {
  method: "text_from_anchor";
  fieldName: string;
  page: number;
  anchorText?: string; // exact label text
  anchorBBox?: [number, number, number, number];
  direction: "right" | "below";
  sameLineTolerance?: number; // e.g., 2–4
  maxDistance?: number; // e.g., 300
  stopAtRegex?: string; // optional delimiter/label
  valueRegex?: string; // optional capture/validation
}

interface ExtractionFieldSpec_TextInBBox {
  method: "text_in_bbox";
  fieldName: string;
  page: number;
  bbox: [number, number, number, number];
  valueRegex?: string;
}

interface ExtractionRuleJsonV1 {
  version: 1;
  signatureId: string;
  fields: Array<
    ExtractionFieldSpec_TextFromAnchor | ExtractionFieldSpec_TextInBBox
  >;
}
```

### 7. Matching algorithm (current policy)

- Exact subset only; single winner (or none).
- Normalize objects identically to anchor creation (same rounding and fields).
- Compute per‑object stable hash: e.g., `SHA256(type|page|bbox|text)`.
- For each signature: `count(anchors present in file objects)`; match only if `count == anchors.length`.
- If multiple signatures would tie (should not with exact policy), treat as no match.

### 8. API outline (server)

- PDFs
  - `POST /api/pdfs/upload` → { fileId } (if client cannot share filesystem)
  - `POST /api/pdfs/extract` { filePath | fileId } → PdfObject[]
- Signatures
  - `POST /api/signatures` { name, customerId, anchors_json } → { signatureId }
  - `GET /api/signatures` → list
- Extraction rules
  - `POST /api/extraction-rules` { signatureId, spec_json } → { ruleId }
- Processing
  - `POST /api/process/:fileId` → kicks job chain (extract → match → extract fields)
- Review
  - `GET /api/review/tasks` → tasks
  - `POST /api/review/:fileId/corrections` → corrections payload
- Health
  - `GET /health` → ok

Client usage (direct fetch example):

```ts
const API = "http://localhost:8080";
const r = await fetch(`${API}/api/pdfs/extract`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ filePath }),
});
const objects = await r.json();
```

### 9. Windows server setup (summary)

- Install Node LTS, Python 3.12, Git, NSSM; create `srv-eto` service account.
- Create directories under `C:\apps\eto\server\` (bin, logs, storage, python, tmp) with proper ACLs.
- Install SQL Server; create DB and least‑privilege login; set `DATABASE_URL`.
- Create Python venv in `server\python\.venv`; install `pdfplumber`, `pillow`, `pdfminer.six`.
- Register Node app as Windows service via NSSM; configure env vars and log redirection.

### 10. CI/CD (initial)

- CI (GitHub Actions)
  - Server tests (Ubuntu): Node + Python, start SQL Server container, run lint/typecheck/unit/integration, `prisma migrate deploy` in CI.
  - Client build (Windows): build main/preload + React; produce unsigned installer.
- Release on tag (`v*`): publish artifacts (server zip, client installer) and changelog.
- Deploy: PowerShell script to stop service → deploy artifacts → migrate DB → start service.

### 11. Testing strategy

- Typecheck: strict TS; Python type hints where useful.
- Lint/format: ESLint + Prettier; Python Ruff/Black.
- Unit tests: Node (matchers, extraction logic); Python (extractor with small fixture PDFs).
- Integration: API + DB with ephemeral SQL Server (container) for CI Linux job or native in Windows job.
- E2E (optional early): Playwright smoke for Electron UI.

### 12. Ops notes

- Stay Windows‑native initially (simpler paths, Outlook/Graph/UNC integration). Consider WSL/containers later once you move to a file‑upload pipeline and drop Windows path dependencies.
- Observability: JSON logs with file_id/job_id; health endpoint; basic metrics in logs.
- Backups: SQL Server full+log backups; log rotation; runbooks for common failures.

### 13. Next steps

1. Finalize Prisma schema for SQL Server (tables above) and add JSON `CHECK` constraints + indexes.
2. Implement server job table + worker loop and health endpoint.
3. Wire Python venv path in server; reuse current extractor.
4. Implement exact signature matching and `text_from_anchor` extraction.
5. Expose minimal REST endpoints and build client calls.
6. Add CI workflows and staging deployment script; iterate.
