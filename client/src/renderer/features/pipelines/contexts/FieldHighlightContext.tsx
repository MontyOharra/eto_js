/**
 * FieldHighlightContext
 * Shared hover state between extraction fields on PDF and pipeline entry points
 * When a field is hovered on one side, it highlights on the other side
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface FieldHighlightContextType {
  /** Currently highlighted field name (null if none) */
  highlightedFieldName: string | null;
  /** Set the highlighted field name */
  setHighlightedFieldName: (name: string | null) => void;
}

const FieldHighlightContext = createContext<FieldHighlightContextType | null>(null);

interface FieldHighlightProviderProps {
  children: ReactNode;
}

export function FieldHighlightProvider({ children }: FieldHighlightProviderProps) {
  const [highlightedFieldName, setHighlightedFieldNameState] = useState<string | null>(null);

  const setHighlightedFieldName = useCallback((name: string | null) => {
    setHighlightedFieldNameState(name);
  }, []);

  return (
    <FieldHighlightContext.Provider value={{ highlightedFieldName, setHighlightedFieldName }}>
      {children}
    </FieldHighlightContext.Provider>
  );
}

/**
 * Hook to access the field highlight context
 * Returns null if used outside of a FieldHighlightProvider (for optional usage)
 */
export function useFieldHighlight(): FieldHighlightContextType | null {
  return useContext(FieldHighlightContext);
}

/**
 * Hook to access the field highlight context (throws if not in provider)
 * Use this when the context is required
 */
export function useFieldHighlightRequired(): FieldHighlightContextType {
  const context = useContext(FieldHighlightContext);
  if (!context) {
    throw new Error('useFieldHighlightRequired must be used within a FieldHighlightProvider');
  }
  return context;
}
