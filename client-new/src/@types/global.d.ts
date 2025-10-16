/**
 * Global type definitions for IPC communication
 */

declare global {
  // Output payloads (responses from main process to renderer)
  type OutputPayloadMapping = {};

  // Input payloads (requests from renderer to main process)
  type InputPayloadMapping = {};

  // Window API exposed to renderer via preload script
  interface Window {
    electron: {};
  }
}

export {};
