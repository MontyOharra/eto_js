/**
 * Pipeline Validation Hook
 * Auto-validates pipeline state with debouncing
 */

import { useState, useEffect } from 'react';
import { usePipelinesApi } from './usePipelinesApi';
import type { PipelineState } from '../../../types/pipelineTypes';

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
      return;
    }

    // Debounce: wait for user to stop making changes before validating
    const timer = setTimeout(async () => {
      setIsValidating(true);

      try {
        const result = await validatePipeline({
          pipeline_json: pipelineState,
        });

        setIsValid(result.valid);
        setError(result.error || null);

        // Log validation errors to console
        if (!result.valid && result.error) {
          console.error(`${result.error.code}: ${result.error.message}`);
        }
      } catch (err) {
        console.error('Validation request failed:', err);
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

    return () => clearTimeout(timer);
  }, [pipelineState, validatePipeline, debounceMs]);

  return { isValid, error, isValidating };
}
