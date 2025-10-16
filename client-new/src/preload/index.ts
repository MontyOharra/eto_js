import { contextBridge } from "electron";

/**
 * Preload script - exposes limited APIs to renderer process
 * Uses contextBridge for security (context isolation)
 */

contextBridge.exposeInMainWorld("electron", {} satisfies Window["electron"]);
