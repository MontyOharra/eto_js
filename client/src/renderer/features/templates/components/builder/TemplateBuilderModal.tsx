/**
 * Template Builder Modal
 * 3-step wizard for creating PDF templates
 */

import { useState, useMemo, useEffect } from "react";
import { SignatureObject, ExtractionField } from "../../types";
import {
  SignatureObjectsStep,
  ExtractionFieldsStep,
  PipelineBuilderStep,
  TestingStep,
  TemplateSimulationResult,
} from "./steps";
import { TemplateBuilderHeader, TemplateBuilderStepper } from "./components";
import { usePdfData, usePdfFilesApi } from "../../../pdf-files/hooks";
import { useModulesApi } from "../../../modules/hooks";
import { useTemplatesApi } from "../../hooks";
import { usePipelineValidation } from "../../../pipelines/hooks";
import type { ModuleTemplate } from "../../../../shared/types/moduleTypes";
import type {
  PipelineState,
  VisualState,
} from "../../../../types/pipelineTypes";

interface TemplateBuilderModalProps {
  isOpen: boolean;
  mode: "create" | "edit"; // NEW: Determines if creating new or editing existing
  templateId?: number; // NEW: Required for edit mode
  pdfFileId: number | null;
  pdfFile: File | null; // For new template creation with uploaded PDF
  onClose: () => void;
  onSave: (templateData: TemplateData) => Promise<void>;
  initialData?: TemplateData; // NEW: Pre-populate wizard in edit mode
}

