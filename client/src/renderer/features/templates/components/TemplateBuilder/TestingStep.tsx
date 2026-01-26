/**
 * TestingStep
 * Fourth step of template builder - test template simulation
 * Shows extraction results and pipeline execution in split-panel layout
 */

import { useState, useEffect, useCallback } from 'react';
import { ExecutedPipelineGraph } from '../../../pipelines/components/ExecutedPipelineGraph';
import { FieldHighlightProvider, useFieldHighlight } from '../../../pipelines/contexts';
import { PdfViewer, usePdfViewer } from '../../../pdf';
import { useOutputChannels } from '../../../modules';
import {
  formatValue,
  formatChannelLabel,
  getChannelColor,
  groupOutputChannelsByCategory,
  type OutputChannelResult,
} from '../../../eto/utils';
import type { PipelineState } from '../../../pipelines/types';
import type { SimulateTemplateResponse } from '../../api/types';

// ========== Component Interfaces ==========

interface TestingStepProps {
  pdfUrl: string;
  pipelineState: PipelineState;
  viewMode: 'summary' | 'detail';
  result: SimulateTemplateResponse | null;
  isLoading: boolean;
  centerTrigger: number;
}

/**
 * ExtractedFieldsOverlay
 * Renders extraction field boxes with values on PDF canvas
 * Uses FieldHighlightContext for cross-component highlighting with pipeline entry points
 */
