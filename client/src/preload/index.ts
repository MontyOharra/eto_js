import { contextBridge } from "electron";
import { ipcRendererInvoke } from "./ipcWrappers.js";

contextBridge.exposeInMainWorld("electron", {
  testDatabaseConnection: () => ipcRendererInvoke("testDatabaseConnection"),
  getPositions: () => ipcRendererInvoke("getPositions"),
} satisfies Window["electron"]);
