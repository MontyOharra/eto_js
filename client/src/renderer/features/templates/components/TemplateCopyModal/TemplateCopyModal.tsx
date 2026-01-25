/**
 * TemplateCopyModal
 * Modal for selecting an existing template to copy structure from
 * (signature objects, extraction fields, pipeline)
 */

import { useState, useMemo } from 'react';
import { useTemplates, useCustomers, useTemplateVersionDetail } from '../../api/hooks';
import { usePdfData } from '../../../pdf/api/hooks';
import { PdfViewer, usePdfViewer } from '../../../pdf';
import { OBJECT_FILL_COLORS, OBJECT_BORDER_COLORS } from '../../constants';
import { usePipelinesApi } from '../../../pipelines/api/hooks';
import type { PdfObjects, ExtractionField } from '../../types';
import type { PipelineState, VisualState } from '../../../pipelines/types';

interface TemplateCopyModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** PDF objects from the template currently being built */
  availablePdfObjects: PdfObjects;
  /** Callback when user confirms copy - receives matched signature objects, extraction fields, and pipeline */
  onCopyStructure: (
    signatureObjects: PdfObjects,
    extractionFields: ExtractionField[],
    pipelineState: PipelineState,
    visualState: VisualState
  ) => void;
}

export function TemplateCopyModal({
  isOpen,
  onClose,
  availablePdfObjects,
  onCopyStructure,
}: TemplateCopyModalProps) {
  // Filter state
  const [nameFilter, setNameFilter] = useState('');
  const [customerFilter, setCustomerFilter] = useState<number | null>(null);
  const [minPages, setMinPages] = useState('');
  const [maxPages, setMaxPages] = useState('');

  // Selected template
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);

  // Fetch templates (active only)
  const { data: templates, isLoading: isLoadingTemplates } = useTemplates({ status: 'active' });
  const { data: customers } = useCustomers();

  // Get selected template data
  const selectedTemplate = useMemo(() => {
    if (!selectedTemplateId || !templates) return null;
    return templates.find((t) => t.id === selectedTemplateId) ?? null;
  }, [selectedTemplateId, templates]);

  // Fetch version details for selected template
  const versionId = selectedTemplate?.current_version?.version_id ?? null;
  const { data: versionDetail, isLoading: isLoadingVersion } = useTemplateVersionDetail(versionId);

  // Fetch PDF data for selected template
  const sourcePdfId = selectedTemplate?.source_pdf_id ?? null;
  const { data: pdfData, isLoading: isLoadingPdf } = usePdfData(sourcePdfId);

  // Pipeline API for fetching pipeline definition
  const { getPipeline } = usePipelinesApi();
  const [isCopying, setIsCopying] = useState(false);

  /**
   * Find signature objects that exist in both the source template and the available PDF objects.
   * Matching is done by type, page, and exact bbox coordinates.
   */
  const findMatchingSignatureObjects = (
    sourceSignatureObjects: PdfObjects,
    availableObjects: PdfObjects
  ): PdfObjects => {
    const matched: PdfObjects = {
      text_words: [],
      graphic_rects: [],
      graphic_lines: [],
      graphic_curves: [],
      images: [],
      tables: [],
    };

    // Helper to check if two bboxes are equal
    const bboxEqual = (a: [number, number, number, number], b: [number, number, number, number]) =>
      a[0] === b[0] && a[1] === b[1] && a[2] === b[2] && a[3] === b[3];

    // Helper to find matching objects for a specific type
    const findMatches = <T extends { page: number; bbox: [number, number, number, number] }>(
      sourceObjects: T[] | undefined,
      availableObjects: T[] | undefined
    ): T[] => {
      if (!sourceObjects || !availableObjects) return [];

      return sourceObjects.filter((srcObj) =>
        availableObjects.some(
          (avail) => avail.page === srcObj.page && bboxEqual(avail.bbox, srcObj.bbox)
        )
      );
    };

    matched.text_words = findMatches(sourceSignatureObjects.text_words, availableObjects.text_words);
    matched.graphic_rects = findMatches(sourceSignatureObjects.graphic_rects, availableObjects.graphic_rects);
    matched.graphic_lines = findMatches(sourceSignatureObjects.graphic_lines, availableObjects.graphic_lines);
    matched.graphic_curves = findMatches(sourceSignatureObjects.graphic_curves, availableObjects.graphic_curves);
    matched.images = findMatches(sourceSignatureObjects.images, availableObjects.images);
    matched.tables = findMatches(sourceSignatureObjects.tables, availableObjects.tables);

    return matched;
  };

  // Handle copy structure button click
  const handleCopyStructure = async () => {
    if (!versionDetail) return;

    setIsCopying(true);
    try {
      // Fetch the pipeline definition
      const pipelineDetail = await getPipeline(versionDetail.pipeline_definition_id);

      // Find signature objects that exist in both source and available
      const matchedSignatureObjects = findMatchingSignatureObjects(
        versionDetail.signature_objects,
        availablePdfObjects
      );

      // Copy extraction fields directly
      const extractionFields = versionDetail.extraction_fields;

      // Call the callback with matched data including pipeline
      onCopyStructure(
        matchedSignatureObjects,
        extractionFields,
        pipelineDetail.pipeline_state,
        pipelineDetail.visual_state
      );
      onClose();
    } catch (error) {
      console.error('[TemplateCopyModal] Failed to fetch pipeline:', error);
      // Could add error state here if needed
    } finally {
      setIsCopying(false);
    }
  };

  // Filter templates
  const filteredTemplates = useMemo(() => {
    if (!templates) return [];

    return templates.filter((template) => {
      // Name filter
      if (nameFilter && !template.name.toLowerCase().includes(nameFilter.toLowerCase())) {
        return false;
      }

      // Customer filter
      if (customerFilter !== null && template.customer_id !== customerFilter) {
        return false;
      }

      // Page count filters
      const pageCount = template.page_count ?? 0;
      if (minPages && pageCount < parseInt(minPages, 10)) {
        return false;
      }
      if (maxPages && pageCount > parseInt(maxPages, 10)) {
        return false;
      }

      return true;
    });
  }, [templates, nameFilter, customerFilter, minPages, maxPages]);

  // Get customer name by ID
  const getCustomerName = (customerId: number | null) => {
    if (!customerId || !customers) return 'No customer';
    const customer = customers.find((c) => c.id === customerId);
    return customer?.name ?? 'Unknown';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-[95vw] h-[95vh] overflow-hidden flex flex-col shadow-2xl border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
          <h2 className="text-xl font-semibold text-white">Copy Template Structure</h2>
          <button
            onClick={onClose}
            className="ml-4 p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-800"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-hidden min-h-0 flex">
          {/* Left Pane - Template List */}
          <div className="w-80 flex-shrink-0 border-r border-gray-700 flex flex-col bg-gray-900">
            {/* Filters Section */}
            <div className="p-4 border-b border-gray-700 space-y-3">
              {/* Name Filter */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Template Name
                </label>
                <input
                  type="text"
                  value={nameFilter}
                  onChange={(e) => setNameFilter(e.target.value)}
                  placeholder="Search by name..."
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              {/* Customer Filter */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Customer
                </label>
                <select
                  value={customerFilter ?? ''}
                  onChange={(e) => setCustomerFilter(e.target.value ? parseInt(e.target.value, 10) : null)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">All Customers</option>
                  {customers?.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Page Count Filter */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Page Count
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={minPages}
                    onChange={(e) => setMinPages(e.target.value)}
                    placeholder="Min"
                    min="1"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                  <span className="text-gray-400 text-sm">-</span>
                  <input
                    type="number"
                    value={maxPages}
                    onChange={(e) => setMaxPages(e.target.value)}
                    placeholder="Max"
                    min="1"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Template List */}
            <div className="flex-1 overflow-y-auto">
              {isLoadingTemplates ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                </div>
              ) : filteredTemplates.length === 0 ? (
                <div className="p-4 text-center text-gray-400 text-sm">
                  No templates found
                </div>
              ) : (
                <div className="divide-y divide-gray-700">
                  {filteredTemplates.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => setSelectedTemplateId(template.id)}
                      className={`w-full p-3 text-left transition-colors ${
                        selectedTemplateId === template.id
                          ? 'bg-blue-600'
                          : 'hover:bg-gray-800'
                      }`}
                    >
                      <div className="font-medium text-white text-sm truncate">
                        {template.name}
                      </div>
                      <div className="text-xs text-gray-400 mt-1 flex items-center gap-2">
                        <span className="truncate">{getCustomerName(template.customer_id)}</span>
                        <span>•</span>
                        <span>{template.page_count ?? 0} pg</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Pane - PDF Preview */}
          <div className="flex-1 bg-gray-800 overflow-hidden">
            {!selectedTemplateId ? (
              <div className="h-full flex items-center justify-center">
                <p className="text-gray-400">Select a template to preview</p>
              </div>
            ) : isLoadingVersion || isLoadingPdf ? (
              <div className="h-full flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              </div>
            ) : pdfData && versionDetail ? (
              <PdfViewer pdfUrl={pdfData.url} autoFitWidth>
                <PdfViewer.Canvas pdfUrl={pdfData.url}>
                  <CombinedOverlay
                    signatureObjects={versionDetail.signature_objects}
                    extractionFields={versionDetail.extraction_fields}
                  />
                </PdfViewer.Canvas>
                <PdfViewer.ControlsSidebar position="right" />
              </PdfViewer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="text-gray-400">Unable to load preview</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-700 flex-shrink-0 bg-gray-900">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCopyStructure}
            disabled={selectedTemplateId === null || !versionDetail || isCopying}
            className="px-6 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
          >
            {isCopying ? 'Copying...' : 'Copy Structure'}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// CombinedOverlay - Renders both signature objects and extraction fields
// =============================================================================

interface CombinedOverlayProps {
  signatureObjects: PdfObjects;
  extractionFields: ExtractionField[];
}

function CombinedOverlay({
  signatureObjects,
  extractionFields,
}: CombinedOverlayProps) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();

  // Flatten signature objects for rendering
  const flattenedSignatureObjects = useMemo(() => {
    const flat: Array<{ type: string; page: number; bbox: [number, number, number, number]; [key: string]: any }> = [];

    const addObjects = (objects: any[] | undefined, type: string) => {
      if (!objects) return;
      objects.forEach((obj) => {
        flat.push({
          ...obj,
          type,
          page: obj.page || 1,
        });
      });
    };

    addObjects(signatureObjects.text_words, 'text_word');
    addObjects(signatureObjects.graphic_rects, 'graphic_rect');
    addObjects(signatureObjects.graphic_lines, 'graphic_line');
    addObjects(signatureObjects.graphic_curves, 'graphic_curve');
    addObjects(signatureObjects.images, 'image');
    addObjects(signatureObjects.tables, 'table');

    return flat;
  }, [signatureObjects]);

  // Filter objects for current page
  const pageSignatureObjects = useMemo(
    () => flattenedSignatureObjects.filter((obj) => obj.page === currentPage),
    [flattenedSignatureObjects, currentPage]
  );

  const pageExtractionFields = useMemo(
    () => extractionFields.filter((field) => field.page === currentPage),
    [extractionFields, currentPage]
  );

  // Don't render if PDF dimensions aren't loaded yet
  if (!pdfDimensions) {
    return null;
  }

  const pageHeight = pdfDimensions.height;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
      }}
    >
      {/* Render signature objects */}
      {pageSignatureObjects.map((obj, idx) => {
        const [x0, y0, x1, y1] = obj.bbox;

        // Coordinate transformation
        // Text objects, tables, and curves don't need Y-axis flipping
        // Graphics (rects, lines) and images need flipping
        let screenY0: number, screenY1: number;

        const noFlipping = obj.type === 'text_word' ||
                           obj.type === 'table' ||
                           obj.type === 'graphic_curve';

        if (noFlipping) {
          screenY0 = y0;
          screenY1 = y1;
        } else {
          screenY0 = pageHeight - y1;
          screenY1 = pageHeight - y0;
        }

        const width = (x1 - x0) * renderScale;
        const height = (screenY1 - screenY0) * renderScale;
        const left = x0 * renderScale;
        const top = screenY0 * renderScale;

        const fillColor = OBJECT_FILL_COLORS[obj.type] || 'rgba(128, 128, 128, 0.2)';
        const borderColor = OBJECT_BORDER_COLORS[obj.type] || 'rgba(128, 128, 128, 0.6)';

        return (
          <div
            key={`sig-${idx}`}
            style={{
              position: 'absolute',
              left: `${left}px`,
              top: `${top}px`,
              width: `${width}px`,
              height: `${height}px`,
              border: `2px solid ${borderColor}`,
              backgroundColor: fillColor,
              pointerEvents: 'none',
            }}
          />
        );
      })}

      {/* Render extraction fields */}
      {pageExtractionFields.map((field, idx) => {
        const [x0, y0, x1, y1] = field.bbox;
        const width = (x1 - x0) * renderScale;
        const height = (y1 - y0) * renderScale;
        const left = x0 * renderScale;
        const top = y0 * renderScale;

        return (
          <div
            key={`field-${idx}`}
            style={{
              position: 'absolute',
              left: `${left}px`,
              top: `${top}px`,
              width: `${width}px`,
              height: `${height}px`,
              border: '2px solid rgba(147, 51, 234, 0.8)', // purple to match TemplateBuilder
              backgroundColor: 'rgba(147, 51, 234, 0.2)',
              pointerEvents: 'none',
            }}
            title={field.name}
          >
            {/* Field label */}
            <div
              style={{
                position: 'absolute',
                top: '-20px',
                left: '0',
                backgroundColor: '#9333ea', // purple-600
                color: 'white',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: '500',
                whiteSpace: 'nowrap',
                pointerEvents: 'none',
              }}
            >
              {field.name}
            </div>
          </div>
        );
      })}
    </div>
  );
}
