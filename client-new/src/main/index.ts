import { app, BrowserWindow } from "electron";
import {
  devServerPort,
  getPreloadPath,
  isDev,
  getUIPath,
} from "./helpers/utils.js";
import { registerIpcHandlers } from "./helpers/ipcHandlers.js";

app.on("ready", () => {
  // Register IPC handlers before creating windows
  registerIpcHandlers();
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

  // When the main window is closed, close any remaining windows then quit.
  mainWindow.on("closed", () => {
    // Close any additional windows that might still be open
    for (const win of BrowserWindow.getAllWindows()) {
      if (!win.isDestroyed()) {
        win.close();
      }
    }

    // On non-macOS platforms quit the application entirely.
    // (macOS usually keeps the app menu alive, adapt if desired.)
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
});
