# PDF Objects Full Typing - Change Analysis

## Executive Summary

**Current State**: PDF `extracted_objects` uses generic `dict` type at service/repository layers, with Pydantic models defined but unused at API layer.

**Desired State**: Strongly-typed dataclasses throughout entire stack (types → repository → service → API).

**Impact**: Changes required across 4 layers and affects PDF templates signature objects.

---

## 1. Current Architecture

### Layer 1: Types (Dataclasses)
**File**: `server-new/src/shared/types/pdf_files.py`

```python
@dataclass(frozen=True)
class PdfMetadata:
    # ... other fields
    extracted_objects: dict  # ← GENERIC DICT
```

**Problem**: No type safety at service/repository level.

### Layer 2: Repository
**File**: `server-new/src/shared/database/repositories/pdf.py`

```python
def _model_to_dataclass(self, model: PdfFileModel) -> PdfMetadata:
    # Parse JSON to dict
    extracted_objects = {}
    if model.objects_json:
        try:
            extracted_objects = json.loads(model.objects_json)  # ← DICT
        except json.JSONDecodeError:
            extracted_objects = {
                "text_words": [],
                "text_lines": [],
                # ... default empty arrays
            }

    return PdfMetadata(
        # ... fields
        extracted_objects=extracted_objects  # ← DICT
    )
```

**Problem**: JSON serialization/deserialization handles raw dicts, no validation.

### Layer 3: Service
**File**: `server-new/src/features/pdf_files/service.py` (per design doc)

```python
def _extract_objects_from_file(self, file_path: Path, filename: str) -> dict:
    objects = {
        "text_words": [],  # List of dicts
        "text_lines": [],  # List of dicts
        # ... etc
    }

    # Extract and append dicts
    for word in words:
        objects["text_words"].append({
            "page": page_num,
            "bbox": [x0, y0, x1, y1],
            "text": word['text'],
            # ...
        })

    return objects  # ← DICT OF LISTS OF DICTS
```

**Problem**: No type safety during extraction, can create invalid object structures.

### Layer 4: API
**File**: `server-new/src/api/routers/pdf_files.py`

```python
@router.get("/{id}/objects")
async def get_pdf_objects(...) -> dict:  # ← RETURNS DICT, NOT TYPED MODEL
    objects_dict = pdf_service.get_pdf_objects(id, object_type)

    return {
        "pdf_file_id": id,
        "page_count": metadata.page_count or 0,
        "objects": objects_dict  # ← DICT
    }
```

**File**: `server-new/src/api/schemas/pdf_files.py`

```python
# THESE MODELS ARE DEFINED BUT NEVER USED:
class TextWordObject(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]
    text: str
    fontname: str
    fontsize: float

class PdfObjects(BaseModel):
    text_words: List[TextWordObject]
    # ... etc

class GetPdfObjectsResponse(BaseModel):
    pdf_file_id: int
    page_count: int
    objects: PdfObjects  # ← TYPED BUT NEVER USED
```

**Problem**: Pydantic schemas exist but router returns raw dict, bypassing validation.

---

## 2. Target Architecture - Full Typing

### New Type Hierarchy

```
PdfExtractedObjects (dataclass container)
├── text_words: list[TextWord]
├── text_lines: list[TextLine]
├── graphic_rects: list[GraphicRect]
├── graphic_lines: list[GraphicLine]
├── graphic_curves: list[GraphicCurve]
├── images: list[Image]
└── tables: list[Table]
```

### Flow with Typing

```
1. Service extracts → Creates typed dataclasses
2. Repository serializes → JSON.dumps via custom serialization
3. Repository deserializes → JSON.loads + validation into dataclasses
4. Service returns → Typed PdfExtractedObjects
5. API converts → Pydantic models (easy 1:1 mapping)
```

---

## 3. Required Changes

### 3.1 Types Layer - NEW Dataclasses

**File**: `server-new/src/shared/types/pdf_files.py`

**Add 7 Object Type Dataclasses**:

