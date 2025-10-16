# Frontend Redesign Implementation Plan

**Version:** 1.0
**Created:** 2025-10-15
**Status:** In Progress

---

## Overview

This document outlines the step-by-step plan for implementing the new frontend application based on the design specification in `FRONTEND_DESIGN.md`.

The implementation will be done in `client-new/` directory, leaving the existing `client/` intact for reference.

---

## Implementation Phases

### Phase 1: Boilerplate Setup ✓ (In Progress)

**Goal:** Set up basic Electron + React application that renders a hello world

#### 1.1 Directory Structure Setup
- [ ] Create `client-new/` directory
- [ ] Copy boilerplate files from `client/`:
  - Configuration files (tsconfig, eslint, vite.config, etc.)
  - Build scripts (`scripts/`)
  - Icons and assets
  - Main process files
  - Preload files
- [ ] Build out top-level src structure (first two levels only):
  ```
  src/
  ├── main/
  ├── preload/
  ├── renderer/
  │   ├── app/
  │   ├── features/
  │   ├── shared/
  │   └── pages/
  └── @types/
  ```

#### 1.2 Hello World Application
- [ ] Create basic `index.html`
- [ ] Create `main.tsx` with router setup
- [ ] Create `App.tsx` with hello world message
- [ ] Create simple root route in `pages/__root.tsx`
- [ ] Create index route in `pages/index.tsx`

#### 1.3 Package Configuration
- [ ] Update `package.json`:
  - Remove Prisma dependencies (no local database)
  - Ensure all necessary dependencies are present
  - Update build scripts if needed
- [ ] Remove Prisma-related files and references

---

### Phase 2: Development Testing

**Goal:** Verify the basic setup works in development mode

#### 2.1 Dev Mode Testing
- [ ] Run `npm install`
- [ ] Run `npm run dev`
- [ ] Verify Electron window opens
- [ ] Verify "Hello World" renders
- [ ] Verify hot reload works
- [ ] Check DevTools for errors

**Success Criteria:**
- Electron app opens successfully
- Hello world message displays
- No console errors
- Hot reload triggers on file changes

---

### Phase 3: Production Build Testing

**Goal:** Verify the application can be built and packaged

#### 3.1 Build Process
- [ ] Run `npm run build`
- [ ] Verify build output in `build/` directory
- [ ] Check for build errors

#### 3.2 Package Application
- [ ] Run `npm run dist:win` (or appropriate platform command)
- [ ] Verify `.exe` (or platform executable) is created
- [ ] Test running the packaged application
- [ ] Verify "Hello World" renders in production build

**Success Criteria:**
- Build completes without errors
- Executable file is created
- Packaged app runs and displays hello world
- No runtime errors in production mode

---

### Phase 4: Electron API Foundation

**Goal:** Complete the type-safe Electron IPC setup and test file operations

#### 4.1 Type-Safe IPC Setup
- [ ] Define IPC type mappings in `@types/global.d.ts`:
  - `InputPayloadMapping`
  - `OutputPayloadMapping`
  - `Window.electron` interface
- [ ] Implement preload API exposure in `preload/index.ts`
- [ ] Implement IPC handlers in `main/helpers/ipcHandlers.ts`
- [ ] Register handlers in `main/index.ts`

#### 4.2 File Operations Implementation
- [ ] Implement `file:select` (open file dialog)
- [ ] Implement `file:read` (read file content)
- [ ] Implement `file:save` (save file dialog)
- [ ] Implement `dialog:confirm` (confirmation dialog)

#### 4.3 Testing File Operations
- [ ] Create test page with file upload/download buttons
- [ ] Test file selection in dev mode
- [ ] Test file reading in dev mode
- [ ] Test file saving in dev mode
- [ ] Test confirmation dialog in dev mode
- [ ] Test all operations in production build

**Success Criteria:**
- All file operations work correctly
- Full TypeScript autocomplete in renderer
- No type errors
- Works in both dev and production

---

### Phase 5: Complete Directory Structure

**Goal:** Build out the complete feature and shared directories

#### 5.1 Shared Infrastructure
- [ ] Create `shared/ui/` components directory
- [ ] Create `shared/api/` infrastructure:
  - `client.ts` (Axios instance)
  - `config.ts` (API configuration)
  - `interceptors/` (auth, errors, logging)
