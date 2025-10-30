/**
 * Pipeline Validation Hook
 * Auto-validates pipeline state with debouncing
 */

import { useState, useEffect } from 'react';
import { usePipelinesApi } from './usePipelinesApi';
import type { PipelineState } from '../types';

interface ValidationError {
  code: string;
  message: string;
  where?: Record<string, any> | null;
}

interface ValidationResult {
  isValid: boolean;
  error: ValidationError | null;
  isValidating: boolean;
}

/**
 * Auto-validates pipeline state whenever it changes
 * Debounces validation calls to avoid excessive API requests
 *
 * @param pipelineState - Current pipeline state to validate (null if not ready)
 * @param debounceMs - Debounce delay in milliseconds (default: 500ms)
 * @returns Validation result with isValid flag and error details
 */
export function usePipelineValidation(
  pipelineState: PipelineState | null,
  debounceMs: number = 500
): ValidationResult {
  const [isValid, setIsValid] = useState(true);
  const [error, setError] = useState<ValidationError | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const { validatePipeline } = usePipelinesApi();

  useEffect(() => {
    // Skip validation if no pipeline state yet
    if (!pipelineState) {
      console.log('[usePipelineValidation] Skipping - no pipeline state');
      return;
    }

    // Empty pipelines (only entry points, no modules) are invalid
    if (pipelineState.modules.length === 0) {
      console.log('[usePipelineValidation] Empty pipeline - setting invalid');
      setIsValid(false);
      setError({
        code: 'empty_pipeline',
        message: 'Pipeline must contain at least one module'
      });
      return;
    }

    console.log('[usePipelineValidation] State changed, starting debounce timer', {
      pipelineState,
      debounceMs
    });

    // Debounce: wait for user to stop making changes before validating
    const timer = setTimeout(async () => {
      console.log('[usePipelineValidation] Debounce complete, calling API');
      setIsValidating(true);

      try {
        const result = await validatePipeline({
          pipeline_json: pipelineState,
        });

        console.log('[usePipelineValidation] Result:', result);
        setIsValid(result.valid);
        setError(result.error || null);

        // Log validation errors to console
        if (!result.valid && result.error) {
          console.error(`[usePipelineValidation] Validation failed: ${result.error.code}: ${result.error.message}`);
        }
      } catch (err) {
        console.error('[usePipelineValidation] API request failed:', err);
        // On API error, assume invalid for safety
        setIsValid(false);
        setError({
          code: 'validation_failed',
          message: 'Failed to validate pipeline',
        });
      } finally {
        setIsValidating(false);
      }
    }, debounceMs);

    return () => {
      console.log('[usePipelineValidation] Debounce timer cancelled');
      clearTimeout(timer);
    };
  }, [pipelineState, validatePipeline, debounceMs]);

  return { isValid, error, isValidating };
}