```python
@dataclass(frozen=True)
class TextWord:
    """Single text word extracted from PDF"""
    page: int
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    text: str
    fontname: str
    fontsize: float

@dataclass(frozen=True)
class TextLine:
    """Single text line boundary"""
    page: int
    bbox: tuple[float, float, float, float]

@dataclass(frozen=True)
class GraphicRect:
    """Rectangle graphic object"""
    page: int
    bbox: tuple[float, float, float, float]
    linewidth: float

@dataclass(frozen=True)
class GraphicLine:
    """Line graphic object"""
    page: int
    bbox: tuple[float, float, float, float]
    linewidth: float

@dataclass(frozen=True)
class GraphicCurve:
    """Curve graphic object with control points"""
    page: int
    bbox: tuple[float, float, float, float]
    points: list[tuple[float, float]]  # Array of (x, y) coordinate pairs
    linewidth: float

@dataclass(frozen=True)
class Image:
    """Image object with metadata"""
    page: int
    bbox: tuple[float, float, float, float]
    format: str  # e.g., "JPEG", "PNG"
    colorspace: str  # e.g., "RGB", "CMYK"
    bits: int  # Bit depth

@dataclass(frozen=True)
class Table:
    """Table structure with dimensions"""
    page: int
    bbox: tuple[float, float, float, float]
    rows: int
    cols: int
```

**Add Container Dataclass**:

```python
@dataclass(frozen=True)
class PdfExtractedObjects:
    """
    Container for all extracted PDF objects, grouped by type.
    Replaces raw dict with strongly-typed structure.
    """
    text_words: list[TextWord]
    text_lines: list[TextLine]
    graphic_rects: list[GraphicRect]
    graphic_lines: list[GraphicLine]
    graphic_curves: list[GraphicCurve]
    images: list[Image]
    tables: list[Table]
```

**Update Existing Dataclasses**:

```python
@dataclass(frozen=True)
class PdfMetadata:
    # ... other fields
    extracted_objects: PdfExtractedObjects  # ← CHANGED FROM dict
    # ... other fields

@dataclass(frozen=True)
class PdfCreate:
    # ... other fields
    extracted_objects: PdfExtractedObjects  # ← CHANGED FROM dict
    # ... other fields
```

**Add Serialization Helpers**:

```python
def serialize_extracted_objects(objects: PdfExtractedObjects) -> dict:
    """
    Convert PdfExtractedObjects dataclass to dict for JSON serialization.
    Used by repository before storing in database.
    """
    from dataclasses import asdict
    return asdict(objects)

def deserialize_extracted_objects(objects_dict: dict) -> PdfExtractedObjects:
    """
    Convert dict from JSON to PdfExtractedObjects dataclass.
    Used by repository after loading from database.

    Validates structure and raises ValueError if invalid.
    """
    return PdfExtractedObjects(
        text_words=[
            TextWord(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                text=obj["text"],
                fontname=obj["fontname"],
                fontsize=obj["fontsize"]
            )
            for obj in objects_dict.get("text_words", [])
        ],
        text_lines=[
            TextLine(
                page=obj["page"],
                bbox=tuple(obj["bbox"])
            )
            for obj in objects_dict.get("text_lines", [])
        ],
        graphic_rects=[
            GraphicRect(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                linewidth=obj["linewidth"]
            )
            for obj in objects_dict.get("graphic_rects", [])
        ],
        graphic_lines=[
            GraphicLine(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                linewidth=obj["linewidth"]
            )
            for obj in objects_dict.get("graphic_lines", [])
        ],
        graphic_curves=[
            GraphicCurve(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                points=[tuple(pt) for pt in obj["points"]],
                linewidth=obj["linewidth"]
            )
            for obj in objects_dict.get("graphic_curves", [])
        ],
        images=[
            Image(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                format=obj["format"],
                colorspace=obj["colorspace"],
                bits=obj["bits"]
            )
            for obj in objects_dict.get("images", [])
        ],
        tables=[
            Table(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                rows=obj["rows"],
                cols=obj["cols"]
            )
            for obj in objects_dict.get("tables", [])
        ]
    )
```

---

### 3.2 Repository Layer Changes

**File**: `server-new/src/shared/database/repositories/pdf.py`

**Change 1: Update imports**

```python
from shared.types.pdf_files import (
    PdfMetadata,
    PdfCreate,
    PdfExtractedObjects,  # NEW
    serialize_extracted_objects,  # NEW
    deserialize_extracted_objects  # NEW
)
```

**Change 2: Update `_model_to_dataclass` method**

