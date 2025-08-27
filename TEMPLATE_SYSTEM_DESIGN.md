# ETO Template System - Complete Design Document

**Created**: August 26, 2025  
**Status**: Database Architecture Complete - Ready for Implementation  
**Next Phase**: Raw Text Extraction Implementation

---

## **SYSTEM OVERVIEW**

The ETO Template System enables automatic recognition and data extraction from PDF documents through exact template matching and configurable extraction pipelines.

### **Core Workflow**
1. **PDF Processing** → Extract structured objects from PDF
2. **Template Matching** → Find template with largest exact subset match of PDF objects  
3. **Data Extraction** → Execute multi-step extraction pipeline defined by matched template
4. **Order Creation** → Transform extracted data into order records
5. **File Management** → Move processed PDFs to order attachment storage

---

## **TEMPLATE MATCHING ALGORITHM**

### **Subset Matching Logic**
Templates contain signature objects (text fields, images, coordinates). A template "matches" a PDF if ALL template objects exist as an exact subset within the PDF objects.

**Selection Criteria:**
- Find all templates that are exact subsets of PDF objects
- Choose template with **most matching objects** (largest subset)
- If no templates match → status = "unrecognized"

**Examples:**
```
PDF Objects: [Image(100,100), Text("BOL#"), Text("Date:"), Text("Weight:"), Text("Customer")]

Template A: [Image(100,100), Text("BOL#"), Text("Date:")]     → 3 matches ✓
Template B: [Image(100,100), Text("BOL#")]                    → 2 matches ✓  
Template C: [Image(200,200), Text("Invoice")]                 → 0 matches ✗

Result: Template A selected (largest subset)
```

### **New Template Detection**
- Calculate **coverage ratio**: (matched_objects / total_pdf_objects)
- If coverage < template.coverage_threshold → flag `suggested_new_template = true`
- Process successfully but notify user of potential template improvement opportunity

---

## **EXTRACTION PIPELINE ARCHITECTURE**

### **Multi-Step Processing**
Each extraction rule consists of ordered steps that feed output into subsequent steps:

1. **Raw Extraction** → Extract text from PDF coordinates
2. **Data Transformation** → LLM parsing, regex processing, SQL lookups
3. **Validation** → Ensure data meets business requirements
4. **Order Mapping** → Transform to order table format

### **Step Types (Planned)**
- `raw_extract` → PDF text extraction using anchors/coordinates
- `sql_lookup` → Database queries (e.g., company name → address_id)
- `llm_parse` → LLM text processing (e.g., "DLV BY 3/15/24" → "2024-03-15")
- `regex_transform` → Pattern-based text transformation
- `validation` → Data validation rules

### **Error Handling Strategy**
- **Processing Errors** → System failures (PDF corrupt, database down) → status = "error"
- **Extraction Errors** → Business logic failures (missing field, invalid data) → status = "failure"
- **Per-Step Error Handling** → fail_rule, skip_step, use_default

---

## **DATABASE SCHEMA DESIGN**

### **Core Template Tables**

#### **pdf_templates**
```sql
CREATE TABLE pdf_templates (
  id INTEGER PRIMARY KEY,
  name VARCHAR(255),
  customer_name VARCHAR(255),
  description TEXT,
  
  -- Template matching
  signature_objects TEXT, -- JSON: objects that define this template
  signature_object_count INTEGER, -- For quick subset matching
  
  -- Improvement detection
  is_complete BOOLEAN DEFAULT FALSE, -- User-marked completeness
  coverage_threshold FLOAT DEFAULT 0.6, -- Expected coverage ratio
  
  -- Usage tracking
  usage_count INTEGER DEFAULT 0,
  last_used_at DATETIME,
  
  -- Versioning
  version INTEGER DEFAULT 1,
  is_current_version BOOLEAN DEFAULT TRUE,
  
  -- Audit
  created_by VARCHAR(255),
  created_at DATETIME,
  updated_at DATETIME,
  status VARCHAR(50) DEFAULT 'active' -- 'active', 'archived', 'draft'
);
```

#### **template_extraction_rules**
```sql
CREATE TABLE template_extraction_rules (
  id INTEGER PRIMARY KEY,
  template_id INTEGER REFERENCES pdf_templates(id),
  rule_name VARCHAR(255), -- "carrier_processing", "pickup_date_processing"
  final_target_field VARCHAR(255), -- "address_id", "pickup_date"
  is_required BOOLEAN DEFAULT TRUE,
  created_at DATETIME
);
```

#### **template_extraction_steps**
```sql
CREATE TABLE template_extraction_steps (
  id INTEGER PRIMARY KEY,
  extraction_rule_id INTEGER REFERENCES template_extraction_rules(id),
  step_number INTEGER, -- 1, 2, 3... (execution order)
  step_name VARCHAR(255), -- "extract_raw_carrier", "lookup_address_id"
  
  -- Step configuration
  step_type VARCHAR(50), -- 'raw_extract', 'sql_lookup', 'llm_parse'
  step_config TEXT, -- JSON: method-specific configuration
  
  -- Input/Output
  input_fields TEXT, -- JSON: ["carrier_raw"]
  output_field VARCHAR(255), -- "carrier_raw", "address_id"
  
  -- Error handling
  error_handling VARCHAR(50), -- 'fail_rule', 'skip_step', 'use_default'
  default_value TEXT,
  
  -- Performance tracking
  avg_execution_time_ms INTEGER DEFAULT 0,
  execution_count INTEGER DEFAULT 0,
  last_executed_at DATETIME,
  
  created_at DATETIME,
  UNIQUE(extraction_rule_id, step_number)
);
```

