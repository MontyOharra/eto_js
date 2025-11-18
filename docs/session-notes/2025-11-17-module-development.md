# Session Notes: Module Development and Organization
**Date**: 2025-11-17
**Branch**: master

## Overview
This session focused on building order creation infrastructure modules and reorganizing the module system with consistent categorization and color schemes.

## Modules Created

### 1. DateTime Extractor (LLM-based)
**File**: `server/src/pipeline_modules/transform/datetime_extractor.py`
**Purpose**: Extract date and time information from varied customer text formats
**Technology**: OpenAI GPT-4o-mini with optimized token-efficient prompt

**Key Features**:
- Extracts: date (YYYY-MM-DD), start_time (HH:MM), end_time (HH:MM)
- Handles edge cases:
  - "at {time}" → start_time = end_time
  - "by/before T" → end_time = T, start_time = "09:00"
  - "after/from T" → start_time = T, end_time = "16:00"
  - Year inference for partial dates
  - Various time formats (9am, 9:00, 0900, nine am, noon, 9-5)
- Token optimization: Reduced from ~591 tokens to ~100-130 tokens per request
- Estimated cost: ~$1-2/month for 200 forms/day

**Prompt Optimization**:
- Removed verbose instructions and redundant examples
- Condensed 8 detailed guidelines to concise bullet points
- Reduced from 4 examples to 1 example
- Removed duplicate format specification
- ~5x token reduction while maintaining functionality