```python
def _model_to_dataclass(self, model: PdfFileModel) -> PdfMetadata:
    """Convert ORM model to PdfMetadata dataclass"""

    # Parse objects_json to dict
    if model.objects_json:
        try:
            objects_dict = json.loads(model.objects_json)
            # NEW: Deserialize dict to typed dataclasses
            extracted_objects = deserialize_extracted_objects(objects_dict)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Invalid JSON in objects_json for PDF {model.id}: {e}")
            # Return empty typed structure
            extracted_objects = PdfExtractedObjects(
                text_words=[],
                text_lines=[],
                graphic_rects=[],
                graphic_lines=[],
                graphic_curves=[],
                images=[],
                tables=[]
            )
    else:
        # No objects extracted
        extracted_objects = PdfExtractedObjects(
            text_words=[],
            text_lines=[],
            graphic_rects=[],
            graphic_lines=[],
            graphic_curves=[],
            images=[],
            tables=[]
        )

    return PdfMetadata(
        id=model.id,
        email_id=model.email_id,
        original_filename=model.original_filename,
        file_hash=model.file_hash or "",
        file_size_bytes=model.file_size or 0,
        file_path=model.relative_path,
        page_count=model.page_count,
        stored_at=model.created_at,
        extracted_objects=extracted_objects,  # ← NOW TYPED
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
```

**Change 3: Update `create` method**

```python
def create(self, pdf_data: PdfCreate) -> PdfMetadata:
    """Create new PDF record."""
    with self._get_session() as session:
        # NEW: Serialize typed dataclass to dict, then to JSON
        objects_dict = serialize_extracted_objects(pdf_data.extracted_objects)
        objects_json = json.dumps(objects_dict)

        # Create ORM model
        model = self.model_class(
            email_id=pdf_data.email_id,
            filename=pdf_data.original_filename,
            original_filename=pdf_data.original_filename,
            file_hash=pdf_data.file_hash,
            file_size=pdf_data.file_size_bytes,
            relative_path=pdf_data.file_path,
            page_count=pdf_data.page_count,
            objects_json=objects_json,  # ← Serialized from typed objects
        )

        session.add(model)
        session.flush()

        return self._model_to_dataclass(model)
```

---

### 3.3 Service Layer Changes

**File**: `server-new/src/features/pdf_files/service.py` (per design doc)

**Change 1: Update imports**

```python
from shared.types.pdf_files import (
    PdfMetadata,
    PdfCreate,
    PdfExtractedObjects,  # NEW
    TextWord,  # NEW
    TextLine,  # NEW
    GraphicRect,  # NEW
    GraphicLine,  # NEW
    GraphicCurve,  # NEW
    Image,  # NEW
    Table,  # NEW
)
```

**Change 2: Update `_extract_objects_from_file` return type and implementation**