### **Enhanced ETO Processing Tables**

#### **pdf_files** (Updated)
```sql
CREATE TABLE pdf_files (
  id INTEGER PRIMARY KEY,
  original_filename VARCHAR(255),
  sha256_hash VARCHAR(64), -- NO unique constraint (allow duplicates)
  file_size BIGINT,
  storage_path TEXT,
  object_count INTEGER,
  objects_json TEXT, -- PDF objects for template matching
  created_at DATETIME,
  updated_at DATETIME
);
```

#### **eto_runs** (Significantly Enhanced)
```sql
CREATE TABLE eto_runs (
  id INTEGER PRIMARY KEY,
  email_id INTEGER REFERENCES emails(id),
  pdf_file_id INTEGER REFERENCES pdf_files(id),
  
  -- Processing status
  status VARCHAR(50), -- 'success', 'failure', 'unrecognized', 'error'
  error_type VARCHAR(50), -- 'processing_error', 'extraction_error', 'order_creation_error'
  error_message TEXT,
  error_details TEXT, -- JSON: detailed error info
  
  -- Template matching results
  matched_template_id INTEGER REFERENCES pdf_templates(id),
  template_version INTEGER, -- Which version was used
  template_match_coverage FLOAT, -- % of PDF objects matched
  unmatched_object_count INTEGER,
  suggested_new_template BOOLEAN DEFAULT FALSE,
  
  -- Extraction results
  extracted_data TEXT, -- JSON: field_name -> value mapping
  
  -- Pipeline execution tracking
  failed_step_id INTEGER REFERENCES template_extraction_steps(id),
  step_execution_log TEXT, -- JSON: step-by-step execution details
  
  -- Processing timeline
  started_at DATETIME,
  completed_at DATETIME,
  processing_duration_ms INTEGER,
  
  -- Order integration
  order_id INTEGER REFERENCES orders(id),
  
  -- Audit
  created_at DATETIME,
  updated_at DATETIME
);
```

---

## **STATUS CLASSIFICATION SYSTEM**

### **Three-Tier Status Model**
- **"success"** → Template matched, extraction completed, order created successfully
- **"failure"** → Template matched BUT extraction/order creation failed (user can review/fix)
- **"unrecognized"** → No template match found (user needs to create new template)
- **"error"** → System-level failure (PDF corrupt, database down, etc.)

### **Error Type Categorization**
- **"processing_error"** → System failures requiring developer attention
- **"extraction_error"** → Business logic failures requiring user review
- **"order_creation_error"** → Order creation failures (data validation, constraints)

---

## **IMPLEMENTATION PHASES**

### **PHASE 1: Foundation** (Current)
- ✅ Database schema implementation
- ✅ Basic template CRUD operations
- ✅ Raw text extraction only (single step pipelines)
- ✅ Simple template matching algorithm

### **PHASE 2: Pipeline Enhancement**
- Multi-step extraction pipelines
- LLM integration for text parsing
- SQL lookup transformations
- Advanced error handling

### **PHASE 3: User Experience**
- Template creation UI for non-technical users
- ML-assisted extraction rule generation
- Visual pipeline editor
- Performance monitoring dashboard

---

## **KEY DESIGN DECISIONS**

### **Why Exact Matching?**
- Eliminates confidence score complexity
- Provides deterministic, predictable results
- Simpler to debug and maintain
- Users know exactly when templates will/won't match

### **Why Multi-Step Pipelines?**
- Real business data requires transformation (company name → address_id)
- LLM parsing needed for variable formats ("DLV BY 3/15" → date)
- Enables complex business logic without hard-coding
- Non-technical users can eventually create rules via UI

### **Why Database-Driven Configuration?**
- No code changes needed for new extraction patterns
- ML can analyze patterns across templates
- Visual UI can manipulate database records
- Proper audit trails and versioning

---

## **FUTURE CONSIDERATIONS**

### **Template Creation Assistance**
- ML analysis of "unrecognized" PDFs to suggest template patterns
- Natural language template creation ("Extract the pickup date from the top right")
- Template similarity detection to prevent duplicates

### **Performance Optimizations**
- PDF object caching for frequently processed templates
- Parallel extraction rule execution
- Template matching algorithm optimizations

### **Advanced Features**
- Template inheritance (child templates extend parent templates)
- Conditional extraction rules (if field A = "rush", extract field B)
- Multi-page template support with page-specific rules

---

**This design provides a solid foundation for exact template matching while maintaining extensibility for future ML enhancements and user-friendly template creation workflows.**