**Category**: LLM
**Color**: Orange (#F97316)

### 2. Customer Picker (Generator)
**File**: `server/src/pipeline_modules/output/customer_picker.py`
**Purpose**: Output-only module for selecting customers with dynamic dropdown

**Key Features**:
- Queries `HTC300_G030_T010 Customers` table for active customers
- Dynamically injects customer names as enum options using `config_schema()` pattern
- Returns customer_id (int) and customer_name (str)
- No inputs - pure generator module

**Pattern Used**: Runtime enum injection via `config_schema()` method
```python
@classmethod
def config_schema(cls) -> Dict[str, Any]:
    schema = cls.ConfigModel.model_json_schema()
    # Query database and inject customer names
    schema['properties']['customer_name']['enum'] = customer_options
    return schema
```

**Category**: Database
**Color**: Yellow (#EAB308)

### 3. Carrier Lookup
**File**: `server/src/pipeline_modules/lookup/carrier_lookup.py`
**Purpose**: Find carrier address ID from customer-provided carrier name

**Evolution**:
- **Version 1**: Fuzzy matching on FavCompany + FavLocnName → Low confidence scores (65% for exact matches)
- **Version 2**: Use location name primarily, fall back to company name → Still unreliable due to name variations
- **Version 3 (Final)**: Exact lookup using Address Name Swaps table

**Implementation**:
- Uses `HTC350_G060_T100 Address Name Swaps` table
- Maps customer names (e.g., "Southwest Airlines") to system addresses (e.g., "Southwest Cargo")
- Returns carrier_id, carrier_found (bool), actual_carrier_name
- Throws error if carrier not found (explicit mapping required)

**Database**: Added `HTC_350D_DB_CONNECTION_STRING` to .env

**Category**: Database
**Color**: Yellow (#EAB308)

### 4. Address Parser
**File**: `server/src/pipeline_modules/transform/address_parser.py`
**Purpose**: Parse US address strings into structured components

**Technology**: usaddress library (ML-based)

**Outputs**:
- address_line_1: Street number, directional, name, type
- address_line_2: Suite/Apt/Unit info
- city, state, zip_code

**Design Iteration**:
- Initial: Single `street_address` output
- Final: Separated into line_1 and line_2 per user feedback

**Category**: Text
**Color**: Sky blue (#0EA5E9)

### 5. String Concatenate
**File**: `server/src/pipeline_modules/transform/string_concatenate.py`
**Purpose**: Concatenate variable number of strings with separator

**Key Features**:
- Accepts 2+ string inputs (no maximum)
- Configurable separator (default: " ")
- Uses `context.inputs` ordering to maintain order
- Handles None values and type conversion

**Category**: Text
**Color**: Sky blue (#0EA5E9)

### 6. Text Cleaner Enhancement
**File**: `server/src/pipeline_modules/transform/text_cleaner.py`
**Changes**: Added `replace_newlines_with_spaces` option
- Handles \n, \r\n, \r variants
- Useful for cleaning address strings before parsing

**Category**: Text
**Color**: Sky blue (#0EA5E9)

## Module Reorganization

### Category and Color Scheme

**Database Modules** (Yellow #EAB308):
- Customer Picker
- SQL Lookup
- Carrier Lookup

**LLM Modules** (Orange #F97316):
- DateTime Extractor

**Text Modules** (Sky Blue #0EA5E9):
- String Concatenate
- Address Parser
- Basic Text Cleaner

**Flow Control Modules** (White #FFFFFF):
- If Branch
- If Selector
- Data Duplicator
- Type Converter

**Number Types & Comparators** (Red Spectrum):
- int type: #DC2626 (red-600, dark red)
- float type: #FCA5A5 (red-300, light red)
- Number comparators: #EF4444 (red-500, middle ground)

**Action Modules** (Brown #92400E):
- Print Action

**Generator Modules** (Black #000000):
- Next Order Number (deregistered)

### Module Type Changes

**Changed to MiscModule**:
- SQL Lookup (from TransformModule)
- Carrier Lookup (from TransformModule)
- Customer Picker (from TransformModule)

**Deregistered**:
- Next Order Number (logic will move to create order action)

## Type System Enhancement

**Added Types**: `date` and `time` to `AllowedNodeType`
**File**: `server/src/shared/types/modules.py`

**Note**: DateTime extractor uses string outputs (not date/time types) per user preference

## Database Schemas Extracted

**Files Added**:
- `docs/access_db_schemas/HTC300_Data-01-01/HTC300_G030_T010_Customers.json`
- `docs/access_db_schemas/HTC300_Data-01-01/HTC300_G060_T010_Addresses.json`
- `docs/access_db_schemas/HTC350D_Database/HTC350_G060_T100_Address_Name_Swaps.json`

## Dependencies Added

**Package**: `openai>=1.0.0`
**Purpose**: LLM-based text extraction for datetime extractor
**Package**: `usaddress>=0.5.10`
**Purpose**: ML-based US address parsing

## Configuration Changes

**.env additions**:
```bash
# Address Name Swaps database
HTC_350D_DB_CONNECTION_STRING="Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:/HTC_Apps_Full-8-20-25/HTC350D_Database.accdb;"

# OpenAI API
OPENAI_API_KEY="[user's key]"
```

## Frontend Changes

**File**: `client/src/renderer/features/pipelines/utils/moduleUtils.ts`

**TYPE_COLORS updates**:
```typescript
int: "#DC2626"   // red-600 (dark red)
float: "#FCA5A5" // red-300 (light red)
```

## Modules Removed/Cleaned Up

**Deleted**:
- `server/src/pipeline_modules/transform/fuzzy_database_lookup.py` (replaced by carrier_lookup)
- `server/src/pipeline_modules/transform/llm_parser.py` (replaced by datetime_extractor)
- `server/src/pipeline_modules/transform/lookup_hawb.py` (obsolete)
- `server/src/pipeline_modules/action/create_order.py` (incomplete, to be reimplemented)

**Moved**:
- `sql_lookup.py` from transform/ to misc/ directory

## Key Learnings

### Dynamic Config Dropdowns Pattern
```python
@classmethod
def config_schema(cls) -> Dict[str, Any]:
    schema = cls.ConfigModel.model_json_schema()
    try:
        from shared.services.service_container import ServiceContainer
        if ServiceContainer.is_initialized():
            # Query database
            # Inject options
            schema['properties']['field_name']['enum'] = options
    except Exception as e:
        logger.error(f"Could not inject options: {e}")
    return schema
```

### LLM Prompt Optimization
- Be extremely concise with instructions
- Use 1 example max, not 4+
- Avoid redundant format specifications
- Token count directly impacts API costs
- Can achieve 5x reduction without losing accuracy

### Module Organization Philosophy
- **Database**: Yellow - anything that queries databases
- **LLM**: Orange - AI-powered extraction
- **Text**: Sky Blue - string manipulation and parsing
- **Flow Control**: White - routing without transformation
- **Actions**: Brown - side effects
- **Generators**: Black - output-only data sources

## Order Creation Progress

**Data Sources Built**:
- ✅ Customer picker (customer_id, customer_name)
- ✅ Carrier lookup (carrier_id from name)
- ✅ DateTime extractor (date, start_time, end_time)
- ✅ Address parser (line_1, line_2, city, state, zip)

**Still Needed for Order Creation**:
- Address lookup module (query addresses by parsed components)
- Create order action module (write to Orders tables)
- Additional field extractors as needed

**Reference Available**:
- Next Order Number logic (in deregistered module)
- VBA order creation analysis (in docs)
- Database schemas (in docs/access_db_schemas)

## Next Steps

1. **Build address lookup module** - Query addresses table by parsed components
2. **Create order action module** - Incorporate next order number logic and write to database
3. **Test integration** - Build complete order creation pipeline
4. **Performance optimization** - Monitor LLM costs and optimize prompts further if needed

## Testing Notes

- DateTime extractor tested with real customer examples
- Carrier lookup tested with name variations (Southwest Airlines → Southwest Cargo)
- Address parser handles street addresses and suite info correctly
- Customer picker dropdown populates from database successfully

## Git Commits

All changes committed in logical groups:
1. Type system enhancement
2. Database schemas
3. Dependencies
4. Individual module additions
5. Module reorganization by category
6. Color scheme updates
7. Frontend type colors
8. Cleanup of obsolete modules

Total: 15 commits ready to push
