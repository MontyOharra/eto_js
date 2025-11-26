/**
 * EtoSubRunDetailViewer
 * Main component for displaying detailed ETO run information
 * Refactored to use extracted sub-components
 */

import { useState } from "react";
import { useEtoSubRunDetail, useReprocessRun, useSkipRun } from "../../api/hooks";
import { EtoSubRunDetailHeader } from "./EtoSubRunDetailHeader";
import { EtoSubRunDetailFooter } from "./EtoSubRunDetailFooter";
import { SummarySuccessView } from "./SummarySuccessView";
import { SummaryErrorView } from "./SummaryErrorView";
import { DetailPipelineView } from "./DetailPipelineView";
import { ResizablePanelLayout } from "./ResizablePanelLayout";
import { PdfViewerPanel } from "./PdfViewerPanel";

interface EtoSubRunDetailViewerProps {
  isOpen: boolean;
  subRunId: number | null;
  onClose: () => void;
}

type ViewMode = "summary" | "detail";

export function EtoSubRunDetailViewer({
  isOpen,
  subRunId,
  onClose,
}: EtoSubRunDetailViewerProps) {
  const {
    data: runDetail,
    isLoading,
    error: queryError,
  } = useEtoSubRunDetail(isOpen ? subRunId : null);
  const reprocessMutation = useReprocessRun();
  const skipMutation = useSkipRun();
  const [viewMode, setViewMode] = useState<ViewMode>("summary");
  const [isDragging, setIsDragging] = useState(false);

  const error = queryError ? "Failed to load run details" : null;

  // Check if sub-run has actionable status (failure or needs_template)
  const hasActionableStatus =
    runDetail?.status === "failure" || runDetail?.status === "needs_template";

  const handleReprocess = async () => {
    if (!runDetail?.eto_run_id) return;
    try {
      await reprocessMutation.mutateAsync(runDetail.eto_run_id);
    } catch (err) {
      console.error("Failed to reprocess run:", err);
    }
  };

  const handleSkip = async () => {
    if (!runDetail?.eto_run_id) return;
    try {
      await skipMutation.mutateAsync(runDetail.eto_run_id);
    } catch (err) {
      console.error("Failed to skip run:", err);
    }
  };

  if (!isOpen || !subRunId) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-[95vw] h-[95vh] overflow-hidden border border-gray-700 flex flex-col">
        {/* Header */}
        <EtoSubRunDetailHeader
          runDetail={runDetail}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          onClose={onClose}
        />

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-blue-400">Loading run details...</div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
                <p className="text-red-200">{error}</p>
              </div>
            </div>
          )}

          {!isLoading && !error && runDetail && (
            <div className="pr-4 pl-2 py-4 h-full">
              <ResizablePanelLayout
                onDragStateChange={setIsDragging}
                leftPanel={
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col h-full overflow-hidden">
                    <h3 className="text-lg font-semibold text-white mb-3">
                      {viewMode === "summary"
                        ? runDetail.status === "success"
                          ? "Actions Executed"
                          : "Error Details"
                        : "Transformation Pipeline"}
                    </h3>

                    <div className="flex-1 overflow-auto bg-gray-900 rounded p-3 relative">
                      {viewMode === "summary" ? (
                        runDetail.status === "success" ? (
                          <SummarySuccessView
                            executedActions={
                              runDetail.stage_pipeline_execution
                                ?.executed_actions || null
                            }
                          />
                        ) : runDetail.status === "failure" ? (
                          <SummaryErrorView
                            errorType={runDetail.error_type}
                            errorMessage={runDetail.error_message}
                            errorDetails={runDetail.error_details}
                          />
                        ) : (
                          <p className="text-gray-400">No details available</p>
                        )
                      ) : (
                        <DetailPipelineView
                          pipelineDefinitionId={
                            runDetail.stage_pipeline_execution
                              ?.pipeline_definition_id || null
                          }
                          runDetail={runDetail}
                        />
                      )}
                    </div>
                  </div>
                }
                rightPanel={
                  <PdfViewerPanel
                    pdfFileId={runDetail.pdf.id}
                    overlayFields={
                      viewMode === "detail"
                        ? runDetail.stage_data_extraction?.extraction_results
                        : undefined
                    }
                    isDragging={isDragging}
                    matchedPages={runDetail.matched_pages}
                  />
                }
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <EtoSubRunDetailFooter
          runDetail={runDetail || null}
          onClose={onClose}
          showActionButtons={hasActionableStatus}
          onReprocess={handleReprocess}
          onSkip={handleSkip}
          isReprocessing={reprocessMutation.isPending}
          isSkipping={skipMutation.isPending}
        />
      </div>
    </div>
  );
}