- [ ] Create `shared/hooks/` directory
- [ ] Create `shared/types/` directory
- [ ] Create `shared/utils/` directory

#### 5.2 Feature Directories
Create directory structure for each feature (no implementation yet):
- [ ] `features/email-configs/`
- [ ] `features/templates/`
- [ ] `features/pipelines/`
- [ ] `features/pdf-files/`
- [ ] `features/eto-runs/`

Each feature gets:
```
features/{feature}/
├── api/
├── components/
├── hooks/
└── mocks/
```

#### 5.3 Pages Structure
Create page files for routing:
- [ ] `pages/__root.tsx` (root layout)
- [ ] `pages/index.tsx` (home)
- [ ] `pages/email-configs/index.tsx`
- [ ] `pages/templates/index.tsx`
- [ ] `pages/pipelines/index.tsx`
- [ ] `pages/pdf-files.tsx`
- [ ] `pages/eto-runs/index.tsx`

---

### Phase 6: Types and Mock Data

**Goal:** Define all TypeScript types and create mock data for development

#### 6.1 Type Definitions
For each feature, create `api/types.ts` matching backend models:
- [ ] Email configs types
- [ ] Templates types
- [ ] Pipelines types
- [ ] PDF files types
- [ ] ETO runs types

#### 6.2 Mock Data
For each feature, create `mocks/*.ts`:
- [ ] Email configs mocks
- [ ] Templates mocks
- [ ] Pipelines mocks
- [ ] PDF files mocks
- [ ] ETO runs mocks

#### 6.3 Mock Service Worker Setup
- [ ] Install and configure MSW
- [ ] Create mock handlers for all features
- [ ] Set up environment variable toggle (`VITE_USE_MOCK_API`)
- [ ] Test mock API responses

**Success Criteria:**
- All types defined with proper TypeScript interfaces
- Mock data covers realistic scenarios
- Can toggle between mock and real API via env var

---

### Phase 7: Basic Page Structure

**Goal:** Create page layouts with navigation, no functionality yet

#### 7.1 Root Layout
- [ ] Create sidebar navigation
- [ ] Create header component
- [ ] Create main content area
- [ ] Implement routing outlet

#### 7.2 Page Shells
Create basic page structure for each route:
- [ ] Home page (dashboard overview)
- [ ] Email configs list page
- [ ] Templates list page
- [ ] Pipelines list page
- [ ] PDF files page
- [ ] ETO runs list page

**Success Criteria:**
- Can navigate between all pages
- Layout is consistent
- No functionality, just structure

---

### Phase 8: Component Implementation

**Goal:** Build components page by page, testing with mock data

#### 8.1 Email Configs Feature
- [ ] Create `EmailConfigList` component
- [ ] Create `EmailConfigCard` component
- [ ] Create `EmailConfigForm` component
- [ ] Create React Query hooks
- [ ] Wire up to mock API
- [ ] Test CRUD operations with mocks

#### 8.2 Templates Feature
- [ ] Create `TemplateList` component
- [ ] Create `TemplateCard` component
- [ ] Create `TemplateBuilder` component (can reuse from old client)
- [ ] Create React Query hooks
- [ ] Wire up to mock API
- [ ] Test with mocks

#### 8.3 Pipelines Feature
- [ ] Create `PipelineList` component
- [ ] Create `PipelineBuilder` component (can reuse from old client)
- [ ] Create `ModulePalette` component
- [ ] Create React Query hooks
- [ ] Wire up to mock API
- [ ] Test with mocks

#### 8.4 PDF Files Feature
- [ ] Create `PdfFileList` component
- [ ] Create `PdfViewer` component (can reuse from old client)
- [ ] Create `PdfUpload` component (Electron + HTTP)
- [ ] Create React Query hooks
- [ ] Wire up to mock API
- [ ] Test upload flow (Electron file selection → mock API)

#### 8.5 ETO Runs Feature
- [ ] Create `EtoRunsList` component
- [ ] Create `EtoRunDetail` component
- [ ] Create `EtoRunViewer` component
- [ ] Create React Query hooks
- [ ] Wire up to mock API
- [ ] Test with mocks

**Success Criteria (per feature):**
- All components render correctly
- Mock data displays properly
- User interactions work (forms, buttons, navigation)
- Loading and error states handled
- React Query caching works

---

### Phase 9: API Foundation Setup

