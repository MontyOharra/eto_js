# Extracted PDF Objects

This directory contains extracted PDF objects from test PDFs, formatted to match the API endpoint specification.

## Format

Each JSON file follows the structure defined in `GET /pdf-files/{id}/objects`:

```json
{
  "pdf_file_id": 103,
  "page_count": 2,
  "objects": {
    "text_words": [
      {
        "page": 1,
        "bbox": [100.5, 200.3, 150.2, 210.8],
        "text": "Invoice",
        "fontname": "Helvetica",
        "fontsize": 12.0
      }
    ],
    "text_lines": [...],
    "graphic_rects": [...],
    "graphic_lines": [...],
    "graphic_curves": [...],
    "images": [...],
    "tables": [...]
  }
}
```

## Usage in Mock API

Copy the relevant sections into your mock API responses:

```typescript
// client-new/src/renderer/features/pdf-files/mocks/useMockPdfApi.ts

getPdfObjects: async (pdfFileId: number) => {
  // Import the extracted JSON
  const objectsData = await import(`./extracted_objects/${pdfFileId}_objects.json`);
  return objectsData;
}
```

## Regenerating

To regenerate these files after updating test PDFs:

```bash
cd server
python extract_test_pdfs.py
```
