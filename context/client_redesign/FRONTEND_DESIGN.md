# Frontend Application Design Specification

**Version:** 1.0
**Last Updated:** 2025-10-15
**Status:** Draft - Pending Approval

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Electron Architecture](#electron-architecture)
6. [Type Safety System](#type-safety-system)
7. [API Layer Design](#api-layer-design)
8. [Routing Architecture](#routing-architecture)
9. [State Management](#state-management)
10. [Feature Module Design](#feature-module-design)
11. [Backend Integration](#backend-integration)
12. [Development Workflow](#development-workflow)
13. [Examples](#examples)

---

## 1. Overview

The ETO Client is an Electron-based desktop application built with React and TypeScript. It serves as a **client interface** to the ETO FastAPI server, providing users with a native desktop experience for managing email configurations, templates, pipelines, and PDF processing.

### Key Characteristics

- **Client-Server Architecture**: The app is a pure HTTP client - no local database
- **Type-Safe Throughout**: Full TypeScript coverage with compile-time guarantees
- **Feature-Based Organization**: Code organized by business domains, not technical layers
- **Modern React Patterns**: Using React Query, TanStack Router, and hooks
- **Native OS Integration**: File dialogs, system notifications, etc. via Electron

---

## 2. Architecture Principles

### 2.1 Separation of Concerns

The application is divided into three distinct layers:

1. **Main Process** (Node.js)
   - Window management
   - File system access
   - OS dialogs and native integrations
   - **No business logic**

2. **Preload Scripts** (Security Bridge)
   - Type-safe API exposure via `contextBridge`
   - Security boundary between main and renderer
   - Minimal, pure delegation to main process

3. **Renderer Process** (React)
   - All UI and business logic
   - HTTP client to FastAPI server
   - State management with React Query
   - **Isolated from Node.js for security**

### 2.2 Design Methodologies

**Feature-Sliced Design (FSD)**
- Organize by business features, not technical layers
- Each feature is self-contained with its own API, components, hooks
- Reference: https://feature-sliced.design/

**Bulletproof React**
- Modern React patterns and best practices
- Co-location of related code
- Reference: https://github.com/alan2207/bulletproof-react

**Electron Security Best Practices**
- `contextIsolation: true`
- `nodeIntegration: false`
- Explicit API surface via preload scripts
- Reference: https://www.electronjs.org/docs/latest/tutorial/security

---

## 3. Technology Stack

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Electron** | Latest | Desktop app framework |
| **React** | 18+ | UI framework |
| **TypeScript** | 5+ | Type safety |
| **Vite** | Latest | Build tool and dev server |
| **TanStack Router** | Latest | Type-safe file-based routing |
| **TanStack Query** | Latest | Server state management |
| **Axios** | Latest | HTTP client |
| **Tailwind CSS** | Latest | Styling |
| **Zod** | Latest | Runtime validation |

### Development Tools

- **Electron Forge** - Packaging and distribution
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **MSW** (Mock Service Worker) - API mocking for development

---

## 4. Project Structure

### 4.1 Complete Directory Layout

```
client/
├── src/
│   ├── main/                          # Electron main process
│   │   ├── index.ts                   # Entry point
│   │   ├── helpers/
│   │   │   ├── ipcHandlers.ts         # IPC handler registration
│   │   │   ├── ipcWrappers.ts         # Type-safe IPC utilities
│   │   │   └── utils.ts               # Main process utilities
│   │   └── window/
│   │       └── mainWindow.ts          # Window creation/management
│   │
│   ├── preload/                       # Security bridge
│   │   ├── index.ts                   # Expose APIs to renderer
│   │   └── ipcWrappers.ts             # Renderer-side IPC wrappers
│   │
│   ├── renderer/                      # React application
│   │   ├── index.tsx                  # Renderer entry point
│   │   ├── App.tsx                    # Root component
│   │   │
│   │   ├── app/                       # App-level config
│   │   │   ├── router.tsx             # Router configuration
│   │   │   ├── queryClient.ts         # React Query setup
│   │   │   └── providers.tsx          # Global providers
│   │   │
│   │   ├── features/                  # Business features (FSD)
│   │   │   ├── email-configs/
│   │   │   │   ├── api/
│   │   │   │   │   ├── types.ts           # TypeScript types
│   │   │   │   │   ├── schemas.ts         # Zod schemas
│   │   │   │   │   ├── emailConfigsApi.ts # Raw API calls
│   │   │   │   │   └── emailConfigsQueries.ts # React Query hooks
│   │   │   │   ├── components/
│   │   │   │   │   ├── EmailConfigList.tsx
│   │   │   │   │   ├── EmailConfigForm.tsx
│   │   │   │   │   └── EmailConfigCard.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useEmailConfigForm.ts
│   │   │   │   └── mocks/
│   │   │   │       └── emailConfigsMocks.ts
│   │   │   │
│   │   │   ├── templates/
│   │   │   │   ├── api/
│   │   │   │   ├── components/
│   │   │   │   ├── hooks/
│   │   │   │   └── mocks/
│   │   │   │
│   │   │   ├── pipelines/
│   │   │   │   ├── api/
│   │   │   │   ├── components/
│   │   │   │   │   ├── PipelineBuilder/     # Complex sub-feature
│   │   │   │   │   │   ├── Canvas.tsx
│   │   │   │   │   │   ├── ModulePalette.tsx
│   │   │   │   │   │   ├── WiringPanel.tsx
│   │   │   │   │   │   └── index.tsx
│   │   │   │   │   └── PipelineList.tsx
│   │   │   │   ├── hooks/
│   │   │   │   └── mocks/
│   │   │   │
│   │   │   ├── pdf-files/
│   │   │   ├── eto-runs/
│   │   │   └── auth/
│   │   │
│   │   ├── shared/                    # Shared utilities
│   │   │   ├── api/
│   │   │   │   ├── client.ts              # Axios instance
│   │   │   │   ├── config.ts              # API configuration
│   │   │   │   ├── interceptors/
│   │   │   │   │   ├── auth.ts            # Add auth headers
│   │   │   │   │   ├── errors.ts          # Error handling
│   │   │   │   │   └── logging.ts         # Request/response logging
│   │   │   │   └── types.ts               # Common API types
│   │   │   │
│   │   │   ├── ui/                        # Primitive UI components
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Table.tsx
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   ├── hooks/                     # Shared hooks
│   │   │   │   ├── useDebounce.ts
│   │   │   │   ├── useLocalStorage.ts
│   │   │   │   └── useToast.ts
│   │   │   │
│   │   │   ├── types/                     # Global types
│   │   │   │   └── common.ts
│   │   │   │
│   │   │   └── utils/                     # Utility functions
│   │   │       ├── date.ts
│   │   │       ├── validation.ts
│   │   │       └── format.ts
│   │   │
│   │   └── pages/                     # TanStack Router pages
│   │       ├── __root.tsx                 # Root layout
│   │       ├── index.tsx                  # Home page
│   │       ├── email-configs/
│   │       │   ├── index.tsx              # /email-configs
│   │       │   └── $id.tsx                # /email-configs/:id
│   │       ├── templates/
│   │       ├── pipelines/
│   │       └── settings.tsx
│   │
│   └── @types/                        # Type declarations
│       ├── global.d.ts                    # IPC type mappings
│       └── env.d.ts                       # Environment variables
│
├── public/                            # Static assets
│   └── icons/
│
├── .env.development                   # Dev environment config
├── .env.production                    # Prod environment config
├── package.json
├── tsconfig.json
├── vite.config.ts
└── forge.config.ts                    # Electron Forge config
```

### 4.2 Design Rationale

**Main Process (`src/main/`)**
- Minimal code - just Electron-specific functionality
- No business logic - that belongs in renderer
- Handles: windows, file system, OS dialogs, app lifecycle

**Preload Scripts (`src/preload/`)**
- Security bridge using `contextBridge`
- Exposes carefully controlled API surface to renderer
- Type-safe wrappers ensure compile-time correctness

**Renderer (`src/renderer/`)**
- Standard React application
- Feature-Sliced Design for scalability
- All business logic lives here

**Features vs Shared**
- `features/`: Domain-specific code (email-configs, pipelines)
- `shared/`: Reusable across multiple features
- Rule: Features can import from shared, but not vice versa

---

## 5. Electron Architecture

### 5.1 Main Process Responsibilities

```typescript
// src/main/index.ts
import { app, BrowserWindow } from 'electron';
import { registerIpcHandlers } from './helpers/ipcHandlers';

app.on('ready', () => {
  // 1. Register all IPC handlers FIRST
  registerIpcHandlers();

  // 2. Create main window
  const mainWindow = new BrowserWindow({
    webPreferences: {
      nodeIntegration: false,      // Security: no Node.js in renderer
      contextIsolation: true,       // Security: isolate contexts
      preload: getPreloadPath(),    // Bridge script
    },
    width: 1200,
    height: 800,
  });

  // 3. Load renderer
  if (isDev()) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile('index.html');
  }
});
```

**Key Operations Handled by Main Process:**
- File dialogs (open, save)
- File system read/write
- System notifications
- App updates (future)
- Window management

### 5.2 Preload Script Security Model

```typescript
// src/preload/index.ts
import { contextBridge } from 'electron';
import { ipcRendererInvoke } from './ipcWrappers';

// Expose ONLY these APIs to renderer - nothing else accessible
contextBridge.exposeInMainWorld('electron', {
  // File operations
  selectFile: (options) => ipcRendererInvoke('file:select', options),
  readFile: (path) => ipcRendererInvoke('file:read', { filePath: path }),
  saveFile: (content, options) => ipcRendererInvoke('file:save', { content, ...options }),

  // Dialogs
  confirm: (message, options) => ipcRendererInvoke('dialog:confirm', { message, ...options }),
  showNotification: (title, body) => ipcRendererInvoke('notification:show', { title, body }),
} satisfies Window['electron']);
```

**Security Benefits:**
- Renderer has NO direct access to Node.js APIs
- Only explicitly exposed APIs are available
- Each API is consciously designed and reviewed
- Prevents accidental security vulnerabilities

---

## 6. Type Safety System

### 6.1 IPC Type Safety Pattern

**The Challenge:** IPC channels are strings - no compile-time type checking by default.

**Our Solution:** Centralized type mappings with generic wrappers.

#### Step 1: Define Type Contracts

```typescript
// src/@types/global.d.ts
declare global {
  // Input payloads (requests FROM renderer TO main)
  type InputPayloadMapping = {
    'file:select': {
      filters?: Array<{ name: string; extensions: string[] }>;
      title?: string;
      defaultPath?: string;
    };
    'file:read': {
      filePath: string;
    };
    'file:save': {
      content: string;
      defaultPath?: string;
      filters?: Array<{ name: string; extensions: string[] }>;
    };
    'dialog:confirm': {
      message: string;
      detail?: string;
      title?: string;
    };
  };

  // Output payloads (responses FROM main TO renderer)
  type OutputPayloadMapping = {
    'file:select': {
      filePath: string;
      fileName: string;
    } | null;
    'file:read': {
      content: string;
      filePath: string;
    };
    'file:save': {
      success: boolean;
      filePath: string;
    };
    'dialog:confirm': {
      confirmed: boolean;
    };
  };

  // Window API shape exposed to renderer
  interface Window {
    electron: {
      selectFile: (
        options?: InputPayloadMapping['file:select']
      ) => Promise<OutputPayloadMapping['file:select']>;

      readFile: (
        filePath: string
      ) => Promise<OutputPayloadMapping['file:read']>;

      saveFile: (
        content: string,
        options?: Omit<InputPayloadMapping['file:save'], 'content'>
      ) => Promise<OutputPayloadMapping['file:save']>;

      confirm: (
        message: string,
        options?: Omit<InputPayloadMapping['dialog:confirm'], 'message'>
      ) => Promise<boolean>;
    };
  }
}

export {};
```

#### Step 2: Type-Safe Wrappers (Preload Side)

```typescript
// src/preload/ipcWrappers.ts
import { ipcRenderer } from 'electron';

/**
 * Type-safe IPC invoke from renderer
 * Uses the key to look up input/output types from mappings
 */
export function ipcRendererInvoke<Key extends keyof InputPayloadMapping>(
  key: Key,
  payload: InputPayloadMapping[Key]
): Promise<OutputPayloadMapping[Key]> {
  return ipcRenderer.invoke(key, payload);
}

/**
 * Type-safe IPC event listener from renderer
 */
export function ipcRendererOn<Key extends keyof OutputPayloadMapping>(
  key: Key,
  callback: (payload: OutputPayloadMapping[Key]) => void
): void {
  ipcRenderer.on(key, (_event, payload) => callback(payload));
}
```

#### Step 3: Type-Safe Handlers (Main Side)

```typescript
// src/main/helpers/ipcWrappers.ts
import { ipcMain, WebFrameMain } from 'electron';

/**
 * Type-safe IPC handler in main process
 * Uses the key to enforce input/output types
 */
export function ipcMainHandle<Key extends keyof OutputPayloadMapping>(
  key: Key,
  handler: (
    payload: InputPayloadMapping[Key]
  ) => Promise<OutputPayloadMapping[Key]>
): void {
  ipcMain.handle(key, (event, payload) => {
    // Security: validate sender frame
    validateEventFrame(event.senderFrame as WebFrameMain);

    // Call handler with typed payload
    return handler(payload);
  });
}

function validateEventFrame(frame: WebFrameMain): void {
  // Validate the frame is from our app, not injected
  if (frame.url !== 'http://localhost:5173' && !frame.url.startsWith('file://')) {
    throw new Error('Invalid frame origin');
  }
}
```

#### Step 4: Implementation (Main Process)

```typescript
// src/main/helpers/ipcHandlers.ts
import { dialog } from 'electron';
import { readFile, writeFile } from 'fs/promises';
import { ipcMainHandle } from './ipcWrappers';

export function registerIpcHandlers() {
  // TypeScript enforces: payload type and return type must match mappings
  ipcMainHandle('file:select', async (payload) => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: payload.filters || [],
      title: payload.title,
      defaultPath: payload.defaultPath,
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null; // Type: OutputPayloadMapping['file:select']
    }

    const filePath = result.filePaths[0];
    const fileName = filePath.split(/[\\/]/).pop() || '';

    return { filePath, fileName }; // TypeScript validates this matches!
  });

  ipcMainHandle('file:read', async (payload) => {
    const content = await readFile(payload.filePath, 'utf-8');
    return { content, filePath: payload.filePath };
  });

  ipcMainHandle('file:save', async (payload) => {
    const result = await dialog.showSaveDialog({
      defaultPath: payload.defaultPath,
      filters: payload.filters || [],
    });

    if (result.canceled || !result.filePath) {
      return { success: false, filePath: '' };
    }

    await writeFile(result.filePath, payload.content, 'utf-8');
    return { success: true, filePath: result.filePath };
  });

  ipcMainHandle('dialog:confirm', async (payload) => {
    const result = await dialog.showMessageBox({
      type: 'question',
      buttons: ['Cancel', 'OK'],
      defaultId: 1,
      title: payload.title || 'Confirm',
      message: payload.message,
      detail: payload.detail,
    });

    return { confirmed: result.response === 1 };
  });
}
```

#### Step 5: Usage (Renderer)

```typescript
// src/renderer/features/pdf-files/components/PdfUpload.tsx

// Full type safety and autocomplete!
const handleSelectPdf = async () => {
  const file = await window.electron.selectFile({
    title: 'Select PDF',
    filters: [{ name: 'PDF Files', extensions: ['pdf'] }],
  });

  // TypeScript knows: file is { filePath: string; fileName: string } | null
  if (!file) return;

  const fileData = await window.electron.readFile(file.filePath);
  // TypeScript knows: fileData is { content: string; filePath: string }
};
```

### 6.2 Benefits of This Pattern

✅ **Compile-Time Safety**
- Typo in channel name? TypeScript error
- Wrong payload shape? TypeScript error
- Missing return value? TypeScript error

✅ **Autocomplete**
- IntelliSense shows all available channels
- Shows expected payload shape
- Shows return type

✅ **Refactor-Safe**
- Rename a channel → TypeScript updates all references
- Change payload type → All usages must be updated

✅ **Self-Documenting**
- `global.d.ts` is the single source of truth
- Types show exactly what each IPC call does

✅ **Centralized Contracts**
- All IPC APIs defined in one place
- Easy to review what's exposed to renderer
- Security audit is straightforward

---

## 7. API Layer Design

### 7.1 Three-Layer API Architecture

Each feature has a three-layer API structure:

```
features/email-configs/api/
├── types.ts              # TypeScript types (matches backend Pydantic models)
├── schemas.ts            # Zod schemas (runtime validation)
├── emailConfigsApi.ts    # Raw Axios calls
└── emailConfigsQueries.ts # React Query hooks
```

#### Layer 1: Types

```typescript
// src/renderer/features/email-configs/api/types.ts

/**
 * Domain types matching FastAPI Pydantic models
 * Generated/maintained in sync with backend
 */

export type EmailProviderType = 'outlook_com';
export type EmailConfigStatus = 'active' | 'inactive' | 'error';

export interface EmailConfig {
  id: number;
  name: string;
  email_address: string;
  provider_type: EmailProviderType;
  status: EmailConfigStatus;
  last_sync: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailConfigCreate {
  name: string;
  email_address: string;
  provider_type: EmailProviderType;
}

export interface EmailConfigUpdate {
  name?: string;
  status?: EmailConfigStatus;
}

export interface EmailConfigListResponse {
  items: EmailConfig[];
  total: number;
  page: number;
  page_size: number;
}
```

#### Layer 2: Raw API Calls

```typescript
// src/renderer/features/email-configs/api/emailConfigsApi.ts

import { apiClient } from '@/shared/api/client';
import type {
  EmailConfig,
  EmailConfigCreate,
  EmailConfigUpdate,
  EmailConfigListResponse,
} from './types';

/**
 * Raw API functions - pure HTTP calls
 * No caching, no state management - just fetch/send data
 */
export const emailConfigsApi = {
  /**
   * Get all email configs
   */
  getAll: async (params?: {
    page?: number;
    pageSize?: number;
    status?: string;
  }): Promise<EmailConfigListResponse> => {
    const response = await apiClient.get('/email-configs', { params });
    return response.data;
  },

  /**
   * Get single email config by ID
   */
  getById: async (id: number): Promise<EmailConfig> => {
    const response = await apiClient.get(`/email-configs/${id}`);
    return response.data;
  },

  /**
   * Create new email config
   */
  create: async (data: EmailConfigCreate): Promise<EmailConfig> => {
    const response = await apiClient.post('/email-configs', data);
    return response.data;
  },

  /**
   * Update existing email config
   */
  update: async (id: number, data: EmailConfigUpdate): Promise<EmailConfig> => {
    const response = await apiClient.patch(`/email-configs/${id}`, data);
    return response.data;
  },

  /**
   * Delete email config
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/email-configs/${id}`);
  },

  /**
   * Test email config connection
   */
  test: async (id: number): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post(`/email-configs/${id}/test`);
    return response.data;
  },
};
```

#### Layer 3: React Query Hooks

```typescript
// src/renderer/features/email-configs/api/emailConfigsQueries.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emailConfigsApi } from './emailConfigsApi';
import type { EmailConfigCreate, EmailConfigUpdate } from './types';

/**
 * Query key factory for email configs
 * Centralized key management prevents cache bugs
 */
export const emailConfigsKeys = {
  all: ['email-configs'] as const,
  lists: () => [...emailConfigsKeys.all, 'list'] as const,
  list: (filters: Record<string, any>) =>
    [...emailConfigsKeys.lists(), filters] as const,
  details: () => [...emailConfigsKeys.all, 'detail'] as const,
  detail: (id: number) => [...emailConfigsKeys.details(), id] as const,
};

/**
 * Query: Get all email configs
 * Includes caching, background refetch, error handling
 */
export function useEmailConfigs(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
}) {
  return useQuery({
    queryKey: emailConfigsKeys.list(params || {}),
    queryFn: () => emailConfigsApi.getAll(params),
    staleTime: 30_000, // Consider fresh for 30 seconds
    gcTime: 5 * 60_000, // Keep in cache for 5 minutes
  });
}

/**
 * Query: Get single email config by ID
 */
export function useEmailConfig(id: number) {
  return useQuery({
    queryKey: emailConfigsKeys.detail(id),
    queryFn: () => emailConfigsApi.getById(id),
    enabled: id > 0, // Only fetch if valid ID
  });
}

/**
 * Mutation: Create new email config
 * Includes optimistic updates and cache invalidation
 */
export function useCreateEmailConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: EmailConfigCreate) => emailConfigsApi.create(data),
    onSuccess: () => {
      // Invalidate list queries to trigger refetch
      queryClient.invalidateQueries({ queryKey: emailConfigsKeys.lists() });
    },
  });
}

