import { dialog, BrowserWindow } from "electron";
import { readFile } from "fs/promises";
import { ipcMainHandle } from "./ipcWrappers.js";

/**
 * Register all IPC handlers for main process
 * Implements file operations and dialog interactions
 */
export function registerIpcHandlers(): void {
  // File selection dialog
  ipcMainHandle("file:select", async (payload) => {
    const result = await dialog.showOpenDialog({
      properties: payload?.properties || ["openFile"],
      filters: payload?.filters || [],
    });

    return {
      filePaths: result.filePaths,
      canceled: result.canceled,
    };
  });

  // Read file content
  ipcMainHandle("file:read", async (payload) => {
    try {
      const content = await readFile(payload.filePath, "utf-8");
      return {
        content,
      };
    } catch (error) {
      return {
        content: "",
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  });

  // Save file dialog
  ipcMainHandle("file:save", async (payload) => {
    const result = await dialog.showSaveDialog({
      defaultPath: payload?.defaultPath,
      filters: payload?.filters || [],
    });

    return {
      filePath: result.filePath || null,
      canceled: result.canceled,
    };
  });

  // Confirmation dialog
  ipcMainHandle("dialog:confirm", async (payload) => {
    const focusedWindow = BrowserWindow.getFocusedWindow();

    const result = await dialog.showMessageBox(
      focusedWindow || BrowserWindow.getAllWindows()[0],
      {
        type: "question",
        buttons: ["OK", "Cancel"],
        defaultId: 0,
        cancelId: 1,
        title: payload.title,
        message: payload.message,
        detail: payload.detail,
      }
    );

    return {
      response: result.response,
      confirmed: result.response === 0,
    };
  });

  console.log("[Main] IPC handlers registered successfully");
}
