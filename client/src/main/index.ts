import { app, BrowserWindow } from "electron";
import { pathToFileURL } from "url";
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
  const initConfig = await SecureConfigManager.getConfig();
  process.env.DATABASE_URL = buildDatabaseUrl(initConfig);
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
    console.log("dev");
  } else {
    mainWindow.loadFile(getUIPath());
    console.log("prod");
  }

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
