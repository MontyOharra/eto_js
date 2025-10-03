# Transformation Pipeline System Specification

## Document Purpose
This specification defines the architecture, data flow, and component structure for the transformation pipeline builder system. It serves as the single source of truth for implementation.

---

## 1. HIGH-LEVEL PAGE ARCHITECTURE

The transformation pipeline system consists of three primary pages under the `/transformation_pipeline` route:

### 1.1 Pipeline Home Page
**Route:** `/transformation_pipeline`

**Purpose:** Dashboard displaying all saved pipelines with management capabilities

**Components:**
- Pipeline list/grid view
- Pipeline summary cards
- Create new pipeline button
- Navigation to view/create pages

**Data Requirements:**
- Fetch pipeline summaries from backend
- Display: name, description, module count, connection count, created date, active status

**User Actions:**
- View pipeline (navigate to view page)
- Create new pipeline (navigate to create page)

**API Endpoints:**
- `GET /api/pipelines?summary=true` - Fetch all pipeline summaries

---

### 1.2 Pipeline View Page
**Route:** `/transformation_pipeline/view/:pipelineId`

**Purpose:** Read-only visualization of a saved pipeline

**Layout:**
```
┌─────────────────────────────────────────┐
│ Header (Pipeline name, description,    │
│         metadata, back button)          │
├─────────────────────────────────────────┤
│                                         │
│   PipelineGraph Component               │
│   (viewOnly = true)                     │
│                                         │
│   - No module selector pane             │
│   - No editing interactions             │
│   - Display only                        │
│                                         │
└─────────────────────────────────────────┘
```

**Components:**
- Header (non-editable pipeline info)
- PipelineGraph (view-only mode)

**State Management:**
```typescript
interface ViewPageState {
  pipeline: Pipeline | null;               // Full pipeline data
  moduleTemplates: ModuleTemplate[];       // All module templates (for rendering)
  loading: boolean;
  error: string | null;
}
```

**Data Requirements:**
- **Page owns and fetches data** (not PipelineGraph)
- Fetch full pipeline data on page load
- Fetch all module templates (needed to reconstruct module instances)
- Parse `pipeline_json` field → PipelineState
- Parse `visual_json` field → VisualState
- Pass both pipeline state and module templates to PipelineGraph component

**Data Fetching Flow:**
```typescript
useEffect(() => {
  // Fetch both pipeline and module templates in parallel
  Promise.all([
    fetch(`/api/pipelines/${pipelineId}`),
    fetch('/api/modules')
  ]).then(([pipelineData, templates]) => {
    setPipeline(pipelineData);
    setModuleTemplates(templates);
  });
}, [pipelineId]);
```

**User Actions:**
- View pipeline structure
- Pan/zoom canvas
- Inspect modules and connections
- Navigate back to home

**API Endpoints:**
- `GET /api/pipelines/:pipelineId` - Fetch complete pipeline data
- `GET /api/modules` - Fetch all module templates (needed for reconstruction)

**Data Structure:**
```typescript
// Pipeline response from API
{
  id: string,
  name: string,
  description: string,
  pipeline_json: PipelineState,  // Modules, connections, entry points
  visual_json: VisualState,      // Canvas positions
  created_at: string,
  is_active: boolean,
  module_count: number,
  connection_count: number
}

// Module templates response (same as Create Page)
ModuleTemplate[] = [
  {
    id: string,
    version: string,
    title: string,
    description: string,
    kind: "transform" | "action" | "control",
    category: string,
    color: string,
    meta: { io_shape: {...} },
    config_schema: {...}
  },
  ...
]
```

**Props Passed to PipelineGraph:**
```typescript
<PipelineGraph
  moduleTemplates={moduleTemplates}        // For reconstructing modules
  initialPipelineState={pipeline.pipeline_json}
  initialVisualState={pipeline.visual_json}
  viewOnly={true}
/>
```

---

### 1.3 Pipeline Create Page
**Route:** `/transformation_pipeline/create`

**Purpose:** Interactive editor for building new pipelines

