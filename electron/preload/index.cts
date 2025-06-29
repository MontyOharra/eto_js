const { contextBridge } = require("electron");
const { ipcInvoke } = require("./ipcWrappers.cjs");

contextBridge.exposeInMainWorld("electron", {
  pythonTest: () => ipcInvoke("pythonTest"),
} satisfies Window["electron"]);
