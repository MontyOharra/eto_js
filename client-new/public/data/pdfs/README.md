# Test PDFs Directory

This directory contains sample PDF files used for testing the PDF viewer in development mode.

## Usage

Place test PDF files in this directory with numeric filenames matching the mock data:

- `1.pdf` - Will be loaded for runs with `pdf.id = 1`
- `2.pdf` - Will be loaded for runs with `pdf.id = 2`
- etc.

## How It Works

The mock API (`useMockEtoApi.getPdfDownloadUrl()`) returns URLs pointing to this directory:
```typescript
getPdfDownloadUrl(1) → "/data/pdfs/1.pdf"
```

Vite's dev server automatically serves files from the `public/` directory, so these URLs work like real API endpoints that stream PDF bytes.

## Production

In production, this directory is not used. The real API endpoint `/api/pdf-files/{id}/download` reads PDFs from the server's storage directory and streams them to the client.