**Layout:**
```
┌─────────────────────────────────────────┐
│ Header (editable name, description,    │
│         save button, cancel button)     │
├──────────┬──────────────────────────────┤
│          │                              │
│ Module   │   PipelineGraph Component    │
│ Selector │   (viewOnly = false)         │
│ Pane     │                              │
│          │   - Full editing enabled     │
│ [List of │   - Module placement         │
│  module  │   - Connection creation      │
│  types]  │   - Node manipulation        │
│          │                              │
│          │                              │
└──────────┴──────────────────────────────┘
```

**Components:**
- Header with editable fields (name, description)
- Module Selector Pane (sidebar, receives modules as props)
- PipelineGraph (edit mode, receives moduleTemplates as props)
- Save/Cancel controls

**State Management:**
```typescript
interface CreatePageState {
  moduleTemplates: ModuleTemplate[];       // All module templates (for pane & graph)
  selectedModuleId: string | null;         // Module selected for placement
  pipelineName: string;                    // Editable pipeline name
  pipelineDescription: string;             // Editable description
  loading: boolean;
  error: string | null;
}
```

**Initial State:**
- Empty PipelineState (no modules, no connections) - managed by PipelineGraph
- Empty VisualState (no positions) - managed by PipelineGraph
- Default pipeline name: "Untitled Pipeline"
- Default description: empty
- selectedModuleId: null

**Data Requirements:**
- **Page owns and fetches data** (not child components)
- Fetch all module templates on page mount
- Pass moduleTemplates to Module Selector Pane for display
- Pass moduleTemplates to PipelineGraph for module instantiation
- Pass selectedModuleId to PipelineGraph for placement

**Data Fetching Flow:**
```typescript
useEffect(() => {
  // Fetch all module templates on mount
  async function loadModules() {
    setLoading(true);
    try {
      const response = await fetch('/api/modules');
      const templates = await response.json();
      setModuleTemplates(templates);
    } catch (err) {
      setError('Failed to load module templates');
    } finally {
      setLoading(false);
    }
  }
  loadModules();
}, []);
```

**User Actions:**
- Edit pipeline name/description
- Select module from pane → updates selectedModuleId
- Click canvas → places selected module at position
- Create connections between nodes
- Add/remove dynamic nodes
- Change node types
- Edit node names
- Save pipeline → POST to backend
- Cancel and return to home

**API Endpoints:**
- `GET /api/modules` - Fetch all module templates with full metadata
- `POST /api/pipelines` - Save new pipeline

**Module Template Structure:**
```typescript
// Response from GET /api/modules
ModuleTemplate[] = [
  {
    id: string,              // e.g., "text_cleaner"
    version: string,         // e.g., "1.0.0"
    title: string,           // Display name
    description: string,     // Module description
    kind: string,            // "transform" | "action" | "control"
    category: string,        // "Text Processing", "Flow Control", etc.
    color: string,           // Hex color for UI
    meta: {
      io_shape: {
        inputs: {
          nodes: NodeGroup[]   // New unified structure
        },
        outputs: {
          nodes: NodeGroup[]   // New unified structure
        },
        type_params: {         // TypeVar domains
          [typeVar: string]: string[]
        }
      }
    },
    config_schema: object    // JSON schema for module config
  },
  ...
]
```

**Props Passed to Module Selector Pane:**
```typescript
<ModuleSelectorPane
  modules={moduleTemplates}                // All available modules
  selectedModuleId={selectedModuleId}      // Currently selected module
  onModuleSelect={(id) => setSelectedModuleId(id)}  // Selection handler
/>
```

**Props Passed to PipelineGraph:**
```typescript
<PipelineGraph
  moduleTemplates={moduleTemplates}        // For instantiating modules
  selectedModuleId={selectedModuleId}      // Module to place on canvas click
  onModulePlaced={() => setSelectedModuleId(null)}  // Clear selection after placement
  viewOnly={false}
/>
```

