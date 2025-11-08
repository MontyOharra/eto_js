/**
 * Pipeline Builder Modal
 * 2-step wizard for creating pipelines:
 * 1. Entry Points: Define pipeline entry points
 * 2. Pipeline Builder: Build the transformation pipeline
 */

import { useState, useCallback } from "react";
import { generateEntryPointId } from "../../utils/idGenerator";
import { PipelineEditor } from "../PipelineEditor";
import type {
  EntryPoint,
  PipelineState,
  VisualState,
} from "../../types";

interface PipelineBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (pipelineData: PipelineData) => Promise<void>;
}

export interface PipelineData {
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

type BuilderStep = "entry-points" | "pipeline";

export function PipelineBuilderModal({
  isOpen,
  onClose,
  onSave,
}: PipelineBuilderModalProps) {
  const [currentStep, setCurrentStep] = useState<BuilderStep>("entry-points");

  // Pipeline state
  const [pipelineState, setPipelineState] = useState<PipelineState>({
    entry_points: [],
    modules: [],
    connections: [],
  });

  // Visual state - node positions
  const [visualState, setVisualState] = useState<VisualState>({});

  // Handle entry points from step 1
  const handleEntryPointsConfirm = useCallback((points: Array<{ name: string }>) => {
    const newEntryPoints: EntryPoint[] = points.map((p) => {
      const entryPointId = generateEntryPointId();
      return {
        entry_point_id: entryPointId,
        name: p.name,
        outputs: [
          {
            node_id: `${entryPointId}_out`,
            direction: 'out' as const,
            type: 'str',
            name: p.name,
            label: 'Output',
            position_index: 0,
            group_index: 0,
            allowed_types: ['str', 'int', 'float', 'bool', 'date', 'datetime'],
          },
        ],
      };
    });

    setPipelineState((prev) => ({
      ...prev,
      entry_points: newEntryPoints,
    }));

    // Move to pipeline builder step
    setCurrentStep("pipeline");
  }, []);

  const handleBack = () => {
    if (currentStep === "pipeline") {
      setCurrentStep("entry-points");
    }
  };

  const handleSave = async () => {
    const data: PipelineData = {
      pipeline_state: pipelineState,
      visual_state: visualState,
    };

    await onSave(data);
  };

  const handleCancel = () => {
    // Reset state
    setPipelineState({
      entry_points: [],
      modules: [],
      connections: [],
    });
    setVisualState({});
    setCurrentStep("entry-points");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-gray-800 rounded-lg shadow-xl w-[95vw] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-gray-900 px-6 py-4 border-b border-gray-700 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">Create Pipeline</h2>
              <p className="text-sm text-gray-400 mt-1">
                {currentStep === "entry-points"
                  ? "Step 1: Define entry points"
                  : "Step 2: Build transformation pipeline"}
              </p>
            </div>
            <button
              onClick={handleCancel}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Step indicator */}
          <div className="flex items-center gap-2 mt-4">
            <div className={`px-3 py-1 rounded text-sm font-medium ${
              currentStep === "entry-points"
                ? "bg-blue-600 text-white"
                : "bg-gray-700 text-gray-300"
            }`}>
              1. Entry Points
            </div>
            <div className="w-8 h-0.5 bg-gray-700" />
            <div className={`px-3 py-1 rounded text-sm font-medium ${
              currentStep === "pipeline"
                ? "bg-blue-600 text-white"
                : "bg-gray-700 text-gray-300"
            }`}>
              2. Pipeline Builder
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {currentStep === "entry-points" && (
            <EntryPointsStep
              onConfirm={handleEntryPointsConfirm}
              onCancel={handleCancel}
            />
          )}

          {currentStep === "pipeline" && (
            <PipelineEditor
              pipelineState={pipelineState}
              visualState={visualState}
              onPipelineStateChange={setPipelineState}
              onVisualStateChange={setVisualState}
            />
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-900 px-6 py-4 border-t border-gray-700 rounded-b-lg flex items-center justify-between">
          {/* Cancel on the left */}
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-md transition-colors"
          >
            Cancel
          </button>

          {/* Back and Next/Save on the right */}
          <div className="flex gap-2">
            {currentStep === "pipeline" && (
              <button
                onClick={handleBack}
                className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-md transition-colors"
              >
                Back
              </button>
            )}

            {currentStep === "entry-points" ? (
              <button
                onClick={() => document.getElementById('entry-points-next')?.click()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSave}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
              >
                Save Pipeline
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Step components
function EntryPointsStep({
  onConfirm,
  onCancel,
}: {
  onConfirm: (points: Array<{ name: string }>) => void;
  onCancel: () => void;
}) {
  const [entryPoints, setEntryPoints] = useState<Array<{ id: string; name: string }>>([
    { id: crypto.randomUUID(), name: '' }
  ]);

  const handleAddEntryPoint = () => {
    setEntryPoints([...entryPoints, { id: crypto.randomUUID(), name: '' }]);
  };

  const handleRemoveEntryPoint = (id: string) => {
    if (entryPoints.length === 1) return; // Keep at least one
    setEntryPoints(entryPoints.filter(ep => ep.id !== id));
  };

  const handleNameChange = (id: string, name: string) => {
    setEntryPoints(entryPoints.map(ep =>
      ep.id === id ? { ...ep, name } : ep
    ));
  };

  const handleNext = () => {
    // Filter out empty names and confirm
    const validEntryPoints = entryPoints.filter(ep => ep.name.trim() !== '');
    if (validEntryPoints.length === 0) {
      alert('Please provide at least one entry point name');
      return;
    }
    onConfirm(validEntryPoints);
  };

  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="w-full max-w-2xl">
        <h3 className="text-2xl font-bold text-white mb-2">Define Entry Points</h3>
        <p className="text-sm text-gray-400 mb-6">
          Entry points are the starting inputs for your pipeline. Each entry point will output a string value.
        </p>

        <div className="space-y-3 mb-6">
          {entryPoints.map((ep, index) => (
            <div key={ep.id} className="flex items-center gap-2">
              <input
                type="text"
                value={ep.name}
                onChange={(e) => handleNameChange(ep.id, e.target.value)}
                placeholder="Entry point name"
                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-200 text-sm focus:outline-none focus:border-blue-500"
                autoFocus={index === 0}
              />
              <button
                onClick={() => handleRemoveEntryPoint(ep.id)}
                disabled={entryPoints.length === 1}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-gray-300 rounded transition-colors"
                title="Remove entry point"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>

        <button
          onClick={handleAddEntryPoint}
          className="w-full mb-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Entry Point
        </button>

        {/* Hidden next button - actual navigation is in footer */}
        <button
          onClick={handleNext}
          id="entry-points-next"
          className="hidden"
        />
      </div>
    </div>
  );
}