```python
def _extract_objects_from_file(
    self,
    file_path: Path,
    filename: str
) -> PdfExtractedObjects:  # ← CHANGED FROM dict
    """
    Extract objects from PDF file using pdfplumber.

    Returns PdfExtractedObjects dataclass with typed objects.
    """
    import pdfplumber

    # Initialize lists for typed objects
    text_words: list[TextWord] = []
    text_lines: list[TextLine] = []
    graphic_rects: list[GraphicRect] = []
    graphic_lines: list[GraphicLine] = []
    graphic_curves: list[GraphicCurve] = []
    images: list[Image] = []
    tables: list[Table] = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_num = page.page_number - 1  # 0-indexed

                # Extract text words → TextWord dataclasses
                words = page.extract_words()
                for word in words:
                    text_words.append(TextWord(
                        page=page_num,
                        bbox=(word['x0'], word['top'], word['x1'], word['bottom']),
                        text=word['text'],
                        fontname=word.get('fontname', ''),
                        fontsize=word.get('size', 0.0)
                    ))

                # Extract lines → TextLine dataclasses
                lines = page.lines
                for line in lines:
                    text_lines.append(TextLine(
                        page=page_num,
                        bbox=(line['x0'], line['top'], line['x1'], line['bottom'])
                    ))

                # Extract rectangles → GraphicRect dataclasses
                rects = page.rects
                for rect in rects:
                    graphic_rects.append(GraphicRect(
                        page=page_num,
                        bbox=(rect['x0'], rect['top'], rect['x1'], rect['bottom']),
                        linewidth=rect.get('linewidth', 1.0)
                    ))

                # Extract lines → GraphicLine dataclasses
                # (Note: pdfplumber differentiates between text lines and graphic lines)
                # This section would extract graphic lines if available

                # Extract curves → GraphicCurve dataclasses
                curves = page.curves
                for curve in curves:
                    graphic_curves.append(GraphicCurve(
                        page=page_num,
                        bbox=(curve['x0'], curve['top'], curve['x1'], curve['bottom']),
                        points=[tuple(pt) for pt in curve.get('points', [])],
                        linewidth=curve.get('linewidth', 1.0)
                    ))

                # Extract images → Image dataclasses
                imgs = page.images
                for img in imgs:
                    images.append(Image(
                        page=page_num,
                        bbox=(img['x0'], img['top'], img['x1'], img['bottom']),
                        format=img.get('name', '').split('.')[-1].upper(),
                        colorspace=img.get('colorspace', ''),
                        bits=img.get('bits', 0)
                    ))

                # Extract tables → Table dataclasses
                tables_found = page.find_tables()
                for table in tables_found:
                    table_data = table.extract()
                    tables.append(Table(
                        page=page_num,
                        bbox=tuple(table.bbox),
                        rows=len(table_data),
                        cols=len(table_data[0]) if table_data else 0
                    ))

        total_objects = (
            len(text_words) + len(text_lines) + len(graphic_rects) +
            len(graphic_lines) + len(graphic_curves) + len(images) + len(tables)
        )
        logger.debug(
            f"Extracted {total_objects} objects from {filename} "
            f"({len(pdf.pages)} pages)"
        )

        # Return typed container
        return PdfExtractedObjects(
            text_words=text_words,
            text_lines=text_lines,
            graphic_rects=graphic_rects,
            graphic_lines=graphic_lines,
            graphic_curves=graphic_curves,
            images=images,
            tables=tables
        )

    except Exception as e:
        logger.error(f"Error extracting objects from {filename}: {e}", exc_info=True)
        raise ServiceError(f"Failed to extract objects: {str(e)}")
```

**Change 3: Update `store_pdf` method**

```python
def store_pdf(
    self,
    file_bytes: bytes,
    filename: str,
    email_id: int | None = None
) -> PdfMetadata:
    """
    Store PDF file and extract objects.
    Returns PdfMetadata with typed extracted_objects.
    """
    # ... deduplication logic unchanged

    # Extract objects (now returns PdfExtractedObjects dataclass)
    extracted_objects = self._extract_objects_from_file(full_path, filename)

    # Create database record
    pdf_create = PdfCreate(
        original_filename=filename,
        file_hash=file_hash,
        file_size_bytes=len(file_bytes),
        file_path=str(relative_path),
        email_id=email_id,
        stored_at=now,
        extracted_objects=extracted_objects  # ← TYPED
    )

    pdf_metadata = self.pdf_repository.create(pdf_create)

    return pdf_metadata
```

**Change 4: Update `extract_objects_from_bytes` method**

```python
def extract_objects_from_bytes(
    self,
    file_bytes: bytes,
    filename: str
) -> PdfExtractedObjects:  # ← CHANGED FROM dict
    """
    Extract objects from PDF bytes (no database persistence).
    Returns typed PdfExtractedObjects dataclass.
    """
    # ... save to temp file

    # Extract and return typed objects
    extracted_objects = self._extract_objects_from_file(temp_path, filename)

    return extracted_objects
```

**Change 5: Update `get_pdf_objects` method**

```python
def get_pdf_objects(
    self,
    pdf_id: int,
    object_type: str | None = None
) -> PdfExtractedObjects:  # ← CHANGED FROM dict
    """
    Get extracted PDF objects (typed).

    Args:
        pdf_id: PDF file ID
        object_type: Optional filter (not implemented - would require filtering logic)

    Returns:
        PdfExtractedObjects dataclass with typed objects
    """
    metadata = self.get_pdf_metadata(pdf_id)

    # If object_type filter requested, would need to create new PdfExtractedObjects
    # with only the specified type populated. For now, return all objects.

    return metadata.extracted_objects  # ← TYPED
```

---

### 3.4 API Layer Changes

**File**: `server-new/src/api/routers/pdf_files.py`

**Change 1: Update `get_pdf_objects` endpoint**