**Save Data Structure:**
```typescript
// POST /api/pipelines payload
{
  name: string,
  description: string,
  pipeline_json: {
    entry_points: EntryPoint[],
    modules: ModuleInstance[],
    connections: Connection[]
  },
  visual_json: {
    modules: { [moduleId: string]: { x: number, y: number } },
    entryPoints: { [nodeId: string]: { x: number, y: number } }
  }
}
```

---

## 2. DATA FLOW ARCHITECTURE

### Module Data Strategy
**Approach:** Parent pages own and fetch module template data

**Rationale:**
- Single API call on page load
- Clear data ownership (props down, callbacks up)
- Instant module placement (no loading delays)
- Simpler state management (no prop drilling complexity)
- Better user experience for interactive editor
- Module count is manageable (~10-50 modules)
- Child components remain stateless regarding module data

**Create Page Flow:**
```
Pipeline Create Page loads
    ↓
GET /api/modules (fetch all templates)
    ↓
Store in Create Page state (moduleTemplates)
    ↓
Pass moduleTemplates as props to Module Selector Pane
    ↓
User selects module → onModuleSelect callback
    ↓
Create Page updates selectedModuleId state
    ↓
Pass selectedModuleId + moduleTemplates to PipelineGraph
    ↓
User clicks canvas → PipelineGraph creates ModuleInstance
    ↓
Module appears on canvas immediately
    ↓
onModulePlaced callback clears selection
```

**View Page Flow:**
```
Pipeline View Page loads
    ↓
GET /api/pipelines/:id + GET /api/modules (parallel fetch)
    ↓
Store in View Page state (pipeline, moduleTemplates)
    ↓
Pass both to PipelineGraph as props
    ↓
PipelineGraph reconstructs module instances using templates
    ↓
Display read-only visualization
```

---

## 3. PAGE NAVIGATION FLOW

```
/transformation_pipeline (Home)
    ↓ Click "Create Pipeline"
    → /transformation_pipeline/create (Create Page)
        ↓ Click "Save"
        → Save to backend
        → Navigate back to home

/transformation_pipeline (Home)
    ↓ Click "View" on pipeline card
    → /transformation_pipeline/view/:id (View Page)
        ↓ Click "Back"
        → Navigate back to home
```

---

## 4. COMPONENT RESPONSIBILITIES

### Home Page
- Fetch and display pipeline summaries
- Provide navigation to create/view pages
- Handle pipeline list filtering/sorting (future)

### View Page
- **Owns and fetches data:**
  - Fetch full pipeline data (GET /api/pipelines/:id)
  - Fetch all module templates (GET /api/modules)
- Pass data down to PipelineGraph as props
- Render read-only pipeline visualization
- No state mutations

### Create Page
- **Owns and fetches data:**
  - Fetch module templates on mount (GET /api/modules)
- **Manages selection state:**
  - selectedModuleId (which module user wants to place)
- **Coordinates child components:**
  - Pass modules to Module Selector Pane
  - Pass modules + selectedModuleId to PipelineGraph
  - Handle callbacks from children
- **Manages pipeline metadata:**
  - Pipeline name, description
- **Handles save operations:**
  - Collect state from PipelineGraph
  - POST to backend

### PipelineGraph Component
- **Shared stateless component** used in both View and Create pages
- **Receives data via props:**
  - moduleTemplates (for creating/reconstructing modules)
  - selectedModuleId (Create mode only)
  - initialPipelineState (View mode only)
  - initialVisualState (View mode only)
- **Props determine behavior:**
  - `viewOnly={true}`: Read-only visualization
  - `viewOnly={false}`: Full editing capabilities
- **Responsibilities:**
  - Manages internal pipeline state (modules, connections, entry points)
  - Manages visual state (positions)
  - Canvas interactions (pan, zoom)
  - Renders modules, connections, entry points
  - Handles module placement when selectedModuleId present
  - Exposes state via callbacks for saving
- **Does NOT fetch data** - purely presentational with local state

### Module Selector Pane
- **Stateless component** - only used in Create Page
- **Receives data via props:**
  - modules (array of ModuleTemplate)
  - selectedModuleId (currently selected module)
  - onModuleSelect (callback when user selects module)
