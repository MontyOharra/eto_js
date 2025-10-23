"""
PDF Template Types
Dataclasses for template management, versioning, and wizard data
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal


# ========== Signature Object Dataclasses ==========

@dataclass(frozen=True)
class SignatureObject:
    """
    Single signature object selected from PDF for template matching.

    Includes object metadata and selection state. Type-specific fields
    are optional and populated based on object_type.
    """
    id: str  # Unique ID for referencing in extraction fields
    page: int
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    object_type: Literal[
        "text_word", "text_line",
        "graphic_rect", "graphic_line", "graphic_curve",
        "image", "table"
    ]
    is_selected: bool

    # Type-specific metadata (populated based on object_type)
    text: str | None = None  # For text_word
    fontname: str | None = None  # For text_word
    fontsize: float | None = None  # For text_word
    linewidth: float | None = None  # For graphic objects
    points: list[tuple[float, float]] | None = None  # For graphic_curve
    format: str | None = None  # For image (JPEG, PNG, etc.)
    colorspace: str | None = None  # For image (RGB, CMYK, etc.)
    bits: int | None = None  # For image (bit depth)
    rows: int | None = None  # For table
    cols: int | None = None  # For table


@dataclass(frozen=True)
class SignatureObjects:
    """
    Container for signature objects, grouped by type (keyed structure).

    BREAKING CHANGE: Previously stored as flat array, now keyed by type.
    This matches the PdfExtractedObjects structure and enables efficient
    type-based filtering and matching.
    """
    text_words: list[SignatureObject]
    text_lines: list[SignatureObject]
    graphic_rects: list[SignatureObject]
    graphic_lines: list[SignatureObject]
    graphic_curves: list[SignatureObject]
    images: list[SignatureObject]
    tables: list[SignatureObject]


@dataclass(frozen=True)
class ExtractionField:
    """
    Field definition for data extraction from PDF.

    References signature objects by ID and defines how to extract
    and validate the field value.
    """
    field_name: str
    field_type: Literal["string", "number", "date", "boolean"]
    object_ids: list[str]  # References SignatureObject.id values
    is_required: bool = False
    validation_pattern: str | None = None  # Regex pattern for validation
    default_value: str | None = None  # Default if extraction fails


# ========== Serialization Helpers ==========

def serialize_signature_objects(objects: SignatureObjects) -> dict:
    """
    Convert SignatureObjects dataclass to dict for JSON serialization.
    Used by repository before storing in database.
    """
    return asdict(objects)


def deserialize_signature_objects(objects_dict: dict) -> SignatureObjects:
    """
    Convert dict from JSON to SignatureObjects dataclass.
    Used by repository after loading from database.

    Validates structure and raises ValueError if invalid.
    """
    def deserialize_object(obj_dict: dict) -> SignatureObject:
        """Helper to deserialize individual signature object"""
        return SignatureObject(
            id=obj_dict["id"],
            page=obj_dict["page"],
            bbox=tuple(obj_dict["bbox"]),
            object_type=obj_dict["object_type"],
            is_selected=obj_dict["is_selected"],
            text=obj_dict.get("text"),
            fontname=obj_dict.get("fontname"),
            fontsize=obj_dict.get("fontsize"),
            linewidth=obj_dict.get("linewidth"),
            points=[tuple(pt) for pt in obj_dict["points"]] if obj_dict.get("points") else None,
            format=obj_dict.get("format"),
            colorspace=obj_dict.get("colorspace"),
            bits=obj_dict.get("bits"),
            rows=obj_dict.get("rows"),
            cols=obj_dict.get("cols")
        )

    return SignatureObjects(
        text_words=[deserialize_object(obj) for obj in objects_dict.get("text_words", [])],
        text_lines=[deserialize_object(obj) for obj in objects_dict.get("text_lines", [])],
        graphic_rects=[deserialize_object(obj) for obj in objects_dict.get("graphic_rects", [])],
        graphic_lines=[deserialize_object(obj) for obj in objects_dict.get("graphic_lines", [])],
        graphic_curves=[deserialize_object(obj) for obj in objects_dict.get("graphic_curves", [])],
        images=[deserialize_object(obj) for obj in objects_dict.get("images", [])],
        tables=[deserialize_object(obj) for obj in objects_dict.get("tables", [])]
    )


def serialize_extraction_fields(fields: list[ExtractionField]) -> str:
    """
    Convert extraction fields list to JSON string for database storage.
    """
    if not fields:
        return "[]"

    return json.dumps([asdict(field) for field in fields])


def deserialize_extraction_fields(fields_json: str | None) -> list[ExtractionField]:
    """
    Convert JSON string from database to extraction fields list.
    """
    if not fields_json:
        return []

    fields_list = json.loads(fields_json)
    return [
        ExtractionField(
            field_name=field["field_name"],
            field_type=field["field_type"],
            object_ids=field["object_ids"],
            is_required=field.get("is_required", False),
            validation_pattern=field.get("validation_pattern"),
            default_value=field.get("default_value")
        )
        for field in fields_list
    ]


# ========== Template Version Dataclasses ==========

@dataclass(frozen=True)
class TemplateVersion:
    """
    Immutable version snapshot of template wizard data.

    Stores complete wizard configuration (signature objects, extraction fields,
    pipeline reference) at a specific point in time. Once created, versions
    never change.
    """
    id: int
    template_id: int
    version_number: int
    source_pdf_id: int
    signature_objects: SignatureObjects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int | None
    created_at: datetime


@dataclass(frozen=True)
class VersionCreate:
    """
    Data needed to create new template version.
    Used by create_template and update_template service methods.
    """
    template_id: int
    version_number: int
    source_pdf_id: int
    signature_objects: SignatureObjects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int | None


@dataclass(frozen=True)
class VersionSummary:
    """
    Lightweight version info for history/list views.
    Used by list_versions service method.
    """
    id: int
    version_number: int
    created_at: datetime
    is_current: bool


# ========== Template Metadata Dataclasses ==========

@dataclass(frozen=True)
class TemplateMetadata:
    """
    Complete template metadata (database record).

    Points to current version via current_version_id. Template status
    controls whether template is used for ETO matching.
    """
    id: int
    name: str
    description: str | None
    status: Literal["active", "inactive", "draft"]
    current_version_id: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TemplateSummary:
    """
    Lightweight template info for list views.
    Used by list_templates service method.
    """
    id: int
    name: str
    status: Literal["active", "inactive", "draft"]
    version_count: int
    current_version_number: int | None
    updated_at: datetime


@dataclass(frozen=True)
class TemplateWithVersion:
    """
    Template metadata combined with current version data.
    Used by get_template service method.
    """
    template: TemplateMetadata
    current_version: TemplateVersion | None


# ========== Template CRUD Dataclasses ==========

@dataclass(frozen=True)
class TemplateCreate:
    """
    Data needed to create new template + initial version.

    Used by create_template service method. Creates both template
    record and version 1 atomically.
    """
    name: str
    description: str | None
    signature_objects: SignatureObjects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int | None
    source_pdf_id: int


@dataclass(frozen=True)
class TemplateUpdate:
    """
    Partial update data for templates.

    All fields optional to support partial updates.

    SMART UPDATE LOGIC:
    - If only name/description change: update metadata only (no new version)
    - If signature_objects, extraction_fields, or pipeline_definition_id change:
      create new version and update current_version_id
    - Status changes handled by separate activate/deactivate methods
    """
    name: str | None = None
    description: str | None = None
    signature_objects: SignatureObjects | None = None
    extraction_fields: list[ExtractionField] | None = None
    pipeline_definition_id: int | None = None


@dataclass(frozen=True)
class TemplateMetadataUpdate:
    """
    Metadata-only update (no version change).

    Used internally when update_template determines only metadata changed.
    """
    name: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class TemplateStatusUpdate:
    """
    Status update data.

    Used by activate_template and deactivate_template service methods.
    """
    status: Literal["active", "inactive", "draft"]
    activated_at: datetime | None = None
