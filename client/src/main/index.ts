import { app, BrowserWindow } from "electron";
import { pathToFileURL } from "url";
import fs from "fs/promises";
import {
  devServerPort,
  getPreloadPath,
  isDev,
  getUIPath,
} from "./helpers/utils.js";
import { ipcMainHandle } from "./helpers/ipcWrappers.js";
import { DataServiceFactory } from "./services/data-service-factory.js";
import { PrismaService } from "./database/prisma/prisma-client.js";
import { SecureConfigManager } from "./database/prisma/secure-config.js";

import { DatabaseConfig } from "../@types/database.js";
import { buildDatabaseUrl } from "./database/prisma/helpers.js";

(async () => {
  const defaultConfig = await SecureConfigManager.getConfig();
  process.env.DATABASE_URL = buildDatabaseUrl(defaultConfig);
})();

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

  // Database IPC handlers
  ipcMainHandle("testDatabaseConnection", async () => {
    const dataService = DataServiceFactory.createDataService();
    return await dataService.testConnection();
  });

  ipcMainHandle("getPositions", async () => {
    const dataService = DataServiceFactory.createDataService();
    return await dataService.getPositions();
  });

  ipcMainHandle("getDatabaseConfig", async () => {
    return await SecureConfigManager.getConfig();
  });

  ipcMainHandle("setDatabaseConfig", async (config: DatabaseConfig) => {
    try {
      await SecureConfigManager.setConfig(config);
      const success = await PrismaService.reconnectWithConfig(config);

      if (success) {
        await DataServiceFactory.cleanup();
        DataServiceFactory.resetInstance();

        return true;
      }

      return false;
    } catch (error) {
      console.error("Failed to set database configuration:", error);
      return false;
    }
  });

  // Send PDF file data to renderer as Uint8Array (safe for structured clone)
  ipcMainHandle("readPdfFile", async (filepath: string) => {
    try {
      const buf = await fs.readFile(filepath);
      // Return a fresh copy as Uint8Array to avoid detached ArrayBuffer issues
      return Uint8Array.from(buf);
    } catch (error) {
      console.error("Failed to read PDF file:", error);
      throw error;
    }
  });

  // Open a separate PDF viewer window
  ipcMainHandle("openPdfWindow", async (filePath: string) => {
    try {
      const encodedPath = encodeURIComponent(filePath);
      const viewerUrl = isDev()
        ? `http://localhost:${devServerPort}/#/pdf-view?file=${encodedPath}`
        : `${pathToFileURL(getUIPath()).toString()}#/pdf-view?file=${encodedPath}`;

      const viewerWindow = new BrowserWindow({
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
          preload: getPreloadPath(),
          // Disable the same-origin policy for this window so that the
          // React dev server (http://localhost) can fetch a file:// resource.
          // The main application window keeps webSecurity enabled.
          webSecurity: false,
        },
        title: "PDF Viewer",
        width: 1000,
        height: 800,
      });

      await viewerWindow.loadURL(viewerUrl);
      return true;
    } catch (error) {
      console.error("Failed to open PDF window:", error);
      return false;
    }
  });
});

// Clean up database connections on app quit
app.on("before-quit", async () => {
  await DataServiceFactory.cleanup();
  await PrismaService.disconnect();
});

for (const signal of ["SIGINT", "SIGTERM", "uncaughtException"]) {
  process.on(signal as NodeJS.Signals, async () => {
    await PrismaService.disconnect();
    process.exit(0);
  });
}
