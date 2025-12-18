import { contextBridge } from "electron";
import { ipcRendererInvoke } from "./ipcWrappers";

/**
 * Preload script - exposes limited APIs to renderer process
 * Uses contextBridge for security (context isolation)
 */

contextBridge.exposeInMainWorld(
  "electron",
  {
    selectFile: (options) => ipcRendererInvoke("file:select", options),
    readFile: (options) => ipcRendererInvoke("file:read", options),
    saveFile: (options) => ipcRendererInvoke("file:save", options),
    confirmDialog: (options) => ipcRendererInvoke("dialog:confirm", options),
    getMachineInfo: () => ipcRendererInvoke("auth:getMachineInfo", {}),
  } satisfies Window["electron"]
);