export interface TemplateData {
  name: string;
  description: string;
  source_pdf_id?: number | null; // Optional for uploaded PDFs
  pdf_file?: File | null; // For uploaded PDFs
  signature_objects: SignatureObject[];
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

type BuilderStep =
  | "signature-objects"
  | "extraction-fields"
  | "pipeline"
  | "testing";

export function TemplateBuilderModal({
  isOpen,
  mode,
  templateId,
  pdfFileId,
  pdfFile,
  onClose,
  onSave,
  initialData,
}: TemplateBuilderModalProps) {
  const [currentStep, setCurrentStep] =
    useState<BuilderStep>("signature-objects");
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [signatureObjects, setSignatureObjects] = useState<{
    text_words: any[];
    text_lines: any[];
    graphic_rects: any[];
    graphic_lines: any[];
    graphic_curves: any[];
    images: any[];
    tables: any[];
  }>({
    text_words: [],
    text_lines: [],
    graphic_rects: [],
    graphic_lines: [],
    graphic_curves: [],
    images: [],
    tables: [],
  });
  const [selectedObjectTypes, setSelectedObjectTypes] = useState<string[]>([]); // Step 1 state persistence
  const [extractionFields, setExtractionFields] = useState<ExtractionField[]>(
    []
  );
  const [pipelineState, setPipelineStateInternal] = useState<PipelineState>({
    entry_points: [],
    modules: [],
    connections: [],
  });

  // Wrapper to log pipeline state changes
  const setPipelineState = (newState: PipelineState) => {
    console.log("[TemplateBuilderModal] Pipeline state changing:", {
      oldEntryPoints: pipelineState.entry_points.map((ep) => ep.node_id),
      newEntryPoints: newState.entry_points.map((ep) => ep.node_id),
    });
    setPipelineStateInternal(newState);
  };
  // Flat visual state: all node positions in one object
  const [visualState, setVisualStateInternal] = useState<VisualState>({});

  // Wrapper to log visual state changes
  const setVisualState = (newState: VisualState) => {
    console.log("[TemplateBuilderModal] Visual state updated:", {
      nodeCount: Object.keys(newState).length,
      entryPointIds: Object.keys(newState).filter((id) =>
        id.startsWith("entry-")
      ),
      moduleIds: Object.keys(newState).filter((id) => !id.startsWith("entry-")),
      entryPointPositions: Object.fromEntries(
        Object.entries(newState).filter(([id]) => id.startsWith("entry-"))
      ),
    });
    setVisualStateInternal(newState);
  };
  const [testResults, setTestResults] =
    useState<TemplateSimulationResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testViewMode, setTestViewMode] = useState<"summary" | "detail">(
    "summary"
  );
  const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);

  // Snapshot of pipeline/visual state when test is run (frozen for testing view)
  const [testedPipelineState, setTestedPipelineState] =
    useState<PipelineState | null>(null);
  const [testedVisualState, setTestedVisualState] =
    useState<VisualState | null>(null);

  // PDF viewer state persistence across steps
  const [pdfScale, setPdfScale] = useState<number>(1.0);
  const [pdfCurrentPage, setPdfCurrentPage] = useState<number>(1);

  // State for uploaded PDF file
  const [uploadedPdfUrl, setUploadedPdfUrl] = useState<string | null>(null);
  const [uploadedPdfData, setUploadedPdfData] = useState<any>(null);
  const [isProcessingUpload, setIsProcessingUpload] = useState(false);

  // Use React Query to fetch and cache PDF data (only for stored PDFs)
  const {
    data: pdfData,
    isLoading: pdfLoading,
    error: pdfError,
  } = usePdfData(pdfFileId);
  const { getModules } = useModulesApi();
  const { uploadPdf, processObjects } = usePdfFilesApi();
  const { simulateTemplate } = useTemplatesApi();

  // Auto-validate pipeline as it's being built
  const {
    isValid: isPipelineValid,
    error: pipelineValidationError,
    isValidating: isPipelineValidating,
  } = usePipelineValidation(pipelineState);

  // Load module templates for pipeline execution visualization
  useEffect(() => {
    async function loadModules() {
      try {
        const response = await getModules();
        setModuleTemplates(response.modules);
      } catch (error) {
        console.error("Failed to load modules:", error);
        setModuleTemplates([]);
      }
    }
    loadModules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only load once on mount

  // Initialize state from initialData when in edit mode
  useEffect(() => {
    if (mode === "edit" && initialData && isOpen) {
      console.log("[TemplateBuilderModal] Initializing edit mode with data:", {
        name: initialData.name,
        description: initialData.description,
        signatureObjectsKeys: Object.keys(initialData.signature_objects),
        signatureObjectsCounts: {
          text_words: initialData.signature_objects.text_words?.length || 0,
          text_lines: initialData.signature_objects.text_lines?.length || 0,
          graphic_rects:
            initialData.signature_objects.graphic_rects?.length || 0,
          graphic_lines:
            initialData.signature_objects.graphic_lines?.length || 0,
          graphic_curves:
            initialData.signature_objects.graphic_curves?.length || 0,
          images: initialData.signature_objects.images?.length || 0,
          tables: initialData.signature_objects.tables?.length || 0,
        },
        extractionFields: initialData.extraction_fields.length,
        pipelineModules: initialData.pipeline_state.modules.length,
      });

      setTemplateName(initialData.name);
      setTemplateDescription(initialData.description);

      // Deep copy to avoid reference issues
      setSignatureObjects({
        text_words: [...(initialData.signature_objects.text_words || [])],
        text_lines: [...(initialData.signature_objects.text_lines || [])],
        graphic_rects: [...(initialData.signature_objects.graphic_rects || [])],
        graphic_lines: [...(initialData.signature_objects.graphic_lines || [])],
        graphic_curves: [
          ...(initialData.signature_objects.graphic_curves || []),
        ],
        images: [...(initialData.signature_objects.images || [])],
        tables: [...(initialData.signature_objects.tables || [])],
      });

      setExtractionFields([...initialData.extraction_fields]);
      setPipelineState(initialData.pipeline_state);
      setVisualState(initialData.visual_state);

      // Determine which object types are selected based on signature_objects
      const selectedTypes: string[] = [];
      if (initialData.signature_objects.text_words?.length > 0)
        selectedTypes.push("text_words");
      if (initialData.signature_objects.text_lines?.length > 0)
        selectedTypes.push("text_lines");
      if (initialData.signature_objects.graphic_rects?.length > 0)
        selectedTypes.push("graphic_rects");
      if (initialData.signature_objects.graphic_lines?.length > 0)
        selectedTypes.push("graphic_lines");
      if (initialData.signature_objects.graphic_curves?.length > 0)
        selectedTypes.push("graphic_curves");
      if (initialData.signature_objects.images?.length > 0)
        selectedTypes.push("images");
      if (initialData.signature_objects.tables?.length > 0)
        selectedTypes.push("tables");

      console.log(
        "[TemplateBuilderModal] Setting selectedObjectTypes:",
        selectedTypes
      );
      setSelectedObjectTypes(selectedTypes);
    }
  }, [mode, initialData, isOpen]);

  // Process uploaded PDF file
  useEffect(() => {
    if (!pdfFile) {
      setUploadedPdfUrl(null);
      setUploadedPdfData(null);
      return;
    }

    async function processUploadedPdf() {
      setIsProcessingUpload(true);

      try {
        // Create blob URL for PDF viewer
        const blobUrl = URL.createObjectURL(pdfFile);
        setUploadedPdfUrl(blobUrl);

        // Process PDF to extract objects via real API
        const objectsData = await processObjects(pdfFile);

        const mockMetadata = {
          id: -1, // Temporary ID for uploaded file
          email_id: null,
          filename: pdfFile.name,
          original_filename: pdfFile.name,
          relative_path: "", // No path for uploaded files
          file_size: pdfFile.size,
          file_hash: null, // Not calculated for uploaded files
          page_count: objectsData.page_count,
        };

        setUploadedPdfData({
          objectsData: objectsData,
          url: blobUrl,
          metadata: mockMetadata,
          emailData: null,
        });
      } catch (error) {
        console.error(
          "[TemplateBuilderModal] Failed to process uploaded PDF:",
          error
        );
        // Keep URL but show empty objects on error
        const blobUrl = URL.createObjectURL(pdfFile);
        setUploadedPdfUrl(blobUrl);
        setUploadedPdfData(null);
      } finally {
        setIsProcessingUpload(false);
      }
    }

    processUploadedPdf();

    // Cleanup blob URL on unmount
    return () => {
      if (uploadedPdfUrl) {
        URL.revokeObjectURL(uploadedPdfUrl);
      }
    };
  }, [pdfFile]);

  // Extract PDF data from either stored PDF or uploaded file
  const activePdfData = pdfFile ? uploadedPdfData : pdfData;
  const pdfObjects = activePdfData?.objectsData;
  const pdfUrl = activePdfData?.url || "";
  const pdfDataLoaded = !!activePdfData;
  const isPdfLoading = pdfFile ? isProcessingUpload : pdfLoading;

  // Calculate completed steps
  // Helper to count total signature objects
  const signatureObjectsCount = useMemo(() => {
    return Object.values(signatureObjects).reduce(
      (sum, arr) => sum + arr.length,
      0
    );
  }, [signatureObjects]);

  const completedSteps = useMemo(() => {
    const completed = new Set<BuilderStep>();
    if (signatureObjectsCount > 0) completed.add("signature-objects");
    if (extractionFields.length > 0) completed.add("extraction-fields");
    return completed;
  }, [signatureObjectsCount, extractionFields.length]);

  // Determine if user can proceed from current step
  const canProceed = useMemo(() => {
    switch (currentStep) {
      case "signature-objects":
        return signatureObjectsCount > 0 && templateName.trim().length > 0;
      case "extraction-fields":
        return extractionFields.length > 0;
      case "pipeline":
        // Pipeline step requires valid pipeline and not currently validating
        return isPipelineValid && !isPipelineValidating;
      case "testing":
        return testResults !== null;
      default:
        return false;
    }
  }, [
    currentStep,
    signatureObjectsCount,
    templateName,
    extractionFields.length,
    testResults,
    isPipelineValid,
    isPipelineValidating,
  ]);

  // Get validation message for current step
  const validationMessage = useMemo(() => {
    if (canProceed) return undefined;

    switch (currentStep) {
      case "signature-objects":
        if (templateName.trim().length === 0) {
          return "Please enter a template name";
        }
        if (signatureObjectsCount === 0) {
          return "Please select at least one signature object";
        }
        return undefined;
      case "extraction-fields":
        return "Please define at least one extraction field";
      case "pipeline":
        // Show validation error or validating status
        if (isPipelineValidating) {
          return "Validating pipeline...";
        }
        if (pipelineValidationError) {
          return `[${pipelineValidationError.code}] ${pipelineValidationError.message}`;
        }
        return "Pipeline validation failed";
      default:
        return undefined;
    }
  }, [
    currentStep,
    canProceed,
    templateName,
    signatureObjectsCount,
    isPipelineValidating,
    pipelineValidationError,
  ]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Step 1: Upload PDF if needed (for newly uploaded files in create mode)
      let sourcePdfId = pdfFileId;

      if (!sourcePdfId && pdfFile && mode === "create") {
        const uploadResponse = await uploadPdf(pdfFile);
        sourcePdfId = uploadResponse.id;
      }

      if (!sourcePdfId) {
        throw new Error(
          "No PDF source available. Please ensure a PDF is loaded."
        );
      }

      // Step 2: Call parent's onSave with template data
      // Parent will handle the actual API call (create or update) and list reload
      await onSave({
        name: templateName,
        description: templateDescription,
        source_pdf_id: sourcePdfId,
        signature_objects: signatureObjects,
        extraction_fields: extractionFields,
        pipeline_state: pipelineState,
        visual_state: visualState,
      });

      handleClose();
    } catch (error) {
      console.error(
        `[TemplateBuilderModal] Failed to ${mode} template:`,
        error
      );
      alert(
        `Failed to ${mode} template: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    setIsTesting(true);

    // Snapshot the current pipeline state (frozen for the test)
    const pipelineSnapshot = JSON.parse(
      JSON.stringify(pipelineState)
    ) as PipelineState;
    const visualSnapshot = JSON.parse(
      JSON.stringify(visualState)
    ) as VisualState;
    setTestedPipelineState(pipelineSnapshot);
    setTestedVisualState(visualSnapshot);

    try {
      // Ensure PDF objects are available (already extracted during upload/load)
      if (!pdfObjects) {
        throw new Error(
          "PDF objects not available for testing. Please ensure PDF is loaded."
        );
      }

      // Transform extraction fields to backend format (already matches!)
      const backendExtractionFields = extractionFields.map((field) => ({
        name: field.name,
        description: field.description,
        bbox: field.bbox,
        page: field.page,
      }));

      // Build JSON request (NOT FormData!)
      const request = {
        pdf_objects: pdfObjects.objects, // Send just the objects part (text_words, text_lines, etc.)
        extraction_fields: backendExtractionFields,
        pipeline_state: pipelineState,
      };

      // Call real simulate API with JSON body
      const response = await simulateTemplate(request);

      // Map API response to TemplateSimulationResult format
      // Convert extraction_results array to extracted_data map
      const extractedDataByFieldName: Record<string, string> = {};
      response.extraction_results.forEach((result) => {
        extractedDataByFieldName[result.name] = result.extracted_value;
      });

      // Convert pipeline_actions (dict of module actions) to simulated_actions array
      const simulatedActions = Object.entries(response.pipeline_actions).map(
        ([moduleId, inputs]) => ({
          action_module_name: moduleId, // Using module_instance_id as action name
          inputs: inputs,
        })
      );

      // Parse error type and message from pipeline_error (format: "ErrorType: message")
      let errorType: string | null = null;
      let errorMessage: string | null = null;
      if (response.pipeline_error) {
        const colonIndex = response.pipeline_error.indexOf(":");
        if (colonIndex > 0) {
          errorType = response.pipeline_error.substring(0, colonIndex).trim();
          errorMessage = response.pipeline_error
            .substring(colonIndex + 1)
            .trim();
        } else {
          errorMessage = response.pipeline_error;
        }
      }

      const simulationResult: TemplateSimulationResult = {
        status: response.pipeline_status === "success" ? "success" : "failure",
        error_type: errorType,
        error_message: errorMessage,
        data_extraction: {
          extracted_data: extractedDataByFieldName,
          extracted_fields_with_boxes: response.extraction_results.map(
            (result) => ({
              name: result.name,
              value: result.extracted_value,
              page: result.page,
              bbox: result.bbox,
            })
          ),
        },
        pipeline_execution: {
          status: response.pipeline_status,
          error_message: response.pipeline_error,
          executed_actions: simulatedActions,
          steps: response.pipeline_steps.map((step) => {
            // Parse step error from "ErrorType: message" format to object
            let errorObj: { type: string; message: string } | null = null;
            if (step.error) {
              const colonIndex = step.error.indexOf(":");
              if (colonIndex > 0) {
                errorObj = {
                  type: step.error.substring(0, colonIndex).trim(),
                  message: step.error.substring(colonIndex + 1).trim(),
                };
              } else {
                errorObj = {
                  type: "Error",
                  message: step.error,
                };
              }
            }

            return {
              id: step.step_number,
              step_number: step.step_number,
              module_instance_id: step.module_instance_id,
              inputs: step.inputs,
              outputs: step.outputs,
              error: errorObj,
            };
          }),
        },
      };

      setTestResults(simulationResult);
      setCurrentStep("testing");
    } catch (error) {
      console.error("Failed to test template:", error);
      alert(
        `Template test failed: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    } finally {
      setIsTesting(false);
    }
  };

  const handleClose = () => {
    // Reset all state (PDF data is cached by React Query, no need to reset)
    setCurrentStep("signature-objects");
    setTemplateName("");
    setTemplateDescription("");
    setSignatureObjects({
      text_words: [],
      text_lines: [],
      graphic_rects: [],
      graphic_lines: [],
      graphic_curves: [],
      images: [],
      tables: [],
    });
    setSelectedObjectTypes([]);
    setExtractionFields([]);
    setPipelineStateInternal({
      entry_points: [],
      modules: [],
      connections: [],
    });
    setVisualStateInternal({});
    setTestResults(null);
    setPdfScale(1.0);
    setPdfCurrentPage(1);
    setUploadedPdfUrl(null);
    setUploadedPdfData(null);
    onClose();
  };

  const handleNext = () => {
    if (currentStep === "signature-objects") {
      setCurrentStep("extraction-fields");
    } else if (currentStep === "extraction-fields") {
      console.log(
        "[TemplateBuilderModal] Navigating to pipeline step. Passing state:",
        {
          pipelineState: {
            entryPoints: pipelineState.entry_points.length,
            modules: pipelineState.modules.length,
          },
          visualState: {
            totalNodes: Object.keys(visualState).length,
            entryPointPositions: Object.fromEntries(
              Object.entries(visualState).filter(([id]) =>
                id.startsWith("entry-")
              )
            ),
          },
        }
      );
      setCurrentStep("pipeline");
    }
  };

  const handleBack = () => {
    if (currentStep === "extraction-fields") {
      setCurrentStep("signature-objects");
    } else if (currentStep === "pipeline") {
      setCurrentStep("extraction-fields");
    } else if (currentStep === "testing") {
      // Clear test snapshots when leaving testing step
      setTestedPipelineState(null);
      setTestedVisualState(null);
      setTestResults(null);
      setCurrentStep("pipeline");
    }
  };

  // Early return after all hooks are defined
  if (!isOpen || (!pdfFileId && !pdfFile)) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-[95vw] h-[95vh] overflow-hidden flex flex-col shadow-2xl border border-gray-700">
        {/* Header */}
        <TemplateBuilderHeader
          pdfMetadata={activePdfData?.metadata ?? null}
          emailData={activePdfData?.emailData}
          onClose={handleClose}
        />

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Loading State - only show during initial load */}
          {!pdfDataLoaded && isPdfLoading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-white text-lg">
                {pdfFile ? "Processing PDF..." : "Loading PDF..."}
              </div>
            </div>
          )}

          {/* Error State */}
          {pdfError && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-red-400 mb-4">
                  {pdfError instanceof Error
                    ? pdfError.message
                    : "Failed to load PDF data"}
                </div>
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {/* Steps - conditionally render based on currentStep (components mount/unmount as needed) */}
          {pdfDataLoaded && !pdfError && (
            <>
              {currentStep === "signature-objects" && (
                <div style={{ height: "100%" }}>
                  <SignatureObjectsStep
                    pdfFileId={pdfFileId}
                    templateName={templateName}
                    templateDescription={templateDescription}
                    signatureObjects={signatureObjects}
                    selectedObjectTypes={selectedObjectTypes}
                    pdfObjects={pdfObjects}
                    pdfUrl={pdfUrl}
                    onTemplateNameChange={setTemplateName}
                    onTemplateDescriptionChange={setTemplateDescription}
                    onSignatureObjectsChange={setSignatureObjects}
                    onSelectedTypesChange={setSelectedObjectTypes}
                    pdfScale={pdfScale}
                    pdfCurrentPage={pdfCurrentPage}
                    onPdfScaleChange={setPdfScale}
                    onPdfCurrentPageChange={setPdfCurrentPage}
                  />
                </div>
              )}
              {currentStep === "extraction-fields" && (
                <div style={{ height: "100%" }}>
                  <ExtractionFieldsStep
                    pdfFileId={pdfFileId}
                    pdfFile={pdfFile}
                    templateName={templateName}
                    templateDescription={templateDescription}
                    extractionFields={extractionFields}
                    signatureObjects={signatureObjects}
                    pdfObjects={pdfObjects}
                    pdfUrl={pdfUrl}
                    pipelineState={pipelineState}
                    visualState={visualState}
                    onTemplateNameChange={setTemplateName}
                    onTemplateDescriptionChange={setTemplateDescription}
                    onExtractionFieldsChange={setExtractionFields}
                    onPipelineStateChange={setPipelineState}
                    pdfScale={pdfScale}
                    pdfCurrentPage={pdfCurrentPage}
                    onPdfScaleChange={setPdfScale}
                    onPdfCurrentPageChange={setPdfCurrentPage}
                  />
                </div>
              )}
              <div
                style={{
                  display: currentStep === "pipeline" ? "block" : "none",
                  height: "100%",
                }}
              >
                <PipelineBuilderStep
                  pipelineState={pipelineState}
                  visualState={visualState}
                  moduleTemplates={moduleTemplates}
                  onPipelineStateChange={setPipelineState}
                  onVisualStateChange={setVisualState}
                />
              </div>
              {currentStep === "testing" &&
                (testResults &&
                pdfUrl &&
                testedPipelineState &&
                testedVisualState ? (
                  <TestingStep
                    pdfUrl={pdfUrl}
                    viewMode={testViewMode}
                    simulationResult={testResults}
                    pipelineState={testedPipelineState}
                    visualState={testedVisualState}
                    moduleTemplates={moduleTemplates}
                  />
                ) : (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-gray-400">
                      No test results available
                    </div>
                  </div>
                ))}
            </>
          )}
        </div>

        {/* Footer - Stepper with Navigation Buttons */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-700 bg-gray-900">
          <div className="flex items-center space-x-4">
            <TemplateBuilderStepper
              currentStep={currentStep}
              completedSteps={completedSteps}
              testStatus={
                testResults?.status === "success"
                  ? "success"
                  : testResults?.status === "failure"
                    ? "failure"
                    : null
              }
            />

            {/* View Mode Toggle - Only show in testing step */}
            {currentStep === "testing" && testResults && (
              <div className="flex items-center bg-gray-800 rounded-lg p-1 border-l border-gray-600 ml-4">
                <button
                  onClick={() => setTestViewMode("summary")}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    testViewMode === "summary"
                      ? "bg-blue-600 text-white"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  Summary
                </button>
                <button
                  onClick={() => setTestViewMode("detail")}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    testViewMode === "detail"
                      ? "bg-blue-600 text-white"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  Detail
                </button>
              </div>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center space-x-3">
            {currentStep !== "signature-objects" && (
              <button
                onClick={handleBack}
                disabled={isSaving || isTesting}
                className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                ← Back
              </button>
            )}

            {currentStep === "pipeline" ? (
              <div className="relative group">
                <button
                  onClick={handleTest}
                  disabled={!canProceed || isTesting}
                  className="px-6 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
                >
                  {isTesting ? "Testing..." : "Test Template →"}
                </button>
                {/* Tooltip on hover when disabled */}
                {!canProceed && validationMessage && (
                  <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block z-10">
                    <div className="bg-gray-800 text-amber-400 text-xs px-3 py-2 rounded shadow-lg whitespace-nowrap border border-amber-400/30">
                      {validationMessage}
                      <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-800"></div>
                    </div>
                  </div>
                )}
              </div>
            ) : currentStep === "testing" ? (
              <button
                onClick={handleSave}
                disabled={!canProceed || isSaving}
                className="px-6 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
              >
                {isSaving
                  ? mode === "edit"
                    ? "Updating..."
                    : "Saving..."
                  : mode === "edit"
                    ? "Update Template"
                    : "Save Template"}
              </button>
            ) : (
              <div className="relative group">
                <button
                  onClick={handleNext}
                  disabled={!canProceed}
                  className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
                >
                  Next →
                </button>
                {/* Tooltip on hover when disabled */}
                {!canProceed && validationMessage && (
                  <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block z-10">
                    <div className="bg-gray-800 text-amber-400 text-xs px-3 py-2 rounded shadow-lg whitespace-nowrap border border-amber-400/30">
                      {validationMessage}
                      <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-800"></div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
