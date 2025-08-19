import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("electron", {} satisfies Window["electron"]);
