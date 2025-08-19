import { ipcMain } from "electron";
import type { WebContents, WebFrameMain } from "electron";
import { validateEventFrame } from "./utils.js";

export function ipcMainHandle<Key extends keyof OutputPayloadMapping>(
  key: Key,
  handler: (
    payload: InputPayloadMapping[Key]
  ) => Promise<OutputPayloadMapping[Key]>
) {
  ipcMain.handle(key, (event, payload) => {
    validateEventFrame(event.senderFrame as WebFrameMain);
    return handler(payload);
  });
}

export function ipcMainOn<Key extends keyof OutputPayloadMapping>(
  key: Key,
  handler: (payload: OutputPayloadMapping[Key]) => void
) {
  ipcMain.on(key, (event, payload) => {
    validateEventFrame(event.senderFrame as WebFrameMain);
    return handler(payload);
  });
}

export function ipcWebContentsSend<Key extends keyof InputPayloadMapping>(
  key: Key,
  webContents: WebContents,
  payload: InputPayloadMapping[Key]
) {
  webContents.send(key, payload);
}
