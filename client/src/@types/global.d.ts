/**
 * Global type definitions for IPC communication
 */

declare global {
  // Output payloads (responses from main process to renderer)
  type OutputPayloadMapping = {
    'file:select': {
      filePaths: string[];
      canceled: boolean;
    };
    'file:read': {
      content: string;
      error?: string;
    };
    'file:save': {
      filePath: string | null;
      canceled: boolean;
    };
    'dialog:confirm': {
      response: number; // 0 = OK, 1 = Cancel
      confirmed: boolean;
    };
    'auth:getMachineInfo': {
      pcName: string;
      pcLid: string;
    };
  };

  // Input payloads (requests from renderer to main process)
  type InputPayloadMapping = {
    'file:select': {
      filters?: Array<{ name: string; extensions: string[] }>;
      properties?: Array<
        | 'openFile'
        | 'openDirectory'
        | 'multiSelections'
        | 'showHiddenFiles'
      >;
    };
    'file:read': {
      filePath: string;
    };
    'file:save': {
      defaultPath?: string;
      filters?: Array<{ name: string; extensions: string[] }>;
    };
    'dialog:confirm': {
      title: string;
      message: string;
      detail?: string;
    };
  };

  // Window API exposed to renderer via preload script
  interface Window {
    electron: {
      selectFile: (
        options?: InputPayloadMapping['file:select']
      ) => Promise<OutputPayloadMapping['file:select']>;
      readFile: (
        options: InputPayloadMapping['file:read']
      ) => Promise<OutputPayloadMapping['file:read']>;
      saveFile: (
        options?: InputPayloadMapping['file:save']
      ) => Promise<OutputPayloadMapping['file:save']>;
      confirmDialog: (
        options: InputPayloadMapping['dialog:confirm']
      ) => Promise<OutputPayloadMapping['dialog:confirm']>;
      getMachineInfo: () => Promise<OutputPayloadMapping['auth:getMachineInfo']>;
    };
  }
}

export {};
