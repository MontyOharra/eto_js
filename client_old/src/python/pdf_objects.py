import pdfplumber
from pathlib import Path
from typing import List, Dict, Any, Optional
import io
import os
import sys
import json
import base64
import binascii
from urllib.parse import urlparse, unquote


def _round(val, ndigits=3):
    return round(val, ndigits) if isinstance(val, float) else val


def extract_pdf_objects_from_bytes(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts all objects (words, lines, tables, rectangles, curves, etc.) from a PDF bytes object.
    Returns a list of serializable dicts, suitable for JSON serialization and frontend use.
    All coordinates, widths, and heights are rounded to 3 decimals.
    """
    objects = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_height = page.height
            # --- Words ---
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            for i, word in enumerate(words):
                x0 = word.get("x0")
                x1 = word.get("x1")
                if "y0" in word and "y1" in word:
                    y0 = word["y0"]
                    y1 = word["y1"]
                elif "top" in word and "bottom" in word:
                    y0 = page_height - word["bottom"]
                    y1 = page_height - word["top"]
                else:
                    y0 = y1 = None
                if (
                    x0 is not None
                    and x1 is not None
                    and y0 is not None
                    and y1 is not None
                ):
                    content = word.get("text", "")
                    if content.strip():
                        x0r, y0r, x1r, y1r = map(_round, [x0, y0, x1, y1])
                        objects.append(
                            {
                                "type": "word",
                                "page": page_num,
                                "bbox": [x0r, y0r, x1r, y1r],
                                "text": content,
                                "fontname": word.get("fontname", ""),
                                "size": word.get("size", ""),
                                "width": _round(x1 - x0),
                                "height": _round(y1 - y0),
                            }
                        )
            # --- Lines (text lines) ---
            lines = page.extract_text_lines(layout=True)
            for i, line in enumerate(lines):
                x0 = line.get("x0")
                x1 = line.get("x1")
                if "y0" in line and "y1" in line:
                    y0 = line["y0"]
                    y1 = line["y1"]
                elif "top" in line and "bottom" in line:
                    y0 = page_height - line["bottom"]
                    y1 = page_height - line["top"]
                else:
                    y0 = y1 = None
                if (
                    x0 is not None
                    and x1 is not None
                    and y0 is not None
                    and y1 is not None
                ):
                    content = line.get("text", "")
                    if content.strip():
                        x0r, y0r, x1r, y1r = map(_round, [x0, y0, x1, y1])
                        objects.append(
                            {
                                "type": "text_line",
                                "page": page_num,
                                "bbox": [x0r, y0r, x1r, y1r],
                                "text": content,
                                "width": _round(x1 - x0),
                                "height": _round(y1 - y0),
                            }
                        )
            # --- Rectangles ---
            for i, rect in enumerate(page.rects):
                x0r, y0r, x1r, y1r = map(
                    _round, [rect["x0"], rect["y0"], rect["x1"], rect["y1"]]
                )
                objects.append(
                    {
                        "type": "rect",
                        "page": page_num,
                        "bbox": [x0r, y0r, x1r, y1r],
                        "linewidth": rect.get("linewidth", ""),
                        "stroke": rect.get("stroke", ""),
                        "fill": rect.get("fill", ""),
                        "width": _round(rect["x1"] - rect["x0"]),
                        "height": _round(rect["y1"] - rect["y0"]),
                    }
                )
            # --- Lines (graphic lines) ---
            for i, line in enumerate(page.lines):
                x0, y0 = min(line["x0"], line["x1"]), min(line["y0"], line["y1"])
                x1, y1 = max(line["x0"], line["x1"]), max(line["y0"], line["y1"])
                padding = 2
                bbox = [x0 - padding, y0 - padding, x1 + padding, y1 + padding]
                x0r, y0r, x1r, y1r = map(_round, bbox)
                objects.append(
                    {
                        "type": "graphic_line",
                        "page": page_num,
                        "bbox": [x0r, y0r, x1r, y1r],
                        "start": [_round(line["x0"]), _round(line["y0"])],
                        "end": [_round(line["x1"]), _round(line["y1"])],
                        "linewidth": line.get("linewidth", ""),
                        "stroke": line.get("stroke", ""),
                        "width": _round(x1 - x0),
                        "height": _round(y1 - y0),
                    }
                )
            # --- Curves ---
            for i, curve in enumerate(page.curves):
                if "pts" in curve and curve["pts"]:
                    flipped_pts = [
                        (_round(pt[0]), _round(page_height - pt[1]))
                        for pt in curve["pts"]
                    ]
                    x_coords = [pt[0] for pt in flipped_pts]
                    y_coords = [pt[1] for pt in flipped_pts]
                    x0, x1 = min(x_coords), max(x_coords)
                    y0, y1 = min(y_coords), max(y_coords)
                    x0r, y0r, x1r, y1r = map(_round, [x0, y0, x1, y1])
                    objects.append(
                        {
                            "type": "curve",
                            "page": page_num,
                            "bbox": [x0r, y0r, x1r, y1r],
                            "points": flipped_pts,
                            "linewidth": curve.get("linewidth", ""),
                            "stroke": curve.get("stroke", ""),
                            "width": _round(x1 - x0),
                            "height": _round(y1 - y0),
                        }
                    )
            # --- Images ---
            for i, image in enumerate(page.images):
                x0 = image.get("x0")
                x1 = image.get("x1")
                y0 = image.get("y0")
                y1 = image.get("y1")

                if (
                    x0 is not None
                    and x1 is not None
                    and y0 is not None
                    and y1 is not None
                ):
                    x0r, y0r, x1r, y1r = map(_round, [x0, y0, x1, y1])
                    # Avoid including non-JSON-serializable objects like PDFStream
                    objects.append(
                        {
                            "type": "image",
                            "page": page_num,
                            "bbox": [x0r, y0r, x1r, y1r],
                            "width": _round(x1 - x0),
                            "height": _round(y1 - y0),
                            "name": image.get("name", ""),
                            # "stream" omitted due to non-serializable PDFStream values
                            "format": image.get("format", ""),
                            "colorspace": image.get("colorspace", ""),
                            "bits": image.get("bits", ""),
                            "width_pixels": image.get("width", ""),
                            "height_pixels": image.get("height", ""),
                        }
                    )
            # --- Tables ---
            tables = page.extract_tables()
            for i, table in enumerate(tables):
                table_bbox = list(map(_round, page.bbox))
                try:
                    table_finder = page.debug_tablefinder()
                    if hasattr(table_finder, "tables") and table_finder.tables:
                        if i < len(table_finder.tables):
                            table_obj = table_finder.tables[i]
                            if hasattr(table_obj, "bbox"):
                                tb = table_obj.bbox
                                if tb[1] < tb[3]:
                                    y0_flipped = _round(page_height - tb[3])
                                    y1_flipped = _round(page_height - tb[1])
                                    table_bbox = [
                                        _round(tb[0]),
                                        y0_flipped,
                                        _round(tb[2]),
                                        y1_flipped,
                                    ]
                                else:
                                    table_bbox = list(map(_round, tb))
                except Exception:
                    pass
                objects.append(
                    {
                        "type": "table",
                        "page": page_num,
                        "bbox": table_bbox,
                        "rows": len(table),
                        "cols": len(table[0]) if table else 0,
                        "preview": table[:3],
                        "width": _round(table_bbox[2] - table_bbox[0]),
                        "height": _round(table_bbox[3] - table_bbox[1]),
                    }
                )
    return objects


# ---- CLI / Electron entrypoint ----


def _stderr_json(
    error: str, message: str, details: Optional[Dict[str, Any]] = None
) -> None:
    payload: Dict[str, Any] = {
        "error": error,
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    sys.stderr.write(json.dumps(payload) + "\n")


def _die(
    exit_code: int, error: str, message: str, details: Optional[Dict[str, Any]] = None
) -> None:
    _stderr_json(error, message, details)
    sys.exit(exit_code)


def _json_default(o: Any) -> Any:
    """Fallback serializer for JSON. Stringifies pdfminer types and other unknowns."""
    try:
        from pdfminer.psparser import PSLiteral, PSKeyword  # type: ignore

        if isinstance(o, (PSLiteral, PSKeyword)):
            return str(o)
    except Exception:
        pass

    if isinstance(o, bytes):
        return o.decode("latin1", errors="replace")

    return str(o)


def _normalize_path(arg: str) -> str:
    # Accept raw paths and file:// URIs
    if arg.startswith("file://"):
        parsed = urlparse(arg)
        path = unquote(parsed.path)
        # On Windows, strip a leading slash from paths like /C:/...
        if os.name == "nt" and len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return path
    return arg


if __name__ == "__main__":
    if len(sys.argv) < 2:
        _die(
            2,
            "MISSING_ARGUMENT",
            "Usage: python pdf_objects.py <pdf_path_or_base64_data>",
        )

    input_arg = sys.argv[1]

    # Prefer treating input as a file path first
    candidate_path = _normalize_path(input_arg)
    pdf_bytes: Optional[bytes] = None

    try:
        if os.path.exists(candidate_path):
            with open(candidate_path, "rb") as f:
                pdf_bytes = f.read()
        else:
            # Fallback: attempt strict base64
            try:
                decoded = base64.b64decode(input_arg, validate=True)
                if not decoded.startswith(b"%PDF"):
                    _die(
                        4,
                        "INVALID_PDF_DATA",
                        "Decoded input is not valid PDF data",
                        {"header": decoded[:8].decode("latin1", errors="replace")},
                    )
                pdf_bytes = decoded
            except binascii.Error as e:
                _die(
                    3,
                    "FILE_NOT_FOUND",
                    "Input is neither an existing file path nor valid base64 PDF",
                    {
                        "input": input_arg,
                        "normalizedPath": candidate_path,
                        "b64error": str(e),
                    },
                )
    except Exception as e:
        _die(
            5,
            "FILE_READ_FAILED",
            "Failed to read PDF file",
            {"path": candidate_path, "error": str(e)},
        )

    if pdf_bytes is None:
        _die(6, "NO_DATA", "No PDF data available after parsing input")

    # Narrow Optional[bytes] to bytes for type checkers
    assert pdf_bytes is not None

    try:
        objs = extract_pdf_objects_from_bytes(pdf_bytes)
        print(json.dumps(objs, indent=2, default=_json_default))
    except Exception as e:
        _die(7, "EXTRACTION_FAILED", "Failed to extract PDF objects", {"error": str(e)})