/**
 * Mutation: Update email config
 */
export function useUpdateEmailConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: EmailConfigUpdate }) =>
      emailConfigsApi.update(id, data),
    onSuccess: (updatedConfig) => {
      // Update the cache for this specific config
      queryClient.setQueryData(
        emailConfigsKeys.detail(updatedConfig.id),
        updatedConfig
      );
      // Invalidate lists to refresh
      queryClient.invalidateQueries({ queryKey: emailConfigsKeys.lists() });
    },
  });
}

/**
 * Mutation: Delete email config
 */
export function useDeleteEmailConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => emailConfigsApi.delete(id),
    onSuccess: (_data, deletedId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: emailConfigsKeys.detail(deletedId) });
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: emailConfigsKeys.lists() });
    },
  });
}

/**
 * Mutation: Test email config connection
 */
export function useTestEmailConfig() {
  return useMutation({
    mutationFn: (id: number) => emailConfigsApi.test(id),
  });
}
```

### 7.2 Shared API Infrastructure

#### Axios Client Configuration

```typescript
// src/renderer/shared/api/client.ts

import axios from 'axios';
import { API_BASE_URL } from './config';

/**
 * Global Axios instance for all API calls
 * Configured with base URL, timeouts, interceptors
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptors registered in app/providers.tsx
export default apiClient;
```

#### API Configuration

```typescript
// src/renderer/shared/api/config.ts

/**
 * API configuration from environment variables
 * Supports different URLs for dev/staging/prod
 */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 30_000;