```python
from api.schemas.pdf_files import (
    GetPdfMetadataResponse,
    GetPdfObjectsResponse,  # ← ALREADY IMPORTED, NOW USE IT
    ProcessPdfObjectsResponse,  # ← ALREADY IMPORTED, NOW USE IT
    PdfObjects,  # NEW
    TextWordObject,  # NEW (for conversion)
    TextLineObject,  # NEW
    GraphicRectObject,  # NEW
    GraphicLineObject,  # NEW
    GraphicCurveObject,  # NEW
    ImageObject,  # NEW
    TableObject,  # NEW
)

@router.get("/{id}/objects", response_model=GetPdfObjectsResponse)  # ← USE TYPED RESPONSE
async def get_pdf_objects(
    id: int,
    object_type: str | None = None,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> GetPdfObjectsResponse:  # ← CHANGED FROM dict
    """Get extracted PDF objects for template building"""

    try:
        # Get typed objects from service
        objects = pdf_service.get_pdf_objects(id, object_type)

        # Get metadata for page count
        metadata = pdf_service.get_pdf_metadata(id)

        # Convert dataclasses to Pydantic models
        pydantic_objects = PdfObjects(
            text_words=[
                TextWordObject(
                    page=obj.page,
                    bbox=obj.bbox,
                    text=obj.text,
                    fontname=obj.fontname,
                    fontsize=obj.fontsize
                )
                for obj in objects.text_words
            ],
            text_lines=[
                TextLineObject(
                    page=obj.page,
                    bbox=obj.bbox
                )
                for obj in objects.text_lines
            ],
            graphic_rects=[
                GraphicRectObject(
                    page=obj.page,
                    bbox=obj.bbox,
                    linewidth=obj.linewidth
                )
                for obj in objects.graphic_rects
            ],
            graphic_lines=[
                GraphicLineObject(
                    page=obj.page,
                    bbox=obj.bbox,
                    linewidth=obj.linewidth
                )
                for obj in objects.graphic_lines
            ],
            graphic_curves=[
                GraphicCurveObject(
                    page=obj.page,
                    bbox=obj.bbox,
                    points=list(obj.points),
                    linewidth=obj.linewidth
                )
                for obj in objects.graphic_curves
            ],
            images=[
                ImageObject(
                    page=obj.page,
                    bbox=obj.bbox,
                    format=obj.format,
                    colorspace=obj.colorspace,
                    bits=obj.bits
                )
                for obj in objects.images
            ],
            tables=[
                TableObject(
                    page=obj.page,
                    bbox=obj.bbox,
                    rows=obj.rows,
                    cols=obj.cols
                )
                for obj in objects.tables
            ]
        )

        return GetPdfObjectsResponse(
            pdf_file_id=id,
            page_count=metadata.page_count or 0,
            objects=pydantic_objects
        )

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF file {id} not found"
        )

    except Exception as e:
        logger.error(f"Error retrieving PDF objects for {id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PDF objects"
        )
```

**Change 2: Update `process_pdf_objects` endpoint**

```python
@router.post("/process-objects", response_model=ProcessPdfObjectsResponse)  # ← USE TYPED RESPONSE
async def process_pdf_objects(
    pdf_file: UploadFile = File(...),
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> ProcessPdfObjectsResponse:  # ← CHANGED FROM dict
    """Process uploaded PDF and extract objects (no persistence)"""

    try:
        # Validate file upload
        if not pdf_file or not pdf_file.filename or not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing PDF file or invalid file type"
            )

        # Read file bytes
        pdf_bytes = await pdf_file.read()

        # Extract objects (now returns PdfExtractedObjects dataclass)
        objects = pdf_service.extract_objects_from_bytes(
            pdf_bytes,
            pdf_file.filename or "uploaded.pdf"
        )

        # Calculate page count from objects
        page_count = 0
        for obj_list in [
            objects.text_words, objects.text_lines, objects.graphic_rects,
            objects.graphic_lines, objects.graphic_curves, objects.images, objects.tables
        ]:
            for obj in obj_list:
                page_count = max(page_count, obj.page + 1)

        # Convert dataclasses to Pydantic models (same conversion as above)
        pydantic_objects = PdfObjects(
            text_words=[
                TextWordObject(
                    page=obj.page,
                    bbox=obj.bbox,
                    text=obj.text,
                    fontname=obj.fontname,
                    fontsize=obj.fontsize
                )
                for obj in objects.text_words
            ],
            text_lines=[
                TextLineObject(page=obj.page, bbox=obj.bbox)
                for obj in objects.text_lines
            ],
            graphic_rects=[
                GraphicRectObject(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
                for obj in objects.graphic_rects
            ],
            graphic_lines=[
                GraphicLineObject(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
                for obj in objects.graphic_lines
            ],
            graphic_curves=[
                GraphicCurveObject(
                    page=obj.page, bbox=obj.bbox,
                    points=list(obj.points), linewidth=obj.linewidth
                )
                for obj in objects.graphic_curves
            ],
            images=[
                ImageObject(
                    page=obj.page, bbox=obj.bbox,
                    format=obj.format, colorspace=obj.colorspace, bits=obj.bits
                )
                for obj in objects.images
            ],
            tables=[
                TableObject(page=obj.page, bbox=obj.bbox, rows=obj.rows, cols=obj.cols)
                for obj in objects.tables
            ]
        )

        return ProcessPdfObjectsResponse(
            page_count=page_count,
            objects=pydantic_objects
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Error processing PDF {pdf_file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process PDF file"
        )
```

