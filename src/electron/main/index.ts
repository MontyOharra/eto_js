import { app, BrowserWindow } from "electron";
import path from "path";
import { devServerPort, getPreloadPath, isDev } from "../utils.js";
import { ipcMainHandle } from "./ipcWrappers.js";
import { spawn } from "child_process";

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

    // Suppress DevTools console errors
    mainWindow.webContents.on("console-message", (event, level, message) => {
      if (message.includes("Autofill")) return; // Filter out autofill errors
      console.log("DevTools:", message);
    });
  } else {
    mainWindow.loadFile(
      path.join(app.getAppPath(), "/build/dist-react/index.html")
    );
  }

  ipcMainHandle("pythonTest", async () => {
    const pythonPromise = new Promise<PythonTestReturn>((resolve, reject) => {
      let outputData = "";
      let errorData = "";

      const pythonProcess = spawn("python", ["src/python/test.py", "test"]);

      pythonProcess.stdout.on("data", (data) => {
        outputData += data.toString();
      });
      pythonProcess.stderr.on("data", (data) => {
        errorData += data.toString();
      });

      pythonProcess.on("close", (code) => {
        if (code === 0) {
          resolve({ output: outputData.trim() });
        } else {
          reject(
            new Error(`Python script failed with code ${code}: ${errorData}`)
          );
        }
      });
      pythonProcess.on("error", (error) => {
        reject(new Error(`Failed to start Python process: ${error.message}`));
      });
    });

    const pythonReturnValue = await pythonPromise;
    return pythonReturnValue;
  });
});
