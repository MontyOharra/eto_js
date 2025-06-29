const { contextBridge } = require("electron");
const { ipcInvoke } = require("./ipcWrappers.cts");

contextBridge.exposeInMainWorld("electron", {
  pythonTest: () => ipcInvoke("pythonTest"),
} satisfies Window["electron"]);