export const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === 'true';
```

#### Request Interceptor (Auth)

```typescript
// src/renderer/shared/api/interceptors/auth.ts

import type { InternalAxiosRequestConfig } from 'axios';

/**
 * Add authentication token to all requests
 */
export function authInterceptor(
  config: InternalAxiosRequestConfig
): InternalAxiosRequestConfig {
  const token = localStorage.getItem('auth_token');

  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
}
```

#### Response Interceptor (Error Handling)

```typescript
// src/renderer/shared/api/interceptors/errors.ts

import type { AxiosError } from 'axios';
import { toast } from '@/shared/hooks/useToast';

/**
 * Global error handler for API responses
 * Maps backend errors to user-friendly messages
 */
export function errorInterceptor(error: AxiosError) {
  if (error.response) {
    // Server responded with error status
    const status = error.response.status;
    const data = error.response.data as any;

    switch (status) {
      case 400:
        toast.error(data.detail || 'Invalid request');
        break;
      case 401:
        toast.error('Unauthorized - please log in');
        // Redirect to login
        window.location.href = '/login';
        break;
      case 403:
        toast.error('Access denied');
        break;
      case 404:
        toast.error('Resource not found');
        break;
      case 500:
        toast.error('Server error - please try again later');
        break;
      default:
        toast.error('An error occurred');
    }
  } else if (error.request) {
    // Request made but no response received
    toast.error('Network error - check your connection');
  }

  return Promise.reject(error);
}
```

#### Interceptor Registration

```typescript
// src/renderer/app/providers.tsx

