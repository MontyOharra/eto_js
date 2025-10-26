/**
 * ExecutePipelineModal
 * Modal for executing a pipeline with entry point values
 */

import { useState, useEffect } from 'react';
import { usePipelinesApi } from '../../hooks/usePipelinesApi';
import type { EntryPoint } from '../../../../types/pipelineTypes';

interface ExecutePipelineModalProps {
  isOpen: boolean;
  pipelineId: number | null;
  entryPoints: EntryPoint[];
  onClose: () => void;
}

interface ExecutionResult {
  status: string;
  steps: Array<{
    module_instance_id: string;
    step_number: number;
    inputs: Record<string, { value: any; type: string }>;
    outputs: Record<string, { value: any; type: string }>;
    error: string | null;
  }>;
  executed_actions: Record<string, Record<string, any>>;
  error: string | null;
}

export function ExecutePipelineModal({
  isOpen,
  pipelineId,
  entryPoints,
  onClose,
}: ExecutePipelineModalProps) {
  const { executePipeline } = usePipelinesApi();

  const [entryValues, setEntryValues] = useState<Record<string, string>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Initialize entry values when modal opens
  useEffect(() => {
    if (isOpen) {
      const initialValues: Record<string, string> = {};
      entryPoints.forEach(ep => {
        initialValues[ep.name] = '';
      });
      setEntryValues(initialValues);
      setResult(null);
      setError(null);
    }
  }, [isOpen, entryPoints]);

  const handleValueChange = (name: string, value: string) => {
    setEntryValues(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleExecute = async () => {
    if (!pipelineId) return;

    // Validate all entry points have values
    const missingEntries = entryPoints.filter(ep => !entryValues[ep.name]?.trim());
    if (missingEntries.length > 0) {
      setError(`Please provide values for: ${missingEntries.map(ep => ep.name).join(', ')}`);
      return;
    }

    setIsExecuting(true);
    setError(null);
    setResult(null);

    try {
      const executionResult = await executePipeline(pipelineId, entryValues);
      setResult(executionResult);
    } catch (err) {
      console.error('Pipeline execution failed:', err);
      setError(err instanceof Error ? err.message : 'Pipeline execution failed');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleClose = () => {
    setEntryValues({});
    setResult(null);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-75">
      <div className="bg-gray-900 rounded-lg shadow-xl w-[90vw] max-w-4xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-white">
              Execute Pipeline #{pipelineId}
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              Provide entry point values to test pipeline execution
            </p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {!result && (
            <>
              {/* Entry Point Inputs */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white mb-4">Entry Point Values</h3>
                <div className="space-y-4">
                  {entryPoints.map(ep => (
                    <div key={ep.node_id}>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        {ep.name}
                        <span className="text-gray-500 ml-2">({ep.type})</span>
                      </label>
                      <input
                        type="text"
                        value={entryValues[ep.name] || ''}
                        onChange={(e) => handleValueChange(ep.name, e.target.value)}
                        placeholder={`Enter value for ${ep.name}`}
                        className="w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
                        disabled={isExecuting}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="mb-4 bg-red-900 border border-red-700 rounded-lg p-4">
                  <p className="text-red-200">{error}</p>
                </div>
              )}

              {/* Execute Button */}
              <div className="flex justify-end gap-3">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
                  disabled={isExecuting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleExecute}
                  disabled={isExecuting}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isExecuting ? 'Executing...' : 'Execute Pipeline'}
                </button>
              </div>
            </>
          )}

          {/* Execution Results */}
          {result && (
            <div className="space-y-6">
              {/* Status */}
              <div className={`p-4 rounded-lg ${
                result.status === 'success'
                  ? 'bg-green-900 border border-green-700'
                  : 'bg-red-900 border border-red-700'
              }`}>
                <h3 className="text-lg font-bold mb-2">
                  {result.status === 'success' ? '✅ Execution Succeeded' : '❌ Execution Failed'}
                </h3>
                {result.error && (
                  <p className="text-sm text-red-200">{result.error}</p>
                )}
              </div>

              {/* Steps */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">Execution Steps</h3>
                <div className="space-y-4">
                  {result.steps.map((step, index) => (
                    <div
                      key={step.module_instance_id}
                      className={`p-4 rounded-lg border ${
                        step.error
                          ? 'bg-red-900 border-red-700'
                          : 'bg-gray-800 border-gray-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium text-white">
                          Step {step.step_number + 1}: {step.module_instance_id}
                        </h4>
                        {step.error && (
                          <span className="text-xs text-red-300 font-medium">ERROR</span>
                        )}
                      </div>

                      {step.error && (
                        <div className="mb-3 text-sm text-red-200">
                          {step.error}
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        {/* Inputs */}
                        <div>
                          <p className="text-gray-400 mb-2">Inputs:</p>
                          <div className="bg-gray-900 rounded p-2 max-h-32 overflow-y-auto">
                            <pre className="text-xs text-gray-300">
                              {JSON.stringify(step.inputs, null, 2)}
                            </pre>
                          </div>
                        </div>

                        {/* Outputs */}
                        <div>
                          <p className="text-gray-400 mb-2">Outputs:</p>
                          <div className="bg-gray-900 rounded p-2 max-h-32 overflow-y-auto">
                            <pre className="text-xs text-gray-300">
                              {JSON.stringify(step.outputs, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Executed Actions */}
              {Object.keys(result.executed_actions).length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Actions (Not Executed - Simulation)</h3>
                  <div className="space-y-3">
                    {Object.entries(result.executed_actions).map(([moduleId, inputs]) => (
                      <div key={moduleId} className="p-4 bg-purple-900 border border-purple-700 rounded-lg">
                        <h4 className="font-medium text-white mb-2">{moduleId}</h4>
                        <div className="bg-gray-900 rounded p-2">
                          <pre className="text-xs text-gray-300">
                            {JSON.stringify(inputs, null, 2)}
                          </pre>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Close Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
