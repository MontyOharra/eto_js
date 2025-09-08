/**
 * Type definitions for input/output definers in custom modules
 */

export type IODataType = 'string' | 'number' | 'boolean' | 'datetime';

export interface InputDefiner {
  id: string;
  name: string;
  description: string;
  type: IODataType;
  required: boolean;
  defaultValue?: unknown;
  position: { x: number; y: number };
}

export interface OutputDefiner {
  id: string;
  name: string;
  description: string;
  type: IODataType;
  position: { x: number; y: number };
}

export interface IODefinerTemplate {
  id: string;
  name: string;
  type: 'input' | 'output';
  color: string;
  icon: string;
}