import { useEffect } from 'react';
import { apiClient } from '@/shared/api/client';
import { authInterceptor } from '@/shared/api/interceptors/auth';
import { errorInterceptor } from '@/shared/api/interceptors/errors';

export function ApiProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Register request interceptor
    const reqInterceptor = apiClient.interceptors.request.use(authInterceptor);

    // Register response interceptor
    const resInterceptor = apiClient.interceptors.response.use(
      (response) => response,
      errorInterceptor
    );

    // Cleanup on unmount
    return () => {
      apiClient.interceptors.request.eject(reqInterceptor);
      apiClient.interceptors.response.eject(resInterceptor);
    };
  }, []);

  return <>{children}</>;
}
```

### 7.3 Mock API Support

For UI development without backend:

```typescript
// src/renderer/features/email-configs/mocks/emailConfigsMocks.ts

import { http, HttpResponse } from 'msw';
import type { EmailConfig } from '../api/types';

const mockEmailConfigs: EmailConfig[] = [
  {
    id: 1,
    name: 'Work Email',
    email_address: 'work@company.com',
    provider_type: 'outlook_com',
    status: 'active',
    last_sync: '2025-10-15T10:30:00Z',
    created_at: '2025-10-01T08:00:00Z',
    updated_at: '2025-10-15T10:30:00Z',
  },
  // ... more mocks
];

