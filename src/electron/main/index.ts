import { app, BrowserWindow } from "electron";
import {
  devServerPort,
  getPreloadPath,
  isDev,
  getUIPath,
} from "./utils.js";
import { ipcMainHandle } from "./ipcWrappers.js";
import { executePythonScript } from "./python.js";

app.on("ready", () => {
  const mainWindow = new BrowserWindow({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: getPreloadPath(),
    },
    title: "ETO",
    width: 1200,
    height: 800,
  });

  if (isDev()) {
    mainWindow.loadURL(`http://localhost:${devServerPort}`);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(getUIPath());
  }
  ipcMainHandle("pythonTest", async (payload) => {
    const res = await executePythonScript("applications/test.py", payload);
    return { output: res };
  });
});
