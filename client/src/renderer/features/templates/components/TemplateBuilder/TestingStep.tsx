/**
 * TestingStep
 * Fourth step of template builder - test template simulation
 * Shows extraction results and pipeline execution in split-panel layout
 */

import { useState, useEffect } from 'react';
import { useSimulateTemplate } from '../../api/hooks';
import { ExecutedPipelineGraph } from '../../../pipelines/components/ExecutedPipelineGraph';
import { PdfViewer, usePdfViewer } from '../../../pdf';
import type { PdfObjects, ExtractionField } from '../../types';
import type { PipelineState } from '../../../pipelines/types';
import type { SimulateTemplateResponse } from '../../api/types';

interface TestingStepProps {
  pdfUrl: string;
  pdfObjects: PdfObjects;
  extractionFields: ExtractionField[];
  pipelineState: PipelineState;
}

type ViewMode = 'summary' | 'detail';

/**
 * ExtractedFieldsOverlay
 * Renders extraction field boxes with values on PDF canvas
 */
function ExtractedFieldsOverlay({
  fields
}: {
  fields: SimulateTemplateResponse['extraction_results']
}) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();
  const [hoveredFieldId, setHoveredFieldId] = useState<string | null>(null);

  if (!pdfDimensions) {
    return null;
  }

  const renderField = (field: typeof fields[0]) => {
    // Only show fields on current page
    if (field.page !== currentPage) return null;

    const [x0, y0, x1, y1] = field.bbox;
    const isHovered = hoveredFieldId === field.name;

    const boxStyle: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * renderScale}px`,
      top: `${y0 * renderScale}px`,
      width: `${(x1 - x0) * renderScale}px`,
      height: `${(y1 - y0) * renderScale}px`,
      backgroundColor: 'rgba(34, 197, 94, 0.15)', // Green with transparency
      border: `2px solid rgba(34, 197, 94, ${isHovered ? '1' : '0.6'})`,
      borderRadius: '2px',
      cursor: 'default',
      transition: 'border-color 0.15s ease-in-out, background-color 0.15s ease-in-out',
      zIndex: 5,
      pointerEvents: 'auto',
    };

    // Determine label position (above or below box)
    const popupHeightPixels = 90;
    const popupHeightPdfCoords = popupHeightPixels / renderScale;
    const showLabel = isHovered;
    const labelAtTop = y0 < 120;
    const labelY = labelAtTop ? y1 + 8 : y0 - popupHeightPdfCoords;

    return (
      <div key={field.name}>
        <div
          style={boxStyle}
          onMouseEnter={() => setHoveredFieldId(field.name)}
          onMouseLeave={() => setHoveredFieldId(null)}
        />
        {showLabel && (
          <div
            style={{
              position: 'absolute',
              left: `${x0 * renderScale}px`,
              top: `${labelY * renderScale}px`,
              backgroundColor: 'rgba(17, 24, 39, 0.95)',
              border: '2px solid rgba(34, 197, 94, 0.8)',
              borderRadius: '8px',
              padding: '16px 20px',
              fontSize: '24px',
              fontWeight: 500,
              color: 'white',
              whiteSpace: 'nowrap',
              zIndex: 20,
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
            }}
          >
            <div className="text-green-400 mb-2" style={{ fontSize: '20px' }}>
              {field.description || field.name}
            </div>
            <div className="text-white" style={{ fontSize: '26px', fontWeight: 700 }}>
              {field.extracted_value}
            </div>
          </div>
        )}
      </div>
    );
  };

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
      {fields.map(renderField)}
    </div>
  );
}

/**
 * ResizablePanelLayout
 * Two-panel layout with resizable divider
 */
function ResizablePanelLayout({
  leftPanel,
  rightPanel,
  defaultSplitPercentage = 50,
  onDragStateChange,
}: {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  defaultSplitPercentage?: number;
  onDragStateChange?: (isDragging: boolean) => void;
}) {
  const [leftWidth, setLeftWidth] = useState(defaultSplitPercentage);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = () => {
    setIsDragging(true);
    onDragStateChange?.(true);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;

    const container = document.querySelector('.resizable-panel-container');
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const percentage = (offsetX / rect.width) * 100;

    // Constrain between 20% and 80%
    const constrainedPercentage = Math.min(Math.max(percentage, 20), 80);
    setLeftWidth(constrainedPercentage);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    onDragStateChange?.(false);
  };

  // Attach/detach global mouse event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging]);

  return (
    <div className="flex h-full resizable-panel-container">
      {/* Left Panel */}
      <div style={{ width: `${leftWidth}%`, height: '100%' }}>{leftPanel}</div>

      {/* Resizable Divider */}
      <div
        className="w-1 bg-gray-700 hover:bg-blue-500 cursor-col-resize transition-colors flex-shrink-0 mx-1"
        onMouseDown={handleMouseDown}
        style={{
          userSelect: 'none',
          backgroundColor: isDragging ? '#3B82F6' : undefined,
        }}
      />

      {/* Right Panel */}
      <div style={{ width: `${100 - leftWidth}%`, height: '100%' }}>{rightPanel}</div>
    </div>
  );
}

export function TestingStep({
  pdfUrl,
  pdfObjects,
  extractionFields,
  pipelineState,
}: TestingStepProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('summary');
  const [result, setResult] = useState<SimulateTemplateResponse | null>(null);
  const [centerTrigger, setCenterTrigger] = useState<number>(0);
  const [isDragging, setIsDragging] = useState(false);

  const simulateMutation = useSimulateTemplate();

  const handleTest = async () => {
    try {
      const response = await simulateMutation.mutateAsync({
        pdf_objects: pdfObjects,
        extraction_fields: extractionFields,
        pipeline_state: pipelineState,
      });
      setResult(response);
      setCenterTrigger(Date.now());
    } catch (err) {
      console.error('Template simulation failed:', err);
    }
  };

  const handlePdfError = (error: Error) => {
    console.error('PDF load error:', error);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Test Controls Bar */}
      <div className="flex-shrink-0 bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h3 className="text-lg font-semibold text-white">Template Testing</h3>

          {/* View Mode Toggle - Only show after testing */}
          {result && (
            <div className="flex items-center bg-gray-700 rounded-lg p-1 border-l border-gray-600 ml-4">
              <button
                onClick={() => setViewMode('summary')}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                  viewMode === 'summary'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Summary
              </button>
              <button
                onClick={() => setViewMode('detail')}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                  viewMode === 'detail'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Detail
              </button>
            </div>
          )}
        </div>

        {/* Test Button */}
        <button
          onClick={handleTest}
          disabled={simulateMutation.isPending}
          className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          {simulateMutation.isPending ? 'Testing...' : result ? 'Re-test' : 'Test Template'}
        </button>
      </div>

      {/* Content - Split Panel Layout */}
      <div className="flex-1 overflow-hidden">
        <div className="pr-4 pl-2 py-4 h-full">
          {!result && !simulateMutation.isPending && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-gray-400 mb-4">
                  <svg
                    className="mx-auto h-16 w-16 mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                    />
                  </svg>
                  <p className="text-lg font-medium">Click "Test Template" to simulate extraction and pipeline execution</p>
                  <p className="text-sm text-gray-500 mt-2">This will show you what data would be extracted and which actions would be executed</p>
                </div>
              </div>
            </div>
          )}

          {simulateMutation.isPending && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-blue-400 mb-4">
                  <div className="animate-spin mx-auto h-12 w-12 border-4 border-blue-400 border-t-transparent rounded-full mb-4"></div>
                  <p className="text-lg font-medium">Running template simulation...</p>
                  <p className="text-sm text-gray-400 mt-2">Extracting fields and executing pipeline</p>
                </div>
              </div>
            </div>
          )}

          {result && (
            <ResizablePanelLayout
              defaultSplitPercentage={50}
              onDragStateChange={setIsDragging}
              leftPanel={
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col h-full overflow-hidden">
                  <h3 className="text-lg font-semibold text-white mb-3">
                    {viewMode === 'summary'
                      ? result.pipeline_status === 'success'
                        ? 'Actions to Execute'
                        : 'Pipeline Error'
                      : 'Pipeline Execution Graph'}
                  </h3>

                  <div className="flex-1 overflow-auto bg-gray-900 rounded p-3 relative">
                    {viewMode === 'summary' ? (
                      // Summary View - Actions/Errors
                      <div className="font-mono text-xs">
                        {result.pipeline_status === 'success' &&
                        Object.keys(result.pipeline_actions).length > 0 ? (
                          <pre className="text-gray-300 whitespace-pre-wrap break-words">
                            {JSON.stringify(result.pipeline_actions, null, 2)}
                          </pre>
                        ) : result.pipeline_status === 'failed' ? (
                          <div className="text-red-300">
                            <p className="font-bold mb-2">Pipeline Execution Failed</p>
                            <p className="mb-2">
                              {result.pipeline_error || 'No error message available'}
                            </p>
                          </div>
                        ) : (
                          <p className="text-gray-400">No actions to execute</p>
                        )}
                      </div>
                    ) : (
                      // Detail View - Pipeline Visualization
                      <div className="absolute inset-0">
                        <ExecutedPipelineGraph
                          pipelineId={0} // Not needed for simulation
                          pipelineState={pipelineState}
                          executionSteps={result.pipeline_steps}
                          centerTrigger={centerTrigger}
                          entryValues={(() => {
                            // Build entry values map from extraction results
                            const entryValuesMap: Record<
                              string,
                              { name: string; value: any; type: string }
                            > = {};

                            // Map extraction results to entry point outputs
                            pipelineState.entry_points.forEach((ep) => {
                              const extractionResult = result.extraction_results.find(
                                (r) => r.name === ep.name
                              );
                              if (extractionResult && ep.outputs[0]) {
                                entryValuesMap[ep.outputs[0].node_id] = {
                                  name: ep.name,
                                  value: extractionResult.extracted_value,
                                  type: ep.outputs[0].type,
                                };
                              }
                            });

                            return entryValuesMap;
                          })()}
                        />
                      </div>
                    )}
                  </div>
                </div>
              }
              rightPanel={
                <div className="bg-gray-800 border border-gray-700 rounded-lg h-full overflow-hidden relative pr-4 pl-1 py-4">
                  <PdfViewer pdfUrl={pdfUrl} onError={handlePdfError}>
                    <PdfViewer.Canvas pdfUrl={pdfUrl} onError={handlePdfError}>
                      {/* Show extraction field overlay with results */}
                      {result.extraction_results && result.extraction_results.length > 0 && (
                        <ExtractedFieldsOverlay fields={result.extraction_results} />
                      )}
                    </PdfViewer.Canvas>
                    <PdfViewer.ControlsSidebar position="right" />
                  </PdfViewer>
                </div>
              }
            />
          )}

          {/* Error Display */}
          {simulateMutation.isError && (
            <div className="mt-4 bg-red-900/30 border border-red-700 rounded-lg p-4">
              <p className="text-red-200">
                {simulateMutation.error instanceof Error
                  ? simulateMutation.error.message
                  : 'Template simulation failed'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