export const emailConfigsHandlers = [
  http.get('/email-configs', () => {
    return HttpResponse.json({
      items: mockEmailConfigs,
      total: mockEmailConfigs.length,
      page: 1,
      page_size: 20,
    });
  }),

  http.post('/email-configs', async ({ request }) => {
    const body = await request.json();
    const newConfig = {
      id: mockEmailConfigs.length + 1,
      ...body,
      status: 'active',
      last_sync: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    mockEmailConfigs.push(newConfig);
    return HttpResponse.json(newConfig, { status: 201 });
  }),

  // ... other handlers
];
```

Toggle via environment variable:

```bash
# .env.development
VITE_USE_MOCK_API=true   # Use mocks
VITE_USE_MOCK_API=false  # Use real backend
```

---

## 8. Routing Architecture

### 8.1 TanStack Router

**Why TanStack Router?**
- Type-safe file-based routing
- URL search params with validation
- Route-level code splitting
- Nested layouts
- Type-safe navigation

### 8.2 Route Structure

```
src/renderer/pages/
├── __root.tsx                    # Root layout (sidebar, header)
├── index.tsx                     # Home page (/)
├── email-configs/
│   ├── index.tsx                 # List page (/email-configs)
│   ├── $id.tsx                   # Detail page (/email-configs/:id)
│   └── new.tsx                   # Create page (/email-configs/new)
├── templates/
│   ├── index.tsx                 # /templates
│   ├── $id/
│   │   ├── index.tsx             # /templates/:id
│   │   └── edit.tsx              # /templates/:id/edit
│   └── builder.tsx               # /templates/builder
├── pipelines/
│   ├── index.tsx                 # /pipelines
│   ├── $id.tsx                   # /pipelines/:id
│   └── builder/
│       └── $id.tsx               # /pipelines/builder/:id
├── pdf-files.tsx                 # /pdf-files
├── eto-runs/
│   ├── index.tsx                 # /eto-runs
│   └── $id.tsx                   # /eto-runs/:id
└── settings.tsx                  # /settings
```

### 8.3 Route Examples

#### Root Layout

```typescript
// src/renderer/pages/__root.tsx

import { createRootRoute, Outlet } from '@tanstack/react-router';
import { Sidebar } from '@/shared/ui/Sidebar';
import { Header } from '@/shared/ui/Header';

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          <Outlet /> {/* Child routes render here */}
        </main>
      </div>
    </div>
  );
}
```

#### List Page with Search Params

```typescript
// src/renderer/pages/email-configs/index.tsx

import { createFileRoute } from '@tanstack/react-router';
import { z } from 'zod';
import { useEmailConfigs } from '@/features/email-configs/api/emailConfigsQueries';
import { EmailConfigList } from '@/features/email-configs/components/EmailConfigList';

// Validate search params
const searchParamsSchema = z.object({
  page: z.number().int().positive().optional().default(1),
  status: z.enum(['active', 'inactive', 'error']).optional(),
});

export const Route = createFileRoute('/email-configs/')({
  validateSearch: searchParamsSchema,
  component: EmailConfigsPage,
});

function EmailConfigsPage() {
  const { page, status } = Route.useSearch(); // Type-safe!
  const navigate = Route.useNavigate();

  const { data, isLoading, error } = useEmailConfigs({ page, status });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Email Configurations</h1>

      <EmailConfigList
        configs={data?.items || []}
        isLoading={isLoading}
        onPageChange={(newPage) =>
          navigate({ search: { page: newPage, status } })
        }
      />
    </div>
  );
}
```

#### Detail Page with Params

```typescript
// src/renderer/pages/email-configs/$id.tsx

import { createFileRoute } from '@tanstack/react-router';
import { useEmailConfig } from '@/features/email-configs/api/emailConfigsQueries';
import { EmailConfigDetail } from '@/features/email-configs/components/EmailConfigDetail';

export const Route = createFileRoute('/email-configs/$id')({
  component: EmailConfigDetailPage,
});

function EmailConfigDetailPage() {
  const { id } = Route.useParams(); // Type-safe! id is string
  const numericId = Number(id);

  const { data: config, isLoading } = useEmailConfig(numericId);

  if (isLoading) return <div>Loading...</div>;
  if (!config) return <div>Email config not found</div>;

  return <EmailConfigDetail config={config} />;
}
```

#### Nested Route (Pipeline Builder)

```typescript
// src/renderer/pages/pipelines/builder/$id.tsx

