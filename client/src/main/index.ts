import { app, BrowserWindow } from "electron";
import {
  devServerPort,
  getPreloadPath,
  isDev,
  getUIPath,
} from "./helpers/utils.js";
import { ipcMainHandle } from "./helpers/ipcWrappers.js";
import { DataServiceFactory } from "./services/data-service-factory.js";

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
});




// Clean up database connections on app quit
app.on("before-quit", async () => {
  await DataServiceFactory.cleanup();
});
