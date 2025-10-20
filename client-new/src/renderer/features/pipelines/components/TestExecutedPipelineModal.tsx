/**
 * TestExecutedPipelineModal
 * Modal for testing the ExecutedPipelineViewer component
 * Used in the pipelines page "Test Executed Pipeline View" button
 */

import { ExecutedPipelineViewer } from './ExecutedPipelineViewer';
import { mockPipelineExecutionData } from '../mocks/pipelineDefinitionMock';

interface TestExecutedPipelineModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function TestExecutedPipelineModal({ isOpen, onClose }: TestExecutedPipelineModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-[95vw] h-[95vh] overflow-hidden border border-gray-700 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
          <div>
            <h2 className="text-xl font-semibold text-white">Executed Pipeline Viewer Test</h2>
            <p className="text-sm text-gray-400 mt-1">
              Testing pipeline visualization with execution data overlay
            </p>
          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Pipeline Viewer */}
        <div className="flex-1 overflow-hidden">
          <ExecutedPipelineViewer
            pipelineDefinitionId={1}
            executionData={{
              steps: mockPipelineExecutionData.steps,
              executed_actions: mockPipelineExecutionData.executed_actions,
            }}
          />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-700 flex-shrink-0">
          <div className="text-sm text-gray-400">
            <span className="font-semibold">Pipeline ID:</span> 1 |{' '}
            <span className="font-semibold">Execution Steps:</span> {mockPipelineExecutionData.steps.length} |{' '}
            <span className="font-semibold">Actions:</span> {mockPipelineExecutionData.executed_actions.length}
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-800 transition-colors text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
