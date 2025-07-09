import { contextBridge } from "electron";
import { ipcRendererInvoke } from "./ipcWrappers.js";
import { webUtils } from "electron";
import { DatabaseConfig } from "../@types/database.js";

contextBridge.exposeInMainWorld("electron", {
  testDatabaseConnection: () => ipcRendererInvoke("testDatabaseConnection"),
  getPositions: () => ipcRendererInvoke("getPositions"),
  getDatabaseConfig: () => ipcRendererInvoke("getDatabaseConfig"),
  setDatabaseConfig: (config: DatabaseConfig) =>
    ipcRendererInvoke("setDatabaseConfig", config),
  openPdfWindow: (filePath: string) =>
    ipcRendererInvoke("openPdfWindow", filePath),
  getFilePath: (file: File) => webUtils.getPathForFile(file),
  readPdfFile: (filePath: string) => ipcRendererInvoke("readPdfFile", filePath),
} satisfies Window["electron"]);
