# Technology Stack & Code Specifics

## Frontend Stack

### **Electron Desktop Application**
- **Electron**: v37.1.0 - Cross-platform desktop app framework
- **React**: v19.1.0 - Component-based UI framework  
- **TypeScript**: v5.8.3 - Type-safe JavaScript development
- **Vite**: v6.3.5 - Fast build tool and dev server
- **TanStack Router**: v1.124.0 - File-based routing system

### **UI & Styling**
- **Tailwind CSS**: v4.1.11 - Utility-first CSS framework
- **React PDF**: v10.0.1 - PDF viewing and manipulation
- **PDF.js**: v5.3.31 - PDF rendering engine

### **Data Management**
- **Prisma**: v6.11.0 - Database ORM and client generation
- **React Hooks** - State management and effects

## Backend Stack

### **Main ETO Server** (`server/`)
- **Python**: 3.x with Flask web framework
- **Flask**: v3.0.0 - Lightweight web application framework
- **Flask-CORS**: v4.0.0+ - Cross-origin resource sharing
- **SQLAlchemy**: v2.0.0+ - SQL toolkit and ORM
- **PyODBC**: v4.0.39+ - SQL Server database connectivity

### **PDF Processing**
- **PyPDF2**: v3.0.1+ - PDF manipulation and text extraction
- **PDFPlumber**: v0.7.6+ - Advanced PDF parsing and layout analysis

### **System Integration**
- **pywin32**: v306+ - Windows API integration
- **requests**: v2.31.0+ - HTTP client library
- **python-dotenv**: v1.0.0+ - Environment variable management

### **Transformation Pipeline Server** (`transformation_pipeline_server/`)
- **Python**: 3.x with Flask microservice architecture
- **Flask**: v3.0.3 - Web framework
- **Flask-CORS**: v4.0.1 - CORS handling
- **SQLAlchemy**: v2.0.31 - Database ORM
- **PyODBC**: v4.0.39+ - Database connectivity

## Database

### **Microsoft SQL Server**
- **Provider**: SQL Server with ODBC connectivity
- **ORM**: Prisma for client, SQLAlchemy for servers
- **Schema**: Comprehensive logistics domain model
- **Features**: 
  - Complex relational schema with 40+ tables
  - Change tracking and audit trails
  - Spatial data support for coordinates
  - Full-text indexing capabilities

## Development Tools

### **Build & Bundling**
- **ESBuild**: v0.25.5 - Fast JavaScript bundler
- **Electron Builder**: v26.0.12 - App packaging and distribution
- **npm-run-all**: v4.1.5 - Parallel script execution

### **Code Quality**
- **ESLint**: v9.25.0 - JavaScript/TypeScript linting
- **TypeScript ESLint**: v8.30.1 - TypeScript-specific linting rules
- **Prettier**: Integrated code formatting

### **Development Experience**
- **Hot Reload**: Vite dev server with React Fast Refresh
- **Live Reload**: Electron app restarts on main process changes
- **Source Maps**: Full debugging support
- **Environment Variables**: Separate configs for dev/prod

## Key Libraries & Frameworks

### **Client-Side Specifics**
- **@tanstack/react-router-devtools** - Development debugging
- **keytar** - Secure credential storage
- **dotenv** - Environment configuration
- **cross-env** - Cross-platform environment variables

### **Server-Side Specifics**
- **Flask application factories** - Modular app structure
- **SQLAlchemy declarative models** - Type-safe database access
- **Async processing** - Background task handling
- **Connection pooling** - Database performance optimization

## Architecture Patterns

### **Frontend Patterns**
- **Component Architecture**: Functional React components with hooks
- **File-Based Routing**: TanStack Router with TypeScript route definitions
- **State Management**: React hooks with context for global state
- **Event-Driven UI**: Mouse interactions and drag-and-drop interfaces

### **Backend Patterns**
- **RESTful APIs**: Standard HTTP endpoints with JSON payloads
- **Service Layer Architecture**: Business logic separation
- **Repository Pattern**: Data access abstraction
- **Dependency Injection**: Modular service registration

### **Database Patterns**
- **Domain-Driven Design**: Business entity modeling
- **Change Data Capture**: Audit trail implementation
- **Normalized Schema**: Proper relational design
- **Indexing Strategy**: Performance-optimized queries

## Development Workflow

### **Client Development**
```bash
npm run dev          # Start Electron app with hot reload
npm run typecheck    # TypeScript compilation check
npm run build        # Production build
npm run dist:win     # Windows executable creation
```

### **Server Development**
```bash
# Main ETO Server
./server-scripts.sh  # Build and start development server on localhost
python main.py       # Direct Flask server start
python setup-venv.sh # Environment setup

# Transformation Pipeline Server  
./server-scripts.sh  # Build and start pipeline server on localhost
python main.py       # Direct pipeline server start
```

### **Database Management**
```bash
npx prisma generate  # Generate Prisma client
npx prisma studio    # Database GUI
npx prisma migrate   # Schema migrations
```