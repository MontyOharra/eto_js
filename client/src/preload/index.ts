import { contextBridge } from "electron";
import { ipcRendererInvoke } from "./ipcWrappers.js";
import { DatabaseConfig } from "../@types/database.js";

contextBridge.exposeInMainWorld("electron", {
  testDatabaseConnection: () => ipcRendererInvoke("testDatabaseConnection"),
  getPositions: () => ipcRendererInvoke("getPositions"),
  getDatabaseConfig: () => ipcRendererInvoke("getDatabaseConfig"),
  setDatabaseConfig: (config: DatabaseConfig) =>
    ipcRendererInvoke("setDatabaseConfig", config),
} satisfies Window["electron"]);