- **Responsibilities:**
  - Display available module templates
  - Filter by search term (local state)
  - Filter by type using carousel (local state)
  - Group by category
  - Handle module selection → call onModuleSelect
  - Collapsible sidebar (local state)
- **Does NOT fetch data** - purely presentational

---

## 5. MODULE SELECTOR PANE SPECIFICATION

**Location:** Left sidebar in Pipeline Create Page only

**Purpose:** Provides searchable, filterable interface for selecting and placing modules onto the canvas

### 5.1 Layout Structure

```
┌────────────────────────────┐
│ [<] Module Pane        [>] │ ← Collapse/Expand Button
├────────────────────────────┤
│ 🔍 [Search modules...]     │ ← Search Bar
├────────────────────────────┤
│ [<] [Transform] [>]        │ ← Type Carousel Selector
│     ← All | Transform →    │   (centered current selection)
├────────────────────────────┤
│ Text Processing            │ ← Category Label
│  ┌──────────────────────┐  │
│  │ Text Cleaner         │  │ ← Module Card
│  │ Transform            │  │
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │ Text Splitter        │  │
│  │ Transform            │  │
│  └──────────────────────┘  │
│                            │
│ Data Conversion            │ ← Another Category
│  ┌──────────────────────┐  │
│  │ Type Converter       │  │
│  │ Control              │  │
│  └──────────────────────┘  │
│                            │
│ ...more categories         │
└────────────────────────────┘
```

### 5.2 Component Breakdown

#### **5.2.1 Collapse/Expand Control**
- **Position:** Top-right corner
- **States:**
  - Expanded: `[>]` button, full width (e.g., 300px)
  - Collapsed: `[<]` button, narrow width (e.g., 40px), only button visible
- **Behavior:**
  - Click to toggle between expanded/collapsed
  - Animation: smooth width transition
  - Collapsed state shows only expand button, no content

#### **5.2.2 Search Bar**
- **Position:** Top of pane, below collapse button
- **Input Type:** Text input with search icon
- **Placeholder:** "Search modules..."
- **Behavior:**
  - Real-time filtering as user types
  - Case-insensitive substring match on `module.title`
  - Empty search = show all modules (respecting type filter)
  - No results = show "No modules found" message
- **Filtering Logic:**
  ```typescript
  filteredModules = allModules.filter(module =>
    module.title.toLowerCase().includes(searchTerm.toLowerCase())
  );
  ```

#### **5.2.3 Type Carousel Selector**
- **Position:** Below search bar
- **Types Available:**
  - "All" (default)
  - "Transform"
  - "Action"
  - "Control" *(recommended name for logic/routing modules)*
- **Visual Layout:**
  ```
  [←] [Current Type] [→]
  ```
  - Left arrow: navigate to previous type
  - Center: current selected type (highlighted)
  - Right arrow: navigate to next type
- **Behavior:**
  - Click arrows to cycle through types
  - Wraps around (after last type, goes to first)
  - Selected type is highlighted/emphasized
  - Filters modules by `module.kind` field
  - "All" shows modules of all types
- **Styling:**
  - Current type: larger, bold, primary color
  - Arrows: subtle, clickable buttons
  - Inactive types: hidden (only show current + arrows)

**Type Cycling Order:**
```
All → Transform → Action → Control → (back to) All
```

#### **5.2.4 Module Cards (Grouped by Category)**

**Data Structure:**
```typescript
interface ModuleTemplate {
  id: string;                    // e.g., "text_cleaner"
  version: string;               // e.g., "1.0.0"
  title: string;                 // Display name: "Text Cleaner"
  description: string;           // Short description
  kind: "transform" | "action" | "control";  // Module type
  category: string;              // Sub-category: "Text Processing", "Data Conversion", etc.
  color: string;                 // Hex color for UI
  meta: ModuleMeta;              // I/O shape and constraints
  config_schema: object;         // JSON schema
}
```

**Grouping Logic:**
1. Filter modules by search term (if any)
2. Filter modules by selected type (if not "All")
3. Group remaining modules by `category` field
4. Sort categories alphabetically
5. Within each category, sort modules alphabetically by `title`