**Optional: Add conversion helper function to reduce duplication**

```python
def _convert_to_pydantic_objects(objects: PdfExtractedObjects) -> PdfObjects:
    """Convert dataclass PdfExtractedObjects to Pydantic PdfObjects"""
    return PdfObjects(
        text_words=[
            TextWordObject(
                page=obj.page,
                bbox=obj.bbox,
                text=obj.text,
                fontname=obj.fontname,
                fontsize=obj.fontsize
            )
            for obj in objects.text_words
        ],
        text_lines=[
            TextLineObject(page=obj.page, bbox=obj.bbox)
            for obj in objects.text_lines
        ],
        graphic_rects=[
            GraphicRectObject(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects.graphic_rects
        ],
        graphic_lines=[
            GraphicLineObject(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects.graphic_lines
        ],
        graphic_curves=[
            GraphicCurveObject(
                page=obj.page, bbox=obj.bbox,
                points=list(obj.points), linewidth=obj.linewidth
            )
            for obj in objects.graphic_curves
        ],
        images=[
            ImageObject(
                page=obj.page, bbox=obj.bbox,
                format=obj.format, colorspace=obj.colorspace, bits=obj.bits
            )
            for obj in objects.images
        ],
        tables=[
            TableObject(page=obj.page, bbox=obj.bbox, rows=obj.rows, cols=obj.cols)
            for obj in objects.tables
        ]
    )

# Then use in both endpoints:
pydantic_objects = _convert_to_pydantic_objects(objects)
```

---

## 4. Impact on PDF Templates

### 4.1 Template Signature Objects - BREAKING CHANGE

**Context**: PDF templates store `signature_objects` as JSON in database. These are selected PDF objects used for template matching.

**Current Structure** (flat array with discriminator):
```typescript
signature_objects: [
  {
    "object_type": "text_word" | "text_line" | "graphic_rect" | ...,
    "page": number,
    "bbox": [number, number, number, number],
    // Type-specific fields based on object_type discriminator
    "text"?: string,
    "fontname"?: string,
    // ... etc
  }
]
```

**New Structure** (keyed lists matching PdfExtractedObjects):
```typescript
signature_objects: {
  "text_words": [
    {
      "page": number,
      "bbox": [number, number, number, number],
      "text": string,
      "fontname": string,
      "fontsize": number
    }
  ],
  "text_lines": [
    {
      "page": number,
      "bbox": [number, number, number, number]
    }
  ],
  "graphic_rects": [...],
  "graphic_lines": [...],
  "graphic_curves": [...],
  "images": [...],
  "tables": [...]
}
```

**Why This Change is Needed**:
1. **Consistency**: Signature objects should match the structure of extracted objects
2. **Type Safety**: Can reuse PdfExtractedObjects dataclass (or create TemplateSignatureObjects alias)
3. **Simpler Logic**: No need for object_type discriminator field
4. **Better Organization**: Objects grouped by type, easier to process

### 4.2 Required Template Changes

**Types Layer** (`shared/types/pdf_templates.py`):
```python
from shared.types.pdf_files import PdfExtractedObjects

@dataclass(frozen=True)
class PdfTemplateVersion:
    # ... other fields
    signature_objects: PdfExtractedObjects  # ← CHANGED FROM dict or custom type
    # ... other fields
```

