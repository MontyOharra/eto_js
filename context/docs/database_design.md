# Database Design

## Overview
The ETO system uses Microsoft SQL Server as its primary database with a schema focused on the email-to-order processing workflow, PDF template management, and transformation pipeline operations.

## Database Configuration
- **Provider**: SQL Server with ODBC connectivity
- **ORM**: Prisma (client-side) + SQLAlchemy (server-side)
- **Connection**: Pooled connections via pyodbc driver
- **Schema Management**: Prisma migrations + manual SQL scripts

## ETO System Schema

### **Template & PDF Processing System**

#### **PDF Templates & Field Extraction**
Tables supporting the spatial box drawing system for PDF data extraction:
- **`pdf_template`** - Template definitions for different document types
- **`extraction_field`** - Spatial field definitions with coordinates
- **`template_field_mapping`** - Relationships between templates and fields

#### **Email & Document Processing**
- **`email_inbox`** - Tracked email sources and processing status
- **`pdf_document`** - Processed PDF files and metadata
- **`extraction_result`** - Raw extracted data from PDF processing

### **Transformation Pipeline System**

#### **Pipeline Configuration**
- **`transformation_pipeline`** - Visual pipeline definitions
- **`pipeline_module`** - Available transformation modules
- **`module_connection`** - Data flow connections between modules
- **`pipeline_execution_log`** - Processing history and results

#### **Data Transformation**
- **`field_mapping`** - Input/output field relationships
- **`transformation_rule`** - Custom processing logic
- **`data_validation`** - Field validation rules and results

### **User & Authentication System**

#### **`user`** - ETO system users
```sql
id (Primary Key)
username, password_hash, password_salt
email, first_name, last_name
role, permissions
date_created, last_login
is_active
```

#### **Session Management**
- **`user_session`** - Active user sessions
- **`user_activity_log`** - User action tracking

### **Reference & Static Data**

#### **Geographic Data**
Supporting address parsing and validation:
- **`static_us_city`** - US cities with coordinates
- **`static_us_state`** - State abbreviations and names
- **`static_us_zip_code`** - ZIP code to coordinate mapping
- **`static_us_airport`** - Airport codes and locations
- **`static_country`** - International country references

#### **ACI (Air Cargo Industry) Data**
```sql
aci_data:
  aci_key, city, state, country, zip_code
  airport_code, carrier, area
  rate_minimum, rate_100, rate_1000, rate_2000, rate_5000
```

### **System Operations**

#### **Processing Status & Monitoring**
- **`processing_queue`** - Email/PDF processing queue
- **`error_log`** - System errors and exceptions
- **`system_configuration`** - Application settings

#### **Audit & Change History**
Comprehensive tracking across ETO operations:
- **`template_change_history`**
- **`pipeline_change_history`**
- **`user_change_history`**
- **`processing_audit_log`**

**Change History Structure**:
```sql
id (Primary Key)
entity_id, entity_type
user_id (Who made the change)
date_changed (When)
changes (JSON description of modifications)
```

## Key Design Patterns

### **Document Processing Pipeline**
Email → PDF Download → Template Matching → Field Extraction → Data Validation → Transformation Pipeline

### **Spatial Field Definition**
- PDF coordinates stored for extraction box boundaries
- Multi-line text area support for addresses and descriptions
- Variable-length field handling within spatial bounds

### **Visual Pipeline Architecture**
- Modular transformation components
- Drag-and-drop connection system
- Real-time data flow visualization

### **Comprehensive Audit Trail**
- All processing operations logged with timestamps
- User attribution for manual operations
- Complete data lineage from email to final output

### **Template Management**
- Reusable template definitions for document types
- Field validation and error correction workflows
- Version control for template modifications

## Performance Considerations

### **Indexing Strategy**
- Primary keys and foreign key relationships
- Text search indexes on extracted content
- Spatial indexes for coordinate-based queries
- Performance indexes on frequently queried fields

### **Data Flow Optimization**
- Efficient PDF processing with memory management
- Batch processing capabilities for high-volume operations
- Connection pooling for concurrent processing

### **Storage Management**
- PDF file storage with compression
- Extracted data caching for pipeline reprocessing
- Archival strategies for processed documents

## Integration Points

### **Email System Integration**
- Gmail/Outlook API connections
- Attachment processing workflows
- Email status tracking and notifications

### **External System Preparation**
The ETO schema is designed to prepare clean, structured data for eventual integration with target logistics systems through a future plugin architecture.