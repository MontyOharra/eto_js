# Backend Typing & Architecture — Project Summary

This doc captures the key decisions and patterns we aligned on for your FastAPI + SQLAlchemy backend, including typing, models, repositories, and API/service layering.

---

## 1) Big Picture

* **Goal:** Strong typing end-to-end with clean boundaries:

  * **API (FastAPI)** — request/response validation (Pydantic).
  * **Service layer** — business logic, transactions, orchestration.
  * **Repository layer** — persistence, ORM mapping, JSON (de)serialization, no leak of ORM to callers.
  * **SQLAlchemy models** — schema + relationships only.

* **Recommended flow:** **API → Service → Repo** (not API → Repo).

  * Routers handle HTTP concerns and mapping.
  * Services own domain rules and transaction scope.
  * Repos hide persistence details and return typed domain data (DTOs).

---

## 2) SQLAlchemy Models

* **Enums:** Use SA `Enum` with `native_enum=False, validate_strings=True` (Option **C**):

  * Stored as strings, with DB CHECK constraints.
  * ORM exposes real Python Enums (type-safe).
* **Timestamps:** Every table has `created_at` and `updated_at` (e.g. `DATETIME2`, `server_default=func.getutcdate()`, `onupdate=func.getutcdate()`).
* **Relationships & indexes:** Match `dbdiagram` definitions; tables ordered alphabetically but field order remains logical.

---

## 3) Pydantic & Typing Strategy

Two viable patterns; both **keep ORM inside repos**:

### Option A — Pydantic end-to-end

* Use Pydantic v2 models for API and domain return types.
* Repos accept Pydantic `Create/Update` and return Pydantic `Read` models.
* Set `model_config = ConfigDict(from_attributes=True, use_enum_values=True)` for `.model_validate()` and enum serialization.
* **Pros:** Simple, fewer types to maintain.
* **Use when:** Most use cases; start here unless you need stricter separations.

### Option B — Lean Service DTOs

* **API** uses Pydantic for requests/responses (ergonomic validation & docs).
* **Service layer** uses **frozen dataclasses** (DTOs) for commands/queries and return values.
* Small mappers convert API schemas ↔ DTOs at the edges.
* **Pros:** Clear separation of API contract vs. domain types, cheaper objects, easier versioning.
* **Use when:** Larger systems, multiple clients/versions, strict domain modeling.

> We proceeded with **Option B** for the **EmailConfig** example: API schemas for requests/responses, dataclass DTOs for services/repos, and repo-scoped JSON (de)serialization.

---

## 4) Repository Responsibilities

* Accept **DTOs** (Option B) or Pydantic models (Option A).
* **Convert**: DTO ↔ ORM model internally.
* **Serialize/Deserialize** JSON fields (e.g., `filter_rules`) **inside the repo**.
* Return **DTOs** (Option B) or Pydantic read models (Option A).
* **Never** return ORM entities to callers.

**Helpers inside repo** (scoped, private):

* `_serialize_filter_rules(dto.rules) -> str | None`
* `_deserialize_filter_rules(raw: str | None) -> List[RuleDTO]`
* `_to_dto(model) -> DTO`
* `_apply_update(model, update_dto) -> None`

---

## 5) Service Layer

* Owns **business rules**, **transactions/UoW**, cross-repo orchestration, retries, authZ checks (if not in routers), event publishing, etc.
* API should depend on **services**, not repos.
* Services call repos and return DTOs (Option B) or Pydantic read models (Option A).

---

## 6) FastAPI Wiring (App State & DI)

* Use **`app.state`** to store long-lived objects created in the **lifespan** (startup):

  * DB connection manager, service container, caches, clients, etc.
* Provide DI helpers to fetch a **service** from `app.state.container`.
* Avoid global singletons; per-process app state is test-friendly and worker-safe.

**Example:**

```py
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    cm = DatabaseConnectionManager(...)
    container = ServiceContainer(connection_manager=cm, ...)
    app.state.container = container
    try:
        yield
    finally:
        cm.close()

app = FastAPI(lifespan=lifespan)
```

---

## 7) EmailConfig Example (Option B)

**API Schemas (Pydantic):**

* `EmailConfigCreateRequest`, `EmailConfigUpdateRequest`
* `EmailConfigResponse`, `EmailConfigSummaryResponse`
* `EmailFilterRuleIn`

**Service DTOs (dataclasses):**

* `EmailConfigCreateDTO`, `EmailConfigUpdateDTO`, `EmailConfigDTO`
* `EmailFilterRuleDTO`

**Mappers:**

* `to_create_dto(req) -> CreateDTO`
* `to_update_dto(req) -> UpdateDTO`
* `dto_to_response(dto) -> Response`

**Repo methods (DTO in/out):**

* `create(dto) -> DTO`
* `get_by_id(id) -> DTO | None`
* `get_all() -> List[DTO]`
* `update(id, dto) -> DTO`
* `delete(id) -> DTO`
* Business ops: `activate`, `deactivate`, `get_active_configs`, `update_runtime_status`, `record_error`

---

## 8) Field & Validation Notes

* Use Pydantic `Field()` for API models to express constraints, examples, docs. Overhead is negligible in v2.
* Keep **strict validation at the API edge**. Services can assume validated inputs (or add domain-specific checks).
* For enums in API responses, set `use_enum_values=True` so JSON shows strings, while services/repos work with Python Enums.

---

## 9) Design Rationale (Why this way)

* **Encapsulation:** ORM changes don’t bubble up to API or services.
* **Type Safety:** Enums and DTOs prevent invalid states; repos validate JSON payloads.
* **Testability:** Unit test services with fake repos; integration test repos with a real DB.
* **Evolvability:** Swap storage, add caches, introduce outbox/eventing with minimal API churn.

---

## 10) Actionable Next Steps

1. Keep **Option B** for EmailConfig in code: router ↔ service ↔ repo with DTOs.
2. Apply the same pattern to **EtoRunExtraction** and other aggregates.
3. Ensure **all JSON fields** are serialized/deserialized only inside repos.
4. Keep **enums** in a shared module and use `SAEnum(native_enum=False, validate_strings=True)`.
5. Centralize **transactions/UoW** inside services as complexity grows.

---

Need examples in code (service class, DI helpers, or Unit-of-Work pattern)? I can add those snippets next.
