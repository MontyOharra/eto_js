# Server Redesign - Design Methodology

## Overview

This document outlines the methodology for redesigning the ETO backend server architecture with a focus on **front-end-first design** and **top-down planning**.

---

## Core Principles

### 1. Front-End Driven Design
The **most important consideration** is what the front-end application actually needs. All backend design decisions flow from understanding:
- What data does the UI need to display?
- What actions can users perform?
- What workflows need to be supported?

### 2. Top-Down Design Process
Instead of designing first-to-last (API → Service → Repository → Types), we design **higher-to-lower level**:

```
1. Domain Segmentation (Routers)
    ↓
2. Domain Requirements (Per-router analysis)
    ↓
3. Endpoint Definitions (Routes, methods, paths)
    ↓
4. Request/Response Types (Schemas, errors, conditions)
    ↓
5. Service Layer Design (Business logic needs)
    ↓
6. Repository Layer Design (Data access patterns)
    ↓
7. Type Unification (DTOs connecting all layers)
    ↓
8. Implementation (Code based on complete design)
```

### 3. Iterative Refinement
This is a **collaborative, back-and-forth process**:
- User describes requirements and vision
- Assistant asks clarification questions
- User provides answers
- Assistant updates design documents
- Repeat until complete understanding

---

## Design Process Steps

### Phase 1: Domain & Router Segmentation
**Goal:** Identify logical API groupings based on frontend features

**Questions to answer:**
- What major features/domains exist in the application?
- How should the API be organized (e.g., `/email-configs`, `/pdf-templates`, `/pipelines`)?
- What entities/aggregates does each domain manage?
- Which domains interact with each other?

**Output:** List of routers with high-level descriptions

---

### Phase 2: Per-Domain Analysis
**Goal:** Understand each domain's requirements deeply

**For each domain, define:**
- **Primary entities**: What objects does this domain manage?
- **User workflows**: What can users do in the frontend?
- **Data relationships**: How does this domain connect to others?
- **Business rules**: What validations or constraints exist?

**Output:** Domain requirements document per router

---

### Phase 3: Endpoint Definitions
**Goal:** Design the actual HTTP API surface

**For each domain, specify:**
- **Endpoint paths**: `/email-configs`, `/email-configs/{id}`, etc.
- **HTTP methods**: GET, POST, PUT, PATCH, DELETE
- **Path parameters**: `{config_id}`, `{template_id}`, etc.
- **Query parameters**: `?active=true`, `?page=1&limit=20`, etc.
- **Authentication/Authorization**: Which endpoints require what permissions?

**Output:** Complete endpoint list with HTTP details

---

### Phase 4: Schema Definitions
**Goal:** Define request/response contracts

**For each endpoint, specify:**
- **Request schema**: What data comes from the client?
  - Required vs optional fields
  - Validation rules (min/max, regex, enums)
  - Nested objects
- **Response schema**: What data goes to the client?
  - Success response structure
  - Field descriptions
- **Error responses**: What can go wrong?
  - 400 (validation error): Which validation failures?
  - 404 (not found): Which resources?
  - 409 (conflict): What conflict conditions?
  - 500 (server error): Graceful degradation?

**Output:** Complete API contract specification

---

### Phase 5: Service Layer Design
**Goal:** Define business logic orchestration

**Based on API requirements, design:**
- **Service methods**: What business operations are needed?
- **Transaction boundaries**: Where do we need atomicity?
- **Cross-domain orchestration**: Which operations span multiple repos?
- **Domain rules**: What business validations occur here?
- **Event handling**: What side effects occur (logging, notifications)?

**Output:** Service interface specifications

---

### Phase 6: Repository Layer Design
**Goal:** Define data access patterns

**Based on service needs, design:**
- **CRUD operations**: Standard create/read/update/delete
- **Query methods**: Custom queries (filters, sorting, pagination)
- **Batch operations**: Bulk inserts, updates
- **JSON serialization**: Which fields need complex handling?
- **Transaction support**: How do repos coordinate?

**Output:** Repository interface specifications

---

### Phase 7: Type System Unification
**Goal:** Create DTOs that connect all layers

**Design the complete type system:**
- **API Schemas** (`api/schemas/`): Pydantic models for HTTP validation
- **DTOs** (`shared/types/`): Frozen dataclasses for internal use
- **Mappers** (`shared/utils/mappers.py`): Schema ↔ DTO conversion
- **Enums & Value Objects**: Shared types across layers

**Output:** Complete type system design

---

### Phase 8: Implementation
**Goal:** Build code based on complete understanding

**Now that we know everything:**
1. Implement types (DTOs and schemas)
2. Implement repositories (data access)
3. Implement services (business logic)
4. Implement mappers (layer translation)
5. Implement routers (HTTP endpoints)
6. Write tests for each layer
7. Integration testing

**Output:** Working, tested code

---

## Key Benefits of This Approach

1. **Frontend Alignment**: API matches actual UI needs, not abstract data models
2. **Complete Understanding**: Design entire system before writing code
3. **Fewer Rewrites**: Discover issues during design, not implementation
4. **Clear Documentation**: Design docs serve as living specification
5. **Team Communication**: Shared understanding before code review
6. **Testability**: Clear contracts make testing straightforward

---

## Design Documents Structure

```
context/server_redesign/
├── INSTRUCTIONS.md           # This file - methodology overview
├── API_DESIGN.md            # API specification (routers, endpoints, schemas)
├── SERVICE_DESIGN.md        # Service layer specification (business logic)
├── REPOSITORY_DESIGN.md     # Repository layer specification (data access)
├── TYPE_SYSTEM.md           # Complete type system (DTOs, schemas, mappers)
└── IMPLEMENTATION_PLAN.md   # Build order and migration strategy
```

---

## Current Status

**Phase:** Phase 1 - Domain & Router Segmentation

**Next Step:** Define domain boundaries and router organization based on frontend requirements

---

## Notes

- This is a **living methodology** - we can refine the process as we discover better approaches
- The goal is **bulletproof design** before implementation
- Front-end requirements drive everything
- Collaborative iteration ensures we don't miss critical details
