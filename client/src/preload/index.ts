import { contextBridge } from "electron";
import { ipcRendererInvoke } from "./ipcWrappers.js";

contextBridge.exposeInMainWorld("electron", {
  testDatabaseConnection: () => ipcRendererInvoke("testDatabaseConnection"),
  getPositions: () => ipcRendererInvoke("getPositions"),
  test: () => ipcRendererInvoke("test"),
} satisfies Window["electron"]);
