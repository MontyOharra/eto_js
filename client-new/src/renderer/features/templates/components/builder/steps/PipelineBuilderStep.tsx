import { useCallback, useState, useEffect, useMemo } from 'react';
import { PipelineState, VisualState, ExtractionField } from '../../../types';
import { PipelineGraph } from './PipelineBuilderStep/PipelineGraph';
import type { ModuleTemplate } from '../../../../types/moduleTypes';
import type { EntryPoint } from '../../../../types/pipelineTypes';

interface PipelineBuilderStepProps {
  extractionFields: ExtractionField[];
  pipelineState: PipelineState;
  visualState: VisualState;
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

export function PipelineBuilderStep({
  extractionFields,
  pipelineState,
  visualState,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineBuilderStepProps) {
  const [modules, setModules] = useState<ModuleTemplate[]>([]);
  const [isLoadingModules, setIsLoadingModules] = useState(true);

  // Convert extraction fields to entry points
  const entryPoints: EntryPoint[] = useMemo(() => {
    return extractionFields.map((field) => ({
      node_id: `entry_${field.field_id}`,
      name: field.label,
      type: 'str', // Extraction fields always output strings
    }));
  }, [extractionFields]);

  // Update entry point positions when new fields are added
  useEffect(() => {
    const newPositions = { ...visualState.positions };
    let hasNewPositions = false;

    entryPoints.forEach((ep, index) => {
      if (!newPositions[ep.node_id]) {
        // Position entry points vertically on the left side
        newPositions[ep.node_id] = { x: 50, y: 50 + index * 120 };
        hasNewPositions = true;
      }
    });

    if (hasNewPositions) {
      onVisualStateChange({ positions: newPositions });
    }
  }, [entryPoints, visualState.positions, onVisualStateChange]);

  // Load modules from API
  useEffect(() => {
    const fetchModules = async () => {
      try {
        setIsLoadingModules(true);
        const response = await fetch('http://localhost:8000/api/modules');
        const data = await response.json();
        setModules(data.modules || []);
      } catch (error) {
        console.error('Failed to load modules:', error);
        setModules([]);
      } finally {
        setIsLoadingModules(false);
      }
    };

    fetchModules();
  }, []);

  // Handle state changes from PipelineGraph
  const handleStateChange = useCallback((state: {
    moduleInstances: any[];
    entryPoints: any[];
    connections: any[];
    positions: Record<string, { x: number; y: number }>;
  }) => {
    onPipelineStateChange({
      entry_points: state.entryPoints,
      modules: state.moduleInstances,
      connections: state.connections,
    });

    onVisualStateChange({
      positions: state.positions,
    });
  }, [onPipelineStateChange, onVisualStateChange]);

  if (isLoadingModules) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-white text-lg mb-2">Loading modules...</div>
          <div className="text-gray-400 text-sm">Please wait</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <PipelineGraph
        modules={modules}
        initialModuleInstances={pipelineState.modules}
        initialEntryPoints={entryPoints}
        initialConnections={pipelineState.connections}
        initialPositions={visualState.positions}
        onStateChange={handleStateChange}
      />
    </div>
  );
}