**Category Section Layout:**
```
Category Name                    ← Category header (bold, larger text)
├─ Module Card 1                 ← First module in category
├─ Module Card 2                 ← Second module in category
└─ Module Card N                 ← Last module in category

Next Category Name
├─ Module Card 1
└─ ...
```

**Module Card Design:**
```
┌──────────────────────────┐
│ Module Title             │ ← Bold, primary text
│ Type badge               │ ← Small colored badge (transform/action/control)
│ Short description...     │ ← Truncated description (2 lines max)
└──────────────────────────┘
```

**Module Card Properties:**
- **Title:** `module.title`
- **Type Badge:** `module.kind` with color coding
- **Description:** `module.description` (truncated)
- **Color Indicator:** Left border or background tint using `module.color`
- **Hover State:** Slight elevation/highlight
- **Cursor:** Grab cursor (indicates draggable)

#### **5.2.5 Interaction Behaviors**

**Module Selection & Placement:**
- **Click to select:** Single click selects module (highlights card)
- **Click canvas:** Place selected module at click position
- **Drag & drop (optional future enhancement):**
  - Drag module card onto canvas
  - Drop at cursor position

**Current Implementation (Simple):**
1. User clicks module card
2. Module card highlights (selected state)
3. User clicks anywhere on PipelineGraph canvas
4. Module instance created at click position
5. Selection cleared (ready for next module)

**Props Interface:**
```typescript
interface ModuleSelectorPaneProps {
  modules: ModuleTemplate[];           // Received from parent Create Page
  selectedModuleId: string | null;     // Currently selected module (from parent)
  onModuleSelect: (id: string | null) => void;  // Callback to parent
}
```

**Internal State Management:**
```typescript
interface ModulePaneState {
  searchTerm: string;                  // Current search input (local state)
  selectedType: string;                // "All" | "Transform" | "Action" | "Control" (local state)
  isCollapsed: boolean;                // Pane collapsed state (local state)
}
```

### 5.3 Filtering & Display Logic

**Filter Pipeline:**
```typescript
// 1. Start with modules from props
let displayModules = props.modules;

// 2. Apply search filter (local state)
if (searchTerm) {
  displayModules = displayModules.filter(m =>
    m.title.toLowerCase().includes(searchTerm.toLowerCase())
  );
}

// 3. Apply type filter (local state)
if (selectedType !== "All") {
  displayModules = displayModules.filter(m =>
    m.kind === selectedType.toLowerCase()
  );
}

// 4. Group by category
const grouped = groupBy(displayModules, m => m.category);

// 5. Sort categories and modules
const sortedCategories = Object.keys(grouped).sort();
sortedCategories.forEach(category => {
  grouped[category].sort((a, b) => a.title.localeCompare(b.title));
});

// 6. Render
return sortedCategories.map(category => (
  <CategorySection
    key={category}
    name={category}
    modules={grouped[category]}
    selectedModuleId={props.selectedModuleId}
    onModuleSelect={props.onModuleSelect}
  />
));
```

### 5.4 Data Flow

**Component receives modules via props (does not fetch):**

```typescript
function ModuleSelectorPane({ modules, selectedModuleId, onModuleSelect }: ModuleSelectorPaneProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('All');
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Filter and display modules from props
  const displayModules = useMemo(() => {
    return modules
      .filter(m => searchTerm ? m.title.toLowerCase().includes(searchTerm.toLowerCase()) : true)
      .filter(m => selectedType !== 'All' ? m.kind === selectedType.toLowerCase() : true);
  }, [modules, searchTerm, selectedType]);

  // Handle module card click
  const handleModuleClick = (moduleId: string) => {
    onModuleSelect(moduleId);  // Notify parent
  };

  return (
    // ... render UI
  );
}
```

**Parent (Create Page) owns and provides the data:**
```typescript
// In Pipeline Create Page component:
const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);
const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);

useEffect(() => {
  // Fetch modules on page mount
  fetch('/api/modules')
    .then(res => res.json())
    .then(modules => setModuleTemplates(modules));
}, []);

return (
  <ModuleSelectorPane
    modules={moduleTemplates}
    selectedModuleId={selectedModuleId}
    onModuleSelect={setSelectedModuleId}
  />
);
```

