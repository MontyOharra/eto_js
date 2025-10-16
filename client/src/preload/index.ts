import { contextBridge } from "electron";
import { ipcRendererInvoke } from "./ipcWrappers";

contextBridge.exposeInMainWorld("electron", {
  // File operations
  selectFile: (options) => ipcRendererInvoke('file:select', options || {}),

  readFile: (filePath) => ipcRendererInvoke('file:read', { filePath }),

  saveFile: (content, options = {}) =>
    ipcRendererInvoke('file:save', {
      content,
      defaultPath: options.defaultPath,
      filters: options.filters,
    }),

  // Dialog operations
  confirm: async (message, options = {}) => {
    const result = await ipcRendererInvoke('dialog:confirm', {
      message,
      detail: options.detail,
      title: options.title,
    });
    return result.confirmed;
  },
} satisfies Window["electron"]);