import { createFileRoute } from '@tanstack/react-router';
import { usePipeline } from '@/features/pipelines/api/pipelinesQueries';
import { PipelineBuilder } from '@/features/pipelines/components/PipelineBuilder';

export const Route = createFileRoute('/pipelines/builder/$id')({
  component: PipelineBuilderPage,
});

function PipelineBuilderPage() {
  const { id } = Route.useParams();
  const { data: pipeline } = usePipeline(Number(id));

  return (
    <div className="h-full">
      {pipeline && <PipelineBuilder pipeline={pipeline} />}
    </div>
  );
}
```

### 8.4 Router Configuration

```typescript
// src/renderer/app/router.tsx

import { createRouter } from '@tanstack/react-router';
import { routeTree } from './routeTree.gen'; // Auto-generated

export const router = createRouter({
  routeTree,
  defaultPreload: 'intent', // Preload on hover
  defaultPreloadDelay: 100,
});

// Type augmentation for type-safe navigation
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
```

---

## 9. State Management

### 9.1 State Classification

We use different tools for different types of state:

| State Type | Tool | Example |
|------------|------|---------|
| **Server State** | React Query | Email configs, templates, pipelines |
| **URL State** | TanStack Router | Pagination, filters, active tab |
| **Local UI State** | useState | Form inputs, modals, dropdowns |
| **Shared UI State** | Context + useState | Theme, sidebar collapsed |
| **Electron State** | IPC + useState | File paths, window state |

**No global state library (Redux, Zustand) needed** - React Query handles most needs.

### 9.2 React Query Benefits

**Problem Without React Query:**

```typescript
// Manual state management - painful!
function EmailConfigsList() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch('/api/email-configs')
      .then(res => res.json())
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  // Every component needs this data? Duplicate code.
  // User navigates away and back? Refetch everything.
  // Create new config? Manually update state.
  // Background updates? Manual polling.
}
```

**With React Query:**

```typescript
function EmailConfigsList() {
  const { data, isLoading, error } = useEmailConfigs();
  // That's it! React Query handles:
  // - Caching (share data across components)
  // - Background refetching
  // - Stale-while-revalidate
  // - Request deduplication
  // - Automatic retries
  // - Loading/error states
}
```

**Mutations Example:**

```typescript
function CreateEmailConfigForm() {
  const createMutation = useCreateEmailConfig();

  const handleSubmit = async (data) => {
    await createMutation.mutateAsync(data);
    // React Query automatically invalidates and refetches list!
    // No manual state updates needed
  };

  return (
    <form onSubmit={handleSubmit}>
      <button disabled={createMutation.isPending}>
        {createMutation.isPending ? 'Creating...' : 'Create'}
      </button>
      {createMutation.isError && <div>Error: {createMutation.error.message}</div>}
    </form>
  );
}
```

### 9.3 Query Client Configuration

```typescript
// src/renderer/app/queryClient.ts

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // Consider data fresh for 30 seconds
      gcTime: 5 * 60_000, // Keep unused data in cache for 5 minutes
      retry: 1, // Retry failed requests once
      refetchOnWindowFocus: true, // Refetch when user returns to app
      refetchOnReconnect: true, // Refetch when network reconnects
    },
    mutations: {
      retry: 0, // Don't retry mutations (could duplicate actions)
    },
  },
});
```

---

## 10. Feature Module Design

### 10.1 Feature Structure

Each feature is self-contained:

```
features/email-configs/
├── api/                      # Backend communication
│   ├── types.ts
│   ├── emailConfigsApi.ts
│   └── emailConfigsQueries.ts
├── components/               # Feature-specific UI
│   ├── EmailConfigList.tsx
│   ├── EmailConfigForm.tsx
│   ├── EmailConfigCard.tsx
│   └── EmailConfigDetail.tsx
├── hooks/                    # Feature-specific hooks
│   └── useEmailConfigForm.ts
└── mocks/                    # Mock data for development
    └── emailConfigsMocks.ts
```

### 10.2 Component Example

```typescript
// src/renderer/features/email-configs/components/EmailConfigList.tsx

import { useNavigate } from '@tanstack/react-router';
import { useDeleteEmailConfig } from '../api/emailConfigsQueries';
import { EmailConfigCard } from './EmailConfigCard';
import type { EmailConfig } from '../api/types';

interface EmailConfigListProps {
  configs: EmailConfig[];
  isLoading: boolean;
  onPageChange: (page: number) => void;
}

export function EmailConfigList({
  configs,
  isLoading,
  onPageChange,
}: EmailConfigListProps) {
  const navigate = useNavigate();
  const deleteMutation = useDeleteEmailConfig();

  const handleDelete = async (id: number) => {
    const confirmed = await window.electron.confirm(
      'Delete this email configuration?',
      { detail: 'This action cannot be undone.' }
    );

    if (confirmed) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleEdit = (id: number) => {
    navigate({ to: '/email-configs/$id', params: { id: String(id) } });
  };

  if (isLoading) {
    return <div>Loading email configurations...</div>;
  }

  return (
    <div className="space-y-4">
      {configs.map((config) => (
        <EmailConfigCard
          key={config.id}
          config={config}
          onEdit={() => handleEdit(config.id)}
          onDelete={() => handleDelete(config.id)}
        />
      ))}
    </div>
  );
}
```

### 10.3 Custom Hook Example

```typescript
// src/renderer/features/email-configs/hooks/useEmailConfigForm.ts

import { useState } from 'react';
import { z } from 'zod';
import { useCreateEmailConfig } from '../api/emailConfigsQueries';
import type { EmailConfigCreate } from '../api/types';

const emailConfigSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email_address: z.string().email('Invalid email address'),
  provider_type: z.enum(['outlook_com']),
});

