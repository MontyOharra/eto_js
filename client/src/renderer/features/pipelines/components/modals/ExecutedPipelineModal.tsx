/**
 * ExecutedPipelineModal
 * Modal for viewing executed pipeline results
 */

import { useEffect, useState } from 'react';
import { ExecutedPipelineViewer } from '../ExecutedPipelineViewer';
import { usePipelinesApi } from '../../api';
import type { PipelineState, VisualState } from '../../types';

interface ExecutedPipelineModalProps {
  isOpen: boolean;
  onClose: () => void;
  pipelineId: number | null;
}

export function ExecutedPipelineModal({
  isOpen,
  onClose,
  pipelineId,
}: ExecutedPipelineModalProps) {
  const { getPipeline } = usePipelinesApi();
  const [pipelineState, setPipelineState] = useState<PipelineState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch pipeline data when modal opens
  useEffect(() => {
    if (!isOpen || !pipelineId) {
      setPipelineState(null);
      setError(null);
      return;
    }

    async function loadPipeline() {
      setIsLoading(true);
      setError(null);

      try {
        const pipeline = await getPipeline(pipelineId);
        setPipelineState(pipeline.pipeline_state);
      } catch (err) {
        console.error('Failed to load pipeline:', err);
        setError(err instanceof Error ? err.message : 'Failed to load pipeline');
      } finally {
        setIsLoading(false);
      }
    }

    loadPipeline();
  }, [isOpen, pipelineId, getPipeline]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div className="relative bg-gray-800 rounded-lg shadow-xl w-[95vw] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">
            Executed Pipeline {pipelineId ? `#${pipelineId}` : ''}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body - Viewer Component */}
        <div className="flex-1 overflow-hidden">
          {isLoading && (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-gray-400">Loading pipeline...</div>
            </div>
          )}

          {error && (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-red-400">Error: {error}</div>
            </div>
          )}

          {!isLoading && !error && (
            <ExecutedPipelineViewer
              pipelineId={pipelineId}
              pipelineState={pipelineState || undefined}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
