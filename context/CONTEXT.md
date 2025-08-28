# Email-to-Order (ETO) PDF Processing System – Project Context

## 1 Problem the software solves

A trucking / logistics company receives shipment request and receipt forms from many different customers. The forms arrive as PDFs attached to e-mails and each customer formats the document differently (no industry standard).

The complete system workflow:

1. **Email Ingestion**: Automatically download PDFs from incoming emails via Outlook API
2. **PDF Processing**: Extract text objects and structural data using pdfplumber
3. **Template Matching**: Match PDFs against known templates using geometric signatures
4. **Data Extraction**: Apply stored extraction recipes to pull structured data
5. **Manual Template Creation**: For unknown PDFs, provide UI to teach the system

The current implementation focuses on the **template creation interface** for training the system on new document types.

## 2 Current System Capabilities

### Frontend (Electron + React + TypeScript)
- **PDF Viewer**: React-PDF based viewer with zoom, navigation, and overlay support
- **Template Builder**: Two-step wizard for creating extraction templates
  - Step 1: Select static objects that always exist in documents
  - Step 2: Draw spatial extraction areas for variable content
- **Spatial Box Drawing**: Click-and-drag interface for defining extraction regions
- **Real-time Visual Feedback**: Purple overlays with field labels show extraction areas
- **Field Management**: Create, edit, view, and delete extraction field definitions

### Backend (Python + FastAPI + SQLAlchemy)
- **Email Processing**: Outlook API integration for automatic PDF download
- **PDF Analysis**: pdfplumber-based text extraction and object detection
- **Template Storage**: Database persistence of templates and extraction field definitions
- **Automatic Matching**: Geometric signature matching for known document types
- **Processing Pipeline**: Background worker for handling email ingestion and PDF processing

## 3 Template Creation Workflow (Current Implementation)

### Step 1: Object Selection
1. User opens an unrecognized PDF in the Template Builder
2. PDF is processed to extract all text objects, rectangles, lines, and other elements
3. User selects which objects should always exist in this document type (static elements)
4. Objects are visually highlighted with different colors by type
5. User assigns a template name and description

### Step 2: Extraction Field Definition  
1. User switches to field-labels step with a clean PDF viewer
2. **Spatial Box Drawing**: User clicks "Draw New Field Area" and draws rectangular regions over content
3. **Variable Content Support**: Drawn areas capture any text within the region, regardless of:
   - Multi-word fields (e.g., "Forward Air, Inc" as one carrier field)
   - Variable length content (e.g., addresses that are 3-4 lines, pushing phone numbers down)
   - Changing text content (e.g., "carrier 1" vs "carrier 1234")
4. **Field Configuration**: For each drawn area, user defines:
   - Field label (e.g., "hawb", "carrier-name", "pu_addr_and_phone")
   - Description and validation rules
   - Required field designation
5. **Visual Feedback**: Purple overlays with floating labels show all defined extraction areas

### Step 3: Template Persistence
1. Template data includes both static objects and spatial extraction field definitions
2. Extraction fields stored as bounding boxes `[x0, y0, x1, y1]` in PDF coordinate space
3. Template triggers automatic reprocessing of previously unmatched PDFs
4. Future PDFs matching this template's signature use these extraction areas

## 4 Spatial Extraction Field Advantages

### Handles Complex Document Variations
- **Multi-word fields**: Single area covers "Forward Air, Inc" rather than individual words
- **Variable positioning**: Address fields accommodate 3-4 line addresses plus phone numbers
- **Content length variations**: Areas sized for maximum expected content
- **Layout flexibility**: Spatial relationships maintained across document instances

### Technical Implementation
- **PDF coordinate system**: All coordinates stored in PDF space (origin bottom-left)
- **Screen coordinate conversion**: Real-time mapping between screen and PDF coordinates
- **Zoom independence**: Extraction areas scale properly with zoom levels
- **Visual clarity**: No individual text object highlighting, only area-based overlays

## 5 Current Technical Architecture

### Frontend Components
- **TemplateBuilderModal**: Two-step wizard with dynamic sidebar states
- **PdfViewer**: Enhanced with box drawing, extraction field overlays, and mouse interactions
- **Field Management**: Create, edit, view, delete extraction field definitions

### Data Models
```typescript
interface ExtractionField {
  id: string;
  boundingBox: [number, number, number, number]; // PDF coordinates
  page: number;
  label: string;
  description: string;
  required: boolean;
  validationRegex?: string;
}
```

### API Integration
- Templates saved with both static objects and extraction field definitions
- Automatic reprocessing pipeline for previously unmatched documents
- Geometric signature matching for template recognition

## 6 Next Development Priorities

1. **Box Editing**: Add resize handles and drag-to-move capabilities for extraction areas
2. **Template Testing**: Interface to test extraction against sample documents
3. **Field Validation**: Real-time preview of extracted content during template creation
4. **Advanced Field Types**: Support for checkboxes, tables, and complex structured data
5. **Template Versioning**: Handle updates to existing templates while preserving data

---

This file captures the current understanding of the project and a high-level road-map. Feel free to reference or extend it in future tasks.
