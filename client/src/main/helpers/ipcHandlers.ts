import { dialog } from 'electron';
import { readFile, writeFile } from 'fs/promises';
import { ipcMainHandle } from './ipcWrappers';

/**
 * Register all IPC handlers for the main process
 * Uses type-safe wrappers from ipcWrappers.ts
 */
export function registerIpcHandlers() {
  // File selection dialog
  ipcMainHandle('file:select', async (payload) => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: payload.filters || [],
      title: payload.title,
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    const filePath = result.filePaths[0];
    const fileName = filePath.split(/[\\/]/).pop() || '';

    return { filePath, fileName };
  });

  // Read file content
  ipcMainHandle('file:read', async (payload) => {
    const content = await readFile(payload.filePath, 'utf-8');
    return {
      content,
      filePath: payload.filePath,
    };
  });

  // Save file with dialog
  ipcMainHandle('file:save', async (payload) => {
    const result = await dialog.showSaveDialog({
      defaultPath: payload.defaultPath,
      filters: payload.filters || [],
    });

    if (result.canceled || !result.filePath) {
      return { success: false, filePath: '' };
    }

    await writeFile(result.filePath, payload.content, 'utf-8');

    return {
      success: true,
      filePath: result.filePath,
    };
  });

  // Confirmation dialog
  ipcMainHandle('dialog:confirm', async (payload) => {
    const result = await dialog.showMessageBox({
      type: 'question',
      buttons: ['Cancel', 'OK'],
      defaultId: 1,
      title: payload.title || 'Confirm',
      message: payload.message,
      detail: payload.detail,
    });

    return {
      confirmed: result.response === 1, // 1 = OK button
    };
  });
}