**Repository Layer** (`shared/database/repositories/pdf_template_version.py`):
```python
from shared.types.pdf_files import serialize_extracted_objects, deserialize_extracted_objects

def _model_to_dataclass(self, model: PdfTemplateVersionModel) -> PdfTemplateVersion:
    # Deserialize signature_objects JSON to typed dataclass
    if model.signature_objects_json:
        try:
            sig_obj_dict = json.loads(model.signature_objects_json)
            signature_objects = deserialize_extracted_objects(sig_obj_dict)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Invalid signature_objects for template version {model.id}: {e}")
            # Return empty structure
            signature_objects = PdfExtractedObjects(
                text_words=[], text_lines=[], graphic_rects=[],
                graphic_lines=[], graphic_curves=[], images=[], tables=[]
            )
    else:
        signature_objects = PdfExtractedObjects(
            text_words=[], text_lines=[], graphic_rects=[],
            graphic_lines=[], graphic_curves=[], images=[], tables=[]
        )

    return PdfTemplateVersion(
        # ... fields
        signature_objects=signature_objects,  # ← TYPED
        # ... fields
    )

def create(self, version_data: PdfTemplateVersionCreate) -> PdfTemplateVersion:
    # Serialize typed signature_objects to JSON
    sig_obj_dict = serialize_extracted_objects(version_data.signature_objects)
    signature_objects_json = json.dumps(sig_obj_dict)

    model = self.model_class(
        # ... fields
        signature_objects_json=signature_objects_json,  # ← SERIALIZED
        # ... fields
    )
    # ... rest of method
```

**API Layer** (`api/routers/pdf_templates.py`, `api/schemas/pdf_templates.py`):
```python
# Schemas - use same Pydantic objects as PDF files
from api.schemas.pdf_files import PdfObjects  # Reuse!

class PdfTemplateVersionDetail(BaseModel):
    # ... fields
    signature_objects: PdfObjects  # ← CHANGED FROM custom discriminated union
    # ... fields

# Router - convert dataclass to Pydantic
from api.routers.pdf_files import _convert_to_pydantic_objects  # Reuse helper!

@router.get("/{id}/versions/{version_number}")
async def get_template_version(...):
    version = template_service.get_version(id, version_number)

    return PdfTemplateVersionDetail(
        # ... fields
        signature_objects=_convert_to_pydantic_objects(version.signature_objects),
        # ... fields
    )
```

**Frontend Impact**:
```typescript
// OLD: Flat array iteration
template.signature_objects.forEach(obj => {
  if (obj.object_type === 'text_word') {
    // Handle text word
  } else if (obj.object_type === 'graphic_rect') {
    // Handle rect
  }
  // ... etc
});

// NEW: Keyed structure iteration
template.signature_objects.text_words.forEach(word => {
  // Handle text word - no type checking needed
});
template.signature_objects.graphic_rects.forEach(rect => {
  // Handle rect - no type checking needed
});
```

### 4.3 Migration Strategy for Templates

**Database Migration Required**:
1. **Read existing signature_objects** (flat array format)
2. **Convert to keyed structure**:
   ```python
   def migrate_signature_objects(old_array: list) -> dict:
       new_structure = {
           "text_words": [], "text_lines": [], "graphic_rects": [],
           "graphic_lines": [], "graphic_curves": [], "images": [], "tables": []
       }
       for obj in old_array:
           obj_type = obj.pop("object_type")  # Remove discriminator
           if obj_type == "text_word":
               new_structure["text_words"].append(obj)
           elif obj_type == "text_line":
               new_structure["text_lines"].append(obj)
           # ... etc for all types
       return new_structure
   ```
3. **Write back to database** in new format

**Breaking Change**: Existing templates need migration before new code can read them

---

## 5. Benefits of Full Typing

### 5.1 Type Safety
- **Compile-time validation**: Catch errors during development, not runtime
- **IDE autocomplete**: Full IntelliSense for object properties
- **Refactoring safety**: Changes propagate through type system

### 5.2 Data Validation
- **Structure enforcement**: Can't create invalid objects (missing required fields)
- **Type checking**: Ensures `page` is int, `bbox` is 4-tuple, etc.
- **Immutability**: `frozen=True` prevents accidental modification

### 5.3 Code Clarity
- **Self-documenting**: Types clearly show what each object contains
- **Reduced bugs**: No more `KeyError` from misspelled dict keys
- **Better testing**: Easier to create test fixtures with typed objects

### 5.4 Consistency
- **Single source of truth**: One set of dataclasses used everywhere
- **API alignment**: Pydantic schemas map 1:1 to dataclasses
- **Validation at boundaries**: Repository validates on deserialization

