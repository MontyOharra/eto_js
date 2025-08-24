# PDF Field-Extraction Tool – Project Context

## 1 Problem the software solves

A trucking / logistics company receives shipment request and receipt forms from many different customers. The forms arrive as PDFs attached to e-mails and each customer formats the document differently (no industry standard).

The long-term goal is to:

1. Automatically download every attached PDF from incoming mail.
2. Compute a _signature_ of each PDF (hash of layout, fonts, etc.).
3. If the signature is already known → use a stored “extraction recipe” to pull the data and insert it into the Orders DB table.
4. If the signature is **unknown** → flag the document so a user can teach the system how to read it.

The front-end being built now is the **teaching UI** for step 4.

## 2 Current front-end capabilities

- Opens any PDF in a viewer (react-pdf).
- Lets the user draw one or more rectangles (overlay) on top of the page.
- Rectangles are stored client-side (not yet persisted) and rendered in real time.

## 3 Planned user flow

1. User selects an “unrecognised” PDF presented by the app.
2. They draw boxes around each data field (date, BOL number, weight, etc.).
3. For every box they choose which DB column (or syntactic rule) the value maps to.
4. The completed mapping + the PDF’s signature are saved to the backend.
5. Future PDFs with the same signature are parsed automatically.

## 4 Box semantics requirement

_The rectangle must fully bound the value even if the content length varies._  
Example: date might be `03/07/25` (8 chars) today and `12/25/2025` (10 chars) tomorrow. The extraction rectangle therefore has to grow with the text.

Implication: the box should **snap** or **auto-expand** to the actual text bounding box rather than the exact pixels the user dragged.

## 5 Recommended technical approach

### 5.1 Extraction strategy

1. **Coordinate space** – work in PDF user-space units (obtained from pdf.js text layer) rather than raw screen pixels.
2. **Value region selection** – the user simply draws a rectangle around the value itself (e.g. the date, BOL number). Selecting the label is optional; only the value needs to be captured for extraction.
3. **Auto-snap** logic
   - After the drag ends, query pdf.js text items whose bounding boxes intersect the raw rectangle.
   - Compute the min/max of those text items → final rectangle. This guarantees the full value is captured.
4. **Recipe storage**
   - `{ pdfSignature, pageNumber, fieldName, rect: { left, top, right, bottom } }` per field.

### 5.2 Backend changes

- Persist recipes in a table (`pdf_field_mappings`).
- On ingestion, use pdf.js (node) to extract text items, then apply every stored rectangle to grab the text.

### 5.3 Front-end additions

- Switch overlay to pdf.js coordinate system (scale-independent). Convert during draw and on zoom.
- After user confirms the rectangle, run the snap routine and redraw the adjusted box.
- Dialog / side-panel to assign DB column.

## 6 Next steps in the codebase

1.  Add helper in `PdfFieldSelector` to query textLayer spans and snap box.
2.  UI for field-name / DB-column selection.
3.  IPC channel to save the recipe to the backend.
4.  Use stored recipes in the server’s PDF-parsing pipeline.

---

This file captures the current understanding of the project and a high-level road-map. Feel free to reference or extend it in future tasks.
