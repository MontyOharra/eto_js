import { position } from "../../prisma/generated/client/index";
import { DatabaseConfig } from "./database";

declare global {
  // Output payloads (responses from main process)
  type OutputPayloadMapping = {
    'file:select': { filePath: string; fileName: string } | null;
    'file:read': { content: string; filePath: string };
    'file:save': { success: boolean; filePath: string };
    'dialog:confirm': { confirmed: boolean };
  };

  // Input payloads (requests to main process)
  type InputPayloadMapping = {
    'file:select': {
      filters?: Array<{ name: string; extensions: string[] }>;
      title?: string;
    };
    'file:read': { filePath: string };
    'file:save': {
      content: string;
      defaultPath?: string;
      filters?: Array<{ name: string; extensions: string[] }>;
    };
    'dialog:confirm': {
      message: string;
      detail?: string;
      title?: string;
    };
  };

  interface Window {
    electron: {
      selectFile: (options?: InputPayloadMapping['file:select']) => Promise<OutputPayloadMapping['file:select']>;
      readFile: (filePath: string) => Promise<OutputPayloadMapping['file:read']>;
      saveFile: (content: string, options?: { defaultPath?: string; filters?: Array<{ name: string; extensions: string[] }> }) => Promise<OutputPayloadMapping['file:save']>;
      confirm: (message: string, options?: { detail?: string; title?: string }) => Promise<boolean>;
    };
  }
}