**Goal:** Prepare for backend integration (but don't connect yet)

#### 9.1 Axios Client Setup
- [ ] Configure base Axios instance
- [ ] Set up environment variable for API URL
- [ ] Create auth interceptor (add token to requests)
- [ ] Create error interceptor (handle API errors)
- [ ] Create logging interceptor (dev mode only)

#### 9.2 API Layer for Each Feature
Create `api/{feature}Api.ts` for each feature:
- [ ] Email configs API functions
- [ ] Templates API functions
- [ ] Pipelines API functions
- [ ] PDF files API functions
- [ ] ETO runs API functions

#### 9.3 React Query Configuration
- [ ] Configure QueryClient with defaults
- [ ] Set up query key factories
- [ ] Configure stale times and cache times
- [ ] Set up dev tools

**Success Criteria:**
- API layer is defined but using mocks
- Can easily toggle between mock and real API
- Error handling works
- Ready to connect to real backend

---

### Phase 10: Backend Connection (Future)

**Goal:** Connect to real FastAPI backend (after server redesign is complete)

**Note:** This phase happens AFTER the backend redesign is complete.

#### 10.1 Switch from Mocks to Real API
- [ ] Set `VITE_USE_MOCK_API=false`
- [ ] Configure `VITE_API_BASE_URL` to point to backend
- [ ] Test each feature with real API
- [ ] Handle real error responses
- [ ] Verify authentication flow

#### 10.2 Integration Testing
- [ ] Test email configs CRUD with real backend
- [ ] Test templates CRUD with real backend
- [ ] Test pipelines CRUD with real backend
- [ ] Test PDF upload with real backend
- [ ] Test ETO runs with real backend

#### 10.3 Production Configuration
- [ ] Set up production API URL
- [ ] Configure authentication for production
- [ ] Test production build with real API
- [ ] Verify security (HTTPS, etc.)

---

## Current Progress

**Current Phase:** Phase 1 - Boilerplate Setup
**Current Task:** Creating client-new directory and copying boilerplate files

---

## Notes

### Files to Copy from `client/` to `client-new/`:

**Root Level:**
- `.gitignore`
- `tsconfig.base.json`
- `tsconfig.json`
- `tsconfig.vite.json`
- `vite.config.ts`
- `electron-builder.json` (update paths if needed)
- `eslint.config.js`

**Scripts:**
- `scripts/build-main.mjs`
- `scripts/build-preload.mjs`

**Icons:**
- `icons/*` (all icon files)

**Main Process:**
- `src/main/helpers/utils.ts`
- `src/main/helpers/ipcWrappers.ts`
- `src/main/index.ts` (base structure)

**Preload:**
- `src/preload/ipcWrappers.ts`
- `src/preload/tsconfig.json`

**Renderer:**
- `src/renderer/index.html`
- `src/renderer/styles.css`
- `src/renderer/vite-env.d.ts`
- `src/renderer/tsconfig.json`

**Type Definitions:**
- `src/@types/global.d.ts` (base structure only)

### Components to Potentially Reuse:

These components from old client may be useful:
- PDF Viewer components
- Template Builder components
- Pipeline Graph components
- React Flow integration

Will evaluate during Phase 8 which components to reuse vs rewrite.

---

## Dependencies to Remove

From `package.json`:
- `@prisma/client`
- `prisma`
- All Prisma-related scripts

From build scripts:
- `prisma:generate` commands
- Prisma query engine bundling

---

## Success Metrics

**Phase 1-4:** Basic app runs and file operations work
**Phase 5-6:** Complete structure with types and mocks
**Phase 7-8:** Full UI working with mock data
**Phase 9:** Ready for backend integration
**Phase 10:** Fully integrated with backend

---

## Timeline Estimate

- **Phase 1-4:** 1-2 hours (setup and testing)
- **Phase 5-7:** 2-3 hours (structure and basic pages)
- **Phase 8:** 5-8 hours (component implementation)
- **Phase 9:** 1-2 hours (API foundation)
- **Phase 10:** 2-4 hours (backend integration)

**Total Estimated:** 11-19 hours

---

## References

- Design Specification: `context/client_redesign/FRONTEND_DESIGN.md`
- Backend Design: `context/server_redesign/SERVICE_LAYER_DESIGN.md`
- Exception Design: `context/server_redesign/EXCEPTION_DESIGN.md`