---

## 6. Migration Considerations

### 6.1 Database Compatibility
**No database migration needed**: JSON storage format remains unchanged.
- Serialization produces same dict structure
- Existing records deserialize without issues
- Forward and backward compatible

### 6.2 Testing Requirements
**New tests needed**:
1. **Serialization/deserialization tests** (types layer)
   - Test `serialize_extracted_objects()` produces correct dict
   - Test `deserialize_extracted_objects()` handles all object types
   - Test error handling for malformed JSON

2. **Repository tests** (repository layer)
   - Test `_model_to_dataclass()` returns typed objects
   - Test `create()` serializes typed objects correctly
   - Test error handling for corrupt database JSON

3. **Service tests** (service layer)
   - Test `_extract_objects_from_file()` returns typed objects
   - Test all object types are extracted correctly
   - Mock pdfplumber responses

4. **API tests** (API layer)
   - Test endpoints return typed Pydantic responses
   - Test conversion from dataclasses to Pydantic
   - Validate response JSON structure

### 6.3 Rollout Strategy
**Recommended order**:
1. ✅ Create new dataclasses in types layer
2. ✅ Add serialization/deserialization helpers
3. ✅ Update repository layer (read first, then write)
4. ✅ Update service layer (extraction methods)
5. ✅ Update API layer (endpoints and conversion)
6. ✅ Add comprehensive tests
7. ✅ Integration testing with template builder

**Risk mitigation**:
- Add error handling for deserialization failures (fallback to empty objects)
- Log warnings for invalid object structures
- Monitor for deserialization errors in production

---

## 7. Summary of Files Changed

### 7.1 PDF Files Domain

| File | Lines Changed | Complexity |
|------|--------------|------------|
| `shared/types/pdf_files.py` | +250 | Medium (new dataclasses + helpers) |
| `shared/database/repositories/pdf.py` | +30 | Low (use helpers) |
| `features/pdf_files/service.py` | +100 | Medium (extraction logic) |
| `api/routers/pdf_files.py` | +80 | Medium (conversion logic) |
| `api/schemas/pdf_files.py` | 0 | None (already correct) |
| **Subtotal** | **~460 lines** | **Medium** |

### 7.2 PDF Templates Domain (Signature Objects)

| File | Lines Changed | Complexity |
|------|--------------|------------|
| `shared/types/pdf_templates.py` | +20 | Low (change signature_objects type) |
| `shared/database/repositories/pdf_template_version.py` | +40 | Medium (reuse serialization helpers) |
| `api/schemas/pdf_templates.py` | +10 | Low (reuse PdfObjects) |
| `api/routers/pdf_templates.py` | +20 | Low (reuse conversion helper) |
| `features/pdf_templates/service.py` | +10 | Low (pass-through changes) |
| **Database Migration Script** | +50 | Medium (convert array to keyed structure) |
| **Subtotal** | **~150 lines** | **Medium** |

### 7.3 Total Impact

| **Grand Total** | **~610 lines** | **Medium** |

---

## 8. Next Steps

### Phase 1: PDF Files Domain
1. **Approve Architecture**: Confirm this design meets requirements
2. **Implement Types Layer**: Create all dataclasses and helpers (foundation)
3. **Update PDF Repository**: Modify serialization/deserialization
4. **Update PDF Service**: Modify extraction to return typed objects
5. **Update PDF API Router**: Use typed responses instead of dicts
6. **Add PDF Tests**: Comprehensive testing at all layers

### Phase 2: PDF Templates Domain
7. **Create Migration Script**: Convert existing template signature_objects from array to keyed structure
8. **Run Migration**: Backup database, run migration, verify all templates converted
9. **Update Template Types**: Change signature_objects field to use PdfExtractedObjects
10. **Update Template Repository**: Reuse serialization helpers from pdf_files
11. **Update Template API**: Reuse PdfObjects schema and conversion helpers
12. **Update Template Service**: Pass-through changes for typed objects
13. **Add Template Tests**: Test serialization/deserialization of signature objects

### Phase 3: Integration
14. **Frontend Updates**: Update template builder to work with keyed structure
15. **Integration Testing**: Test complete workflow from PDF upload → template creation → matching
16. **Validation**: Ensure template matching still works correctly with new structure

---

**End of Analysis**