**Module Template Structure (received via props.modules):**
```json
[
  {
    "id": "text_cleaner",
    "version": "1.0.0",
    "title": "Text Cleaner",
    "description": "Removes whitespace and normalizes text",
    "kind": "transform",
    "category": "Text Processing",
    "color": "#3B82F6",
    "meta": { "io_shape": {...} },
    "config_schema": {...}
  },
  {
    "id": "if_selector",
    "version": "1.0.0",
    "title": "If Selector",
    "description": "Routes data based on condition",
    "kind": "control",
    "category": "Flow Control",
    "color": "#8B5CF6",
    "meta": { "io_shape": {...} },
    "config_schema": {...}
  }
]
```

### 5.5 Visual Design Specifications

**Dimensions:**
- Expanded width: `320px`
- Collapsed width: `48px`
- Height: `100%` (full viewport height minus header)

**Colors (Dark Theme):**
- Background: `#1F2937` (gray-800)
- Card background: `#374151` (gray-700)
- Card hover: `#4B5563` (gray-600)
- Selected card: `#3B82F6` (blue-500 border)
- Text primary: `#F9FAFB` (gray-50)
- Text secondary: `#D1D5DB` (gray-300)
- Type badges:
  - Transform: `#3B82F6` (blue-500)
  - Action: `#10B981` (green-500)
  - Control: `#8B5CF6` (purple-500)

**Typography:**
- Category headers: `14px`, `600 weight`, `uppercase`, letter-spacing
- Module title: `14px`, `500 weight`
- Module type: `11px`, `500 weight`, `uppercase`
- Module description: `12px`, `400 weight`, line clamp 2

**Spacing:**
- Search bar margin: `12px`
- Type carousel margin: `12px`
- Category section gap: `24px`
- Module card gap: `8px`
- Card padding: `12px`

**Animations:**
- Collapse/expand: `300ms ease-in-out`
- Card hover: `150ms ease`
- Selection highlight: `200ms ease`

### 5.6 Edge Cases & States

**Empty States:**
- `props.modules` is empty array: Show "No modules available" message
- No search results: "No modules found for '{searchTerm}'"
- No modules in selected type: "No {type} modules available"

**Loading States:**
- Parent is loading modules: `props.modules` will be empty array initially
  - Component shows "No modules available" or loading placeholder
  - Parent controls loading UI (shows spinner in its own layout)
- During filter: No loading state (instant client-side filtering)

