# System Architecture

## Overview
The ETO (Email-to-Order) system is a comprehensive PDF processing pipeline designed for logistics companies to automatically extract structured order data from email attachments and transform it through customizable visual pipelines.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│  Email Source   │───▶│   Main ETO Server    │───▶│  Transformation      │
│  (Gmail/Outlook)│    │                      │    │  Pipeline Server     │
└─────────────────┘    └──────────────────────┘    └──────────────────────┘
                                │                           │
                                ▼                           ▼
                       ┌─────────────────┐         ┌──────────────────────┐
                       │  Electron App   │◀────────│  Pipeline Modules    │
                       │  (Desktop UI)   │         │  Registry & Execution│
                       └─────────────────┘         └──────────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  SQL Server     │
                       │  Database       │
                       └─────────────────┘
```

## Component Architecture

### 1. **Client Application (Electron + React)**
- **Technology**: Electron desktop app with React frontend
- **Purpose**: Main user interface for document processing and pipeline management
- **Key Features**:
  - PDF viewer with spatial template creation
  - Visual transformation pipeline builder
  - Real-time data processing interface
  - Order management and tracking

### 2. **Main ETO Server (Python Flask)**
- **Location**: `server/`
- **Technology**: Python Flask with SQL Server integration
- **Purpose**: Core email processing and PDF extraction engine
- **Key Features**:
  - Email ingestion from Gmail/Outlook APIs
  - PDF processing with spatial field extraction
  - Template matching and order generation
  - Error handling and retry mechanisms

### 3. **Transformation Pipeline Server (Python Flask)**
- **Location**: `transformation_pipeline_server/`
- **Technology**: Python Flask microservice
- **Purpose**: Handles data transformation pipelines with modular processing
- **Key Features**:
  - Visual pipeline analysis and execution
  - Modular transformation system
  - Field mapping and data flow management
  - Real-time processing capabilities

### 4. **Database Layer (SQL Server)**
- **Technology**: Microsoft SQL Server with Prisma ORM
- **Purpose**: Persistent storage for all system data
- **Key Schema Areas**:
  - Order management (open_order, invoiced_order, etc.)
  - Customer and address data
  - Template and extraction field definitions
  - User management and audit trails

## Data Flow Architecture

### Email Processing Pipeline
```
Email Inbox → PDF Download → Template Matching → Field Extraction → Order Creation → Database Storage
```

### Transformation Pipeline
```
Input Data → Pipeline Analysis → Module Execution → Field Mapping → Output Generation
```

### Template Creation Workflow
```
PDF Upload → Spatial Box Drawing → Field Definition → Template Validation → Template Storage
```

## Service Communication

- **Client ↔ Main Server**: HTTP REST APIs for order management and template operations
- **Client ↔ Pipeline Server**: HTTP REST APIs for pipeline execution and module management  
- **Inter-Service**: Services communicate via HTTP APIs when needed
- **Database Access**: Each service connects directly to SQL Server using connection pooling

## Security Model

- **Authentication**: User-based authentication with session management
- **Authorization**: Role-based access control through user permissions
- **Data Protection**: SQL Server encryption and secure connection strings
- **API Security**: CORS configuration and request validation

## Deployment Architecture

- **Development**: Local development with hot-reload capabilities
- **Client**: Electron app distributable for Windows/Mac/Linux
- **Servers**: Python services deployable to any environment supporting Flask
- **Database**: SQL Server instance (local or cloud)

## Scalability Considerations

- **Horizontal Scaling**: Pipeline server can be scaled independently
- **Processing Queue**: Email processing designed for background execution
- **Module System**: Transformation modules are pluggable and extensible
- **Database**: SQL Server supports clustering and replication for high availability