function ExtractedFieldsOverlay({
  fields
}: {
  fields: SimulateTemplateResponse['extraction_results']
}) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();
  const highlightContext = useFieldHighlight();

  if (!pdfDimensions) {
    return null;
  }

  const renderField = (field: typeof fields[0]) => {
    // Only show fields on current page
    if (field.page !== currentPage) return null;

    const [x0, y0, x1, y1] = field.bbox;
    const isHighlighted = highlightContext?.highlightedFieldName === field.name;

    const boxStyle: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * renderScale}px`,
      top: `${y0 * renderScale}px`,
      width: `${(x1 - x0) * renderScale}px`,
      height: `${(y1 - y0) * renderScale}px`,
      backgroundColor: isHighlighted ? 'rgba(59, 130, 246, 0.25)' : 'rgba(59, 130, 246, 0.15)',
      border: `2px solid rgba(59, 130, 246, ${isHighlighted ? '1' : '0.6'})`,
      borderRadius: '2px',
      cursor: 'default',
      transition: 'border-color 0.15s ease-in-out, background-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out',
      zIndex: 5,
      pointerEvents: 'auto',
      boxShadow: isHighlighted ? '0 0 12px rgba(59, 130, 246, 0.6)' : undefined,
    };

    // Determine label position (above or below box)
    const popupHeightPixels = 90;
    const popupHeightPdfCoords = popupHeightPixels / renderScale;
    const showLabel = isHighlighted;
    const labelAtTop = y0 < 120;
    const labelY = labelAtTop ? y1 + 8 : y0 - popupHeightPdfCoords;

    const handleMouseEnter = () => {
      highlightContext?.setHighlightedFieldName(field.name);
    };

    const handleMouseLeave = () => {
      highlightContext?.setHighlightedFieldName(null);
    };

    return (
      <div key={field.name}>
        <div
          style={boxStyle}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        />
        {showLabel && (
          <div
            style={{
              position: 'absolute',
              left: `${x0 * renderScale}px`,
              top: `${labelY * renderScale}px`,
              backgroundColor: 'rgba(17, 24, 39, 0.95)',
              border: '2px solid rgba(59, 130, 246, 0.8)',
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
  onResize,
}: {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  defaultSplitPercentage?: number;
  onDragStateChange?: (isDragging: boolean) => void;
  onResize?: () => void;
}) {
  const [leftWidth, setLeftWidth] = useState(defaultSplitPercentage);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = () => {
    setIsDragging(true);
    onDragStateChange?.(true);
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;

    const container = document.querySelector('.resizable-panel-container');
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const percentage = (offsetX / rect.width) * 100;

    // Constrain between 20% and 80%
    const constrainedPercentage = Math.min(Math.max(percentage, 20), 80);
    setLeftWidth(constrainedPercentage);

    // Call onResize callback during drag
    onResize?.();
  }, [isDragging, onResize]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    onDragStateChange?.(false);
  }, [onDragStateChange]);

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
  }, [isDragging, handleMouseMove, handleMouseUp]);

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

/**
 * AutoFitOnResize
 * Triggers PDF fit-to-width when resize divider is dragged
 * Must be used as child of PdfViewer to access context
 */
function AutoFitOnResize({ isDragging }: { isDragging: boolean }) {
  const { fitToWidth, pdfDimensions } = usePdfViewer();

  // Trigger fitToWidth when dragging (resizing)
  useEffect(() => {
    if (!isDragging || !pdfDimensions) return;

    const pdfViewerContainer = document.querySelector('.pdf-viewer-container');
    if (!pdfViewerContainer) return;

    const containerWidth = pdfViewerContainer.clientWidth;
    const sidebarWidth = 64; // w-16 = 64px
    fitToWidth(containerWidth, sidebarWidth);
  }, [isDragging, fitToWidth, pdfDimensions]);

  return null;
}

/**
 * PdfViewerWithAutoFit
 * PDF viewer that auto-fits on resize
 */
function PdfViewerWithAutoFit({
  pdfUrl,
  extractionResults,
  isDragging,
}: {
  pdfUrl: string;
  extractionResults?: SimulateTemplateResponse['extraction_results'];
  isDragging: boolean;
}) {
  const handlePdfError = (error: Error) => {
    console.error('PDF load error:', error);
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg h-full overflow-hidden relative pr-4 pl-1 py-4 pdf-viewer-container">
      <PdfViewer pdfUrl={pdfUrl} onError={handlePdfError} autoFitWidth>
        <AutoFitOnResize isDragging={isDragging} />
        <PdfViewer.Canvas pdfUrl={pdfUrl} onError={handlePdfError}>
          {extractionResults && extractionResults.length > 0 && (
            <ExtractedFieldsOverlay fields={extractionResults} />
          )}
        </PdfViewer.Canvas>
        <PdfViewer.ControlsSidebar position="right" />
      </PdfViewer>
    </div>
  );
}

export function TestingStep({
  pdfUrl,
  pipelineState,
  viewMode,
  result,
  isLoading,
  centerTrigger,
}: TestingStepProps) {
  const [isDragging, setIsDragging] = useState(false);
  const { data: outputChannelTypes } = useOutputChannels();

  const handleResize = () => {
    // Resize handler - fitToWidth is called in PdfViewerWithAutoFit
  };

  // Build output channel results with labels from output channel types registry
  const outputChannelGroups = (() => {
    if (!result?.output_channel_values) return [];

    const results = Object.entries(result.output_channel_values).map(([channelType, value]) => {
      // Get label from output channel types registry
      const channelTypeInfo = outputChannelTypes?.find(
        (oct) => oct.name === channelType
      );
      const label = channelTypeInfo?.label || formatChannelLabel(channelType);

      return {
        label,
        channelType,
        value,
      };
    });

    // Group results by category
    return groupOutputChannelsByCategory(results, outputChannelTypes);
  })();

  return (
    <div className="h-full overflow-hidden">
      <div className="pr-4 pl-2 py-4 h-full">
        {!result && !isLoading && (
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

        {isLoading && (
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
          <FieldHighlightProvider>
            <ResizablePanelLayout
              defaultSplitPercentage={50}
              onDragStateChange={setIsDragging}
              onResize={handleResize}
              leftPanel={
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col h-full overflow-hidden">
                  <h3 className="text-lg font-semibold text-white mb-3">
                    {viewMode === 'summary'
                      ? result.pipeline_status === 'success'
                        ? 'Output Channel Values'
                        : 'Pipeline Error'
                      : 'Pipeline Execution Graph'}
                  </h3>

                  <div className="flex-1 overflow-auto bg-gray-900 rounded p-3 relative">
                    {viewMode === 'summary' ? (
                      // Summary View - Output Channel Values/Errors
                      <div>
                        {result.pipeline_status === 'success' && outputChannelGroups.length > 0 ? (
                          <div className="space-y-4">
                            {outputChannelGroups.map((group) => {
                              const colors = getChannelColor();
                              return (
                                <div key={group.category}>
                                  <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
                                    {group.categoryLabel}
                                  </h4>
                                  <div className="space-y-2">
                                    {group.channels.map((channelResult, index) => (
                                      <div
                                        key={index}
                                        className={`flex items-start gap-3 py-2 px-3 rounded border ${colors.bg} ${colors.border}`}
                                      >
                                        <span className={`text-sm w-40 flex-shrink-0 font-medium ${colors.text}`}>
                                          {channelResult.label}
                                        </span>
                                        <span className="text-sm text-white break-words flex-1">
                                          {formatValue(channelResult.value)}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : result.pipeline_status === 'failed' ? (
                          <div className="text-red-300">
                            <p className="font-bold mb-2">Pipeline Execution Failed</p>
                            <p className="mb-2">
                              {result.pipeline_error || 'No error message available'}
                            </p>
                          </div>
                        ) : result.pipeline_status === 'success' ? (
                          <div className="flex flex-col items-center justify-center h-full text-center py-8">
                            <div className="text-green-400 mb-4">
                              <svg
                                className="mx-auto h-12 w-12"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                              </svg>
                            </div>
                            <p className="text-green-400 font-medium mb-1">
                              Pipeline Completed Successfully
                            </p>
                            <p className="text-gray-400 text-sm">
                              No output channels configured
                            </p>
                          </div>
                        ) : (
                          <p className="text-gray-400">No results available</p>
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
                <PdfViewerWithAutoFit
                  pdfUrl={pdfUrl}
                  extractionResults={result.extraction_results}
                  isDragging={isDragging}
                />
              }
            />
          </FieldHighlightProvider>
        )}
      </div>
    </div>
  );
}