export function useEmailConfigForm(onSuccess?: () => void) {
  const [formData, setFormData] = useState<EmailConfigCreate>({
    name: '',
    email_address: '',
    provider_type: 'outlook_com',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const createMutation = useCreateEmailConfig();

  const handleChange = (field: keyof EmailConfigCreate, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const handleSubmit = async () => {
    // Validate with Zod
    const result = emailConfigSchema.safeParse(formData);

    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      result.error.errors.forEach((err) => {
        if (err.path[0]) {
          fieldErrors[err.path[0]] = err.message;
        }
      });
      setErrors(fieldErrors);
      return;
    }

    // Submit to API
    try {
      await createMutation.mutateAsync(formData);
      onSuccess?.();
    } catch (error) {
      // Error handled by interceptor
    }
  };

  return {
    formData,
    errors,
    handleChange,
    handleSubmit,
    isSubmitting: createMutation.isPending,
    isSuccess: createMutation.isSuccess,
  };
}
```

---

## 11. Backend Integration

### 11.1 API Mapping

Our frontend features map directly to backend routers:

| Frontend Feature | Backend Router | Base Path |
|-----------------|----------------|-----------|
| `features/email-configs` | `EmailConfigRouter` | `/email-configs` |
| `features/templates` | `TemplateRouter` | `/templates` |
| `features/pipelines` | `PipelineRouter` | `/pipelines` |
| `features/pdf-files` | `PdfFileRouter` | `/pdf-files` |
| `features/eto-runs` | `EtoRunRouter` | `/eto-runs` |

### 11.2 Type Synchronization Strategy

**Goal:** Keep frontend TypeScript types in sync with backend Pydantic models.

**Options:**

1. **Manual sync** (initial approach)
   - Copy types from Pydantic models
   - Update when backend changes
   - Simplest, but requires discipline

2. **Shared types package** (future)
   - Generate TypeScript types from Pydantic models
   - Tools: `pydantic-to-typescript`, `datamodel-code-generator`
   - Guarantees sync, but adds complexity

3. **OpenAPI generation** (future)
   - FastAPI auto-generates OpenAPI spec
   - Use `openapi-typescript` to generate client types
   - Most robust, but requires build pipeline

**Current Approach:** Manual sync with clear naming conventions and comments.

```typescript
// src/renderer/features/email-configs/api/types.ts

/**
 * EmailConfig model
 * Backend: server/src/features/email_configs/domain/models.py - EmailConfig
 */
export interface EmailConfig {
  id: number;
  name: string;
  email_address: string;
  provider_type: EmailProviderType;
  status: EmailConfigStatus;
  last_sync: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * EmailConfigCreate schema
 * Backend: server/src/features/email_configs/schemas/requests.py - EmailConfigCreateRequest
 */
export interface EmailConfigCreate {
  name: string;
  email_address: string;
  provider_type: EmailProviderType;
}
```

### 11.3 Error Handling

Backend errors follow this structure:

```python
# Backend (FastAPI)
class ErrorResponse(BaseModel):
    error_code: str  # e.g., "EMAIL_CONFIG_NOT_FOUND"
    message: str     # User-friendly message
    details: dict | None = None
```

Frontend maps these to UI messages:

```typescript
// src/renderer/shared/api/interceptors/errors.ts

export function errorInterceptor(error: AxiosError) {
  if (error.response?.data) {
    const errorData = error.response.data as {
      error_code?: string;
      message?: string;
      details?: Record<string, any>;
    };

    // Map backend error codes to user messages
    const message = getErrorMessage(errorData.error_code, errorData.message);
    toast.error(message);
  }

  return Promise.reject(error);
}

function getErrorMessage(code?: string, fallback?: string): string {
  const messages: Record<string, string> = {
    EMAIL_CONFIG_NOT_FOUND: 'Email configuration not found',
    EMAIL_CONFIG_ALREADY_EXISTS: 'An email config with this address already exists',
    EMAIL_AUTH_FAILED: 'Failed to authenticate with email provider',
    TEMPLATE_NOT_FOUND: 'Template not found',
    PIPELINE_VALIDATION_FAILED: 'Pipeline configuration is invalid',
    // ... more mappings
  };

  return messages[code || ''] || fallback || 'An error occurred';
}
```

### 11.4 Authentication Flow

```typescript
// src/renderer/features/auth/api/authApi.ts

export const authApi = {
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { email, password });
    const { access_token, user } = response.data;

    // Store token
    localStorage.setItem('auth_token', access_token);
    localStorage.setItem('user', JSON.stringify(user));

    return { user, token: access_token };
  },

  logout: async () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  },

  getCurrentUser: () => {
    const userJson = localStorage.getItem('user');
    return userJson ? JSON.parse(userJson) : null;
  },
};
```

---

## 12. Development Workflow

### 12.1 Environment Setup

```bash
# Install dependencies
cd client
npm install

# Development mode (Electron + Vite dev server)
npm run dev

# Build for production
npm run build

# Package for distribution
npm run package
```

### 12.2 Environment Variables

**Development (`.env.development`):**

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK_API=false
VITE_LOG_LEVEL=debug
```

**Production (`.env.production`):**

```bash
VITE_API_BASE_URL=https://api.production.example.com
VITE_USE_MOCK_API=false
VITE_LOG_LEVEL=error
```

### 12.3 Mock API Development

**Scenario:** Backend API not ready yet, but you want to build UI.

**Solution:** Use Mock Service Worker (MSW)

```typescript
// src/renderer/mocks/browser.ts

import { setupWorker } from 'msw/browser';
import { emailConfigsHandlers } from '@/features/email-configs/mocks/emailConfigsMocks';
import { templatesHandlers } from '@/features/templates/mocks/templatesMocks';

export const worker = setupWorker(
  ...emailConfigsHandlers,
  ...templatesHandlers,
  // ... other handlers
);
```

