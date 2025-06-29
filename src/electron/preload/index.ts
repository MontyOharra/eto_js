import { contextBridge } from "electron";
import { ipcRendererInvoke } from "./ipcWrappers.js";

contextBridge.exposeInMainWorld("electron", {
  pythonTest: (testType: string) => ipcRendererInvoke("pythonTest", testType),
} satisfies Window["electron"]);