**Error States:**
- Parent handles API errors (Module Pane doesn't fetch, so no error handling needed)
- Parent can choose to pass empty array or show error UI in its own layout

---

## 6. PIPELINEGRAPH COMPONENT SPECIFICATION (BASELINE)

**Purpose:** Interactive canvas component for visualizing and editing transformation pipelines. Shared between View (read-only) and Create (editable) pages.

**Foundation:** Built on **React Flow** (@xyflow/react) library for canvas, pan/zoom, and connection management.

### 6.1 Technology Choice

**Library:** React Flow (https://reactflow.dev)
- **Version:** @xyflow/react v12.8.6+
- **Why React Flow:**
  - Handles dynamic node positioning automatically (solves variable-length node names, variable node counts)
  - Built-in pan/zoom controls
  - Built-in connection validation
  - Automatic bezier curve rendering between connection points
  - Performance optimized (only re-renders changed elements)
  - Battle-tested (used by Stripe, Typeform, etc.)
  - Actively maintained (updated regularly)

**Installation:**
```bash
npm install @xyflow/react
```

### 6.2 Component Structure

**PipelineGraph is a wrapper around ReactFlow:**

```typescript
import { ReactFlow, Controls, Background } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface PipelineGraphProps {
  // Mode control
  viewOnly: boolean;

  // Module templates (for creating/reconstructing modules)
  moduleTemplates: ModuleTemplate[];

  // Initial state (optional - for View page)
  initialPipelineState?: PipelineState;
  initialVisualState?: VisualState;

  // Create mode only
  selectedModuleId?: string | null;
  onModulePlaced?: () => void;
}

function PipelineGraph({
  viewOnly,
  moduleTemplates,
  initialPipelineState,
  initialVisualState,
  selectedModuleId,
  onModulePlaced
}: PipelineGraphProps) {
  // Internal state
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // Initialize from props (View mode)
  useEffect(() => {
    if (initialPipelineState && initialVisualState) {
      const rfNodes = convertModulesToNodes(initialPipelineState, initialVisualState);
      const rfEdges = convertConnectionsToEdges(initialPipelineState.connections);
      setNodes(rfNodes);
      setEdges(rfEdges);
    }
  }, []);

  return (
    <div className="pipeline-graph" style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={viewOnly ? undefined : onNodesChange}
        onEdgesChange={viewOnly ? undefined : onEdgesChange}
        nodesDraggable={!viewOnly}
        nodesConnectable={!viewOnly}
        elementsSelectable={!viewOnly}
        nodeTypes={nodeTypes}
        fitView
      >
        <Controls />
        <Background variant="dots" gap={12} size={1} />
      </ReactFlow>
    </div>
  );
}
```

### 6.3 Layout & Visual Design

**Component fills its container:**
- Parent component controls dimensions
- PipelineGraph uses `width: 100%` and `height: 100%`
- Does NOT overlay other components at same level
- Positioned alongside Module Selector Pane in Create page
- Positioned below header in View page

**Canvas Features:**
- **Background:** Dotted grid pattern (React Flow `<Background>` component)
- **Pan:** Click and drag canvas to move viewport
- **Zoom:** Mouse wheel or Controls component buttons
- **Controls Position:** Top-right corner (React Flow default)

**Controls Component (Built-in):**
```
┌─────────────────────────────────┐
│                      [+]  ← Zoom in
│                      [⊙]  ← Fit view (recenter)
│                      [-]  ← Zoom out
│                      [⛶]  ← Fullscreen (optional)
```

### 6.4 Core State Management

**Internal State:**

```typescript
interface PipelineGraphState {
  // React Flow state (nodes = modules + entry points)
  nodes: Node[];           // React Flow nodes
  edges: Edge[];           // React Flow edges (connections)

  // Our domain state (derived from/synchronized with nodes/edges)
  pipelineState: PipelineState;   // modules, connections, entry_points
  visualState: VisualState;       // module positions
}
```

**State Initialization:**

**View Mode (read-only):**
```typescript
// Initialize from props on mount
useEffect(() => {
  if (initialPipelineState && initialVisualState) {
    // Convert our format → React Flow format
    const rfNodes = convertModulesToNodes(
      initialPipelineState.modules,
      initialVisualState.modules,
      moduleTemplates
    );
    const rfEdges = convertConnectionsToEdges(
      initialPipelineState.connections
    );

    setNodes(rfNodes);
    setEdges(rfEdges);
  }
}, [initialPipelineState, initialVisualState, moduleTemplates]);
```

**Create Mode (empty start):**
```typescript
// Start with empty state
const [nodes, setNodes] = useState<Node[]>([]);
const [edges, setEdges] = useState<Edge[]>([]);

// Module placement happens via selectedModuleId prop
useEffect(() => {
  if (selectedModuleId) {
    // User has module selected, show visual indicator
    // Actual placement happens on canvas click
  }
}, [selectedModuleId]);
```

### 6.5 Data Conversion Functions

**ModuleInstance → React Flow Node:**

```typescript
function convertModuleToNode(
  moduleInstance: ModuleInstance,
  position: { x: number; y: number },
  template: ModuleTemplate
): Node {
  return {
    id: moduleInstance.module_instance_id,
    type: 'module',  // Custom node type
    position,
    data: {
      moduleInstance,   // Full module data
      template          // Template for metadata
    }
  };
}

function convertModulesToNodes(
  modules: ModuleInstance[],
  positions: Record<string, { x: number; y: number }>,
  templates: ModuleTemplate[]
): Node[] {
  return modules.map(module => {
    const template = templates.find(t =>
      module.module_ref.startsWith(`${t.id}:`)
    );
    const position = positions[module.module_instance_id] || { x: 0, y: 0 };

    return convertModuleToNode(module, position, template!);
  });
}
```

**Connection → React Flow Edge:**

```typescript
function convertConnectionToEdge(connection: Connection): Edge {
  return {
    id: `${connection.from_node_id}-${connection.to_node_id}`,
    source: findModuleIdForNode(connection.from_node_id),  // Module ID
    target: findModuleIdForNode(connection.to_node_id),    // Module ID
    sourceHandle: connection.from_node_id,  // Specific output node
    targetHandle: connection.to_node_id,    // Specific input node
    type: 'default'  // React Flow edge type (bezier curve)
  };
}

function convertConnectionsToEdges(connections: Connection[]): Edge[] {
  return connections.map(convertConnectionToEdge);
}
```

### 6.6 Props Interface (Complete)

```typescript
interface PipelineGraphProps {
  // Mode
  viewOnly: boolean;

  // Required data
  moduleTemplates: ModuleTemplate[];

  // View mode initialization
  initialPipelineState?: PipelineState;
  initialVisualState?: VisualState;

  // Create mode - module placement
  selectedModuleId?: string | null;
  onModulePlaced?: () => void;

  // Future: state extraction for saving
  // ref will expose: getState() => { pipelineState, visualState }
}
```

### 6.7 viewOnly Behavior

**When `viewOnly={true}` (View Page):**
- `nodesDraggable={false}` - Modules cannot be moved
- `nodesConnectable={false}` - Cannot create new connections
- `elementsSelectable={false}` - Cannot select elements
- `onNodesChange={undefined}` - No node change handlers
- `onEdgesChange={undefined}` - No edge change handlers
- Pan and zoom still work (read-only visualization)

**When `viewOnly={false}` (Create Page):**
- `nodesDraggable={true}` - Can drag modules
- `nodesConnectable={true}` - Can create connections by dragging
- `elementsSelectable={true}` - Can select/delete elements
- Change handlers enabled for state updates

### 6.8 File Structure

```
client/src/renderer/components/transformation-pipeline/
├── PipelineGraph.tsx              # Main wrapper component
├── pipeline-graph/
│   ├── conversion.ts              # Data conversion utilities
│   ├── ModuleNode.tsx             # Custom node type (Section 7)
│   └── types.ts                   # React Flow type extensions
```

### 6.9 Dependencies

**React Flow Imports:**
```typescript
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  Connection,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
```

**Required Types:**
```typescript
// Extend React Flow's Node type with our data
type ModuleNode = Node<{
  moduleInstance: ModuleInstance;
  template: ModuleTemplate;
}>;
```

### 6.10 Next Steps (Future Sections)

**Not included in baseline (defer for now):**
- Custom ModuleNode component rendering (Section 7)
- Connection validation logic
- TypeVar coordination
- Module placement on canvas click
- State extraction for saving
- Entry point handling
- Configuration UI

**Baseline scope (implement first):**
- Empty ReactFlow canvas
- Pan/zoom controls working
- Background grid
- Accept viewOnly prop
- Basic component structure

---

## 7. NEXT SECTIONS TO DEFINE

- ModuleNode custom component (renders module with inputs/outputs as Handles)
- Connection validation and type constraints
- Module placement interaction
- Entry points rendering
- State extraction for saving
- Configuration panel

---

**Document Status:** In Progress - Baseline PipelineGraph Defined
**Last Updated:** 2025-10-02

**Completed Sections:**
- ✅ Section 1: High-level page architecture (Home, View, Create pages)
- ✅ Section 2: Data flow architecture (parent-owns-data strategy)
- ✅ Section 3: Page navigation flow
- ✅ Section 4: Component responsibilities
- ✅ Section 5: Module Selector Pane specification (complete with props-based architecture)
- ✅ Section 6: PipelineGraph component specification (baseline with React Flow)

**Next Section:** ModuleNode custom component rendering
