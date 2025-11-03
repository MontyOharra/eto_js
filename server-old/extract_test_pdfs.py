"""
Standalone script to extract PDF objects from test PDFs

Run this from the server directory:
    python extract_test_pdfs.py

This will extract objects from all test PDFs and save them as JSON files
in the format expected by the mock API.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import importlib.util

# Load pdf_extractor module directly without triggering package __init__.py
pdf_extractor_path = Path(__file__).parent / 'src' / 'features' / 'pdf_processing' / 'utils' / 'pdf_extractor.py'

spec = importlib.util.spec_from_file_location("pdf_extractor", pdf_extractor_path)
pdf_extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdf_extractor)

def extract_pdf_objects(file_content: bytes):
    """Wrapper to call the extractor function"""
    return pdf_extractor.extract_pdf_objects(file_content)

# Test PDF paths
TEST_PDF_DIR = Path(__file__).parent.parent / 'client-new' / 'public' / 'data' / 'pdfs'
OUTPUT_DIR = Path(__file__).parent / 'extracted_objects'

def group_objects_by_type(objects: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Transform flat object list into grouped format matching API design

    API expects:
    {
      "text_words": [...],
      "text_lines": [...],
      "graphic_rects": [...],
      "graphic_lines": [...],
      "graphic_curves": [...],
      "images": [...],
      "tables": [...]
    }
    """
    grouped = {
        "text_words": [],
        "text_lines": [],
        "graphic_rects": [],
        "graphic_lines": [],
        "graphic_curves": [],
        "images": [],
        "tables": []
    }

    # Map type field to group name
    type_mapping = {
        "text_word": "text_words",
        "text_line": "text_lines",
        "graphic_rect": "graphic_rects",
        "graphic_line": "graphic_lines",
        "graphic_curve": "graphic_curves",
        "image": "images",
        "table": "tables"
    }

    for obj in objects:
        obj_type = obj.get('type')
        group_name = type_mapping.get(obj_type)

        if group_name:
            # Remove 'type' field from object (redundant when grouped)
            obj_copy = {k: v for k, v in obj.items() if k != 'type'}
            grouped[group_name].append(obj_copy)

    return grouped


def extract_and_save_pdf(pdf_path: Path, pdf_id: str):
    """Extract objects from a PDF and save in API format"""
    print(f"\n{'='*60}")
    print(f"Processing: {pdf_path.name} (ID: {pdf_id})")
    print(f"{'='*60}")

    # Read PDF bytes
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    # Extract objects using backend code
    result = extract_pdf_objects(pdf_bytes)

    if not result['success']:
        print(f"[ERROR] Extraction failed: {result.get('error_message')}")
        return

    # Group objects by type
    grouped_objects = group_objects_by_type(result['objects'])

    # Create API response format
    api_response = {
        "pdf_file_id": int(pdf_id),
        "page_count": result['page_count'],
        "objects": grouped_objects
    }

    # Print summary
    print(f"\n[SUCCESS] Extraction successful!")
    print(f"   Pages: {result['page_count']}")
    print(f"   Total objects: {result['object_count']}")
    print(f"   Signature hash: {result['signature_hash'][:16]}...")
    print(f"\n   Object breakdown:")
    for obj_type, objects in grouped_objects.items():
        if objects:
            print(f"     - {obj_type}: {len(objects)}")

    # Save to output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / f"{pdf_id}_objects.json"

    with open(output_file, 'w') as f:
        json.dump(api_response, f, indent=2)

    print(f"\n[SAVED] File: {output_file.relative_to(Path.cwd())}")

    return api_response


def main():
    """Extract objects from all test PDFs"""
    print("\n" + "="*60)
    print("PDF Object Extraction Script")
    print("="*60)
    print(f"Test PDF directory: {TEST_PDF_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Find all PDF files
    pdf_files = sorted(TEST_PDF_DIR.glob('*.pdf'))

    if not pdf_files:
        print(f"\n[ERROR] No PDF files found in {TEST_PDF_DIR}")
        return

    print(f"\nFound {len(pdf_files)} PDF file(s)")

    # Extract each PDF
    results = {}
    for pdf_path in pdf_files:
        # Use filename (without .pdf) as ID
        pdf_id = pdf_path.stem

        try:
            result = extract_and_save_pdf(pdf_path, pdf_id)
            if result:
                results[pdf_id] = result
        except Exception as e:
            print(f"\n[ERROR] Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()

    # Final summary
    print(f"\n{'='*60}")
    print(f"Extraction Complete!")
    print(f"{'='*60}")
    print(f"\n[SUCCESS] Successfully processed {len(results)} / {len(pdf_files)} PDFs")
    print(f"\n[OUTPUT] Files saved to: {OUTPUT_DIR}")
    print(f"\nYou can now use these JSON files in your mock API:")
    for pdf_id in sorted(results.keys()):
        print(f"   - {pdf_id}_objects.json -> Mock API for PDF ID {pdf_id}")

    print("\n" + "="*60)


if __name__ == '__main__':
    main()
