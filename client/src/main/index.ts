import { app, BrowserWindow } from "electron";
import {
  devServerPort,
  getPreloadPath,
  isDev,
  getUIPath,
} from "./helpers/utils.js";
import { ipcMainHandle } from "./helpers/ipcWrappers.js";
import { DataServiceFactory } from "./services/data-service-factory.js";
import {
  PrismaService,
  type DatabaseConfig,
} from "./database/prisma-client.js";
import { SecureConfigManager } from "./database/secure-config.js";

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

  ipcMainHandle("loadDatabaseConfig", async () => {
    return await SecureConfigManager.loadConfig();
  });

  ipcMainHandle("updateDatabaseConfig", async (config: DatabaseConfig) => {
    try {
      // Reconnect with new configuration
      const success = await PrismaService.reconnectWithConfig(config);

      if (success) {
        // Reset the data service factory to use new connection
        await DataServiceFactory.cleanup();
        DataServiceFactory.resetInstance();

        // Test the new connection
        const dataService = DataServiceFactory.createDataService();
        const testResult = await dataService.testConnection();

        return testResult;
      }

      return false;
    } catch (error) {
      console.error("Failed to update database configuration:", error);
      return false;
    }
  });
});

// Clean up database connections on app quit
app.on("before-quit", async () => {
  await DataServiceFactory.cleanup();
});
