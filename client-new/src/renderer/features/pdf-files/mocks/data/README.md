# Extracted PDF Objects Data

This directory contains **real extracted PDF objects** from test PDFs, generated using the backend extraction algorithm.

## Files

- `2_objects.json` - PDF ID 2 (2 pages, 709 objects)
- `3_objects.json` - PDF ID 3 (2 pages, 735 objects)
- `4_objects.json` - PDF ID 4 (18 pages, 8,434 objects)
- `103_objects.json` - PDF ID 103 (11 pages, 6,595 objects)

## Format

Each JSON file matches the API endpoint specification for `GET /pdf-files/{id}/objects`:

```json
{
  "pdf_file_id": 103,
  "page_count": 11,
  "objects": {
    "text_words": [...],      // Text word objects with font info
    "text_lines": [...],      // Text line boundary boxes
    "graphic_rects": [...],   // Rectangle graphics
    "graphic_lines": [...],   // Line graphics
    "graphic_curves": [...],  // Bezier curves (if present)
    "images": [...],          // Embedded images (if present)
    "tables": [...]           // Detected tables (if present)
  }
}
```

## Generation

These files were generated using:

```bash
cd server
./venv/Scripts/python.exe extract_test_pdfs.py
```

The extraction script:
1. Reads PDFs from `client-new/public/data/pdfs/`
2. Extracts objects using `server/src/features/pdf_processing/utils/pdf_extractor.py`
3. Groups objects by type (matching API design)
4. Saves formatted JSON files

## Usage in Mock API

See `../useMockPdfApi.ts` which imports and serves this data.

## Regenerating

To regenerate after updating test PDFs or extraction logic:

1. Place new PDFs in `client-new/public/data/pdfs/` with numeric filenames (e.g., `5.pdf`)
2. Run extraction script: `cd server && ./venv/Scripts/python.exe extract_test_pdfs.py`
3. Move generated files: `mv server/extracted_objects/*.json client-new/src/renderer/features/pdf-files/mocks/data/`
4. Update `useMockPdfApi.ts` to import and serve the new files