```typescript
// src/renderer/index.tsx

import { worker } from './mocks/browser';

async function enableMocking() {
  if (import.meta.env.VITE_USE_MOCK_API !== 'true') {
    return;
  }

  return worker.start({
    onUnhandledRequest: 'warn',
  });
}

enableMocking().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});
```

Now toggle `VITE_USE_MOCK_API=true` and develop without backend!

### 12.4 Testing Strategy

**Unit Tests:**
- Test custom hooks
- Test utility functions
- Test API layer functions
- Tool: Vitest

**Component Tests:**
- Test feature components in isolation
- Mock API calls with MSW
- Tool: Vitest + React Testing Library

**E2E Tests:**
- Test full user workflows
- Use real backend (test environment)
- Tool: Playwright

---

## 13. Examples

### 13.1 Complete Feature Example: Email Configs

This shows all layers working together.

#### 1. Types

```typescript
// features/email-configs/api/types.ts
export interface EmailConfig {
  id: number;
  name: string;
  email_address: string;
  provider_type: 'outlook_com';
  status: 'active' | 'inactive' | 'error';
  last_sync: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailConfigCreate {
  name: string;
  email_address: string;
  provider_type: 'outlook_com';
}
```

#### 2. API Layer

```typescript
// features/email-configs/api/emailConfigsApi.ts
import { apiClient } from '@/shared/api/client';

export const emailConfigsApi = {
  getAll: async () => {
    const response = await apiClient.get('/email-configs');
    return response.data;
  },
  create: async (data: EmailConfigCreate) => {
    const response = await apiClient.post('/email-configs', data);
    return response.data;
  },
};
```

#### 3. React Query

```typescript
// features/email-configs/api/emailConfigsQueries.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useEmailConfigs() {
  return useQuery({
    queryKey: ['email-configs'],
    queryFn: emailConfigsApi.getAll,
  });
}

export function useCreateEmailConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: emailConfigsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-configs'] });
    },
  });
}
```

#### 4. Component

```typescript
// features/email-configs/components/EmailConfigList.tsx
export function EmailConfigList() {
  const { data: configs, isLoading } = useEmailConfigs();
  const createMutation = useCreateEmailConfig();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      {configs?.map((config) => (
        <div key={config.id}>{config.name}</div>
      ))}
      <button onClick={() => createMutation.mutate({ /* ... */ })}>
        Create New
      </button>
    </div>
  );
}
```

#### 5. Page/Route

```typescript
// pages/email-configs/index.tsx
import { createFileRoute } from '@tanstack/react-router';
import { EmailConfigList } from '@/features/email-configs/components/EmailConfigList';

export const Route = createFileRoute('/email-configs/')({
  component: () => (
    <div>
      <h1>Email Configurations</h1>
      <EmailConfigList />
    </div>
  ),
});
```

### 13.2 PDF Upload Flow (Electron + HTTP)

Complete workflow showing Electron file selection + HTTP upload:

```typescript
// features/pdf-files/components/PdfUpload.tsx

import { useState } from 'react';
import { apiClient } from '@/shared/api/client';

export function PdfUpload() {
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    setUploading(true);

    try {
      // 1. Electron: Select file from OS
      const file = await window.electron.selectFile({
        title: 'Select PDF',
        filters: [{ name: 'PDF Files', extensions: ['pdf'] }],
      });

      if (!file) {
        setUploading(false);
        return;
      }

      // 2. Electron: Read file content
      const fileData = await window.electron.readFile(file.filePath);

      // 3. Convert to base64 for HTTP transfer
      const base64Content = btoa(fileData.content);

      // 4. HTTP: Upload to FastAPI server
      const response = await apiClient.post('/pdf-files', {
        file_name: file.fileName,
        content: base64Content,
      });

      console.log('Uploaded PDF ID:', response.data.id);

      // 5. Electron: Show success notification
      await window.electron.showNotification(
        'Upload Complete',
        `${file.fileName} uploaded successfully`
      );
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <button onClick={handleUpload} disabled={uploading}>
      {uploading ? 'Uploading...' : 'Upload PDF'}
    </button>
  );
}
```

### 13.3 Pipeline Builder (Complex Feature)

This shows a more complex feature with nested components:

```
features/pipelines/
├── api/
│   ├── types.ts              # Pipeline, Module types
│   ├── pipelinesApi.ts       # CRUD operations
│   └── pipelinesQueries.ts   # React Query hooks
├── components/
│   ├── PipelineList.tsx
│   ├── PipelineBuilder/      # Complex sub-component
│   │   ├── index.tsx         # Main builder component
│   │   ├── Canvas.tsx        # React Flow canvas
│   │   ├── ModulePalette.tsx # Draggable module list
│   │   ├── WiringPanel.tsx   # Connection config
│   │   └── useBuilderState.ts # Builder state hook
│   └── PipelineDetail.tsx
└── hooks/
    └── usePipelineValidation.ts
```

---

## Conclusion

This design specification provides a complete blueprint for building the ETO Client application with:

✅ **Clear architecture** - Three-layer Electron structure with defined responsibilities
✅ **Type safety** - End-to-end TypeScript with compile-time guarantees
✅ **Modern patterns** - React Query, TanStack Router, Feature-Sliced Design
✅ **Scalability** - Feature-based organization that grows with the app
✅ **Developer experience** - Mock APIs, hot reload, excellent DX
✅ **Security** - Context isolation, explicit API surface, no Node in renderer
✅ **Backend integration** - Clear mapping to FastAPI server architecture

**Next Steps:**
1. Review and approve this design specification
2. Set up project scaffolding with this structure
3. Implement one feature (email-configs) as a reference implementation
4. Use that as a template for remaining features

---

**References:**

- Electron Security: https://www.electronjs.org/docs/latest/tutorial/security
- Feature-Sliced Design: https://feature-sliced.design/
- Bulletproof React: https://github.com/alan2207/bulletproof-react
- TanStack Router: https://tanstack.com/router
- TanStack Query: https://tanstack.com/query
- electron-react-boilerplate: https://github.com/electron-react-boilerplate/electron-react-boilerplate
