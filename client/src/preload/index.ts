import { contextBridge } from "electron";
import { ipcRendererInvoke } from "./ipcWrappers.js";
import { DatabaseConfig } from "../@types/types";

contextBridge.exposeInMainWorld("electron", {
  testDatabaseConnection: () => ipcRendererInvoke("testDatabaseConnection"),
  getPositions: () => ipcRendererInvoke("getPositions"),
  loadDatabaseConfig: () => ipcRendererInvoke("loadDatabaseConfig"),
  updateDatabaseConfig: (config: DatabaseConfig) =>
    ipcRendererInvoke("updateDatabaseConfig", config),
} satisfies Window["electron"]);
