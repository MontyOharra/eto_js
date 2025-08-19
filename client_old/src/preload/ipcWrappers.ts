import { ipcRenderer } from "electron";

export function ipcRendererInvoke<Key extends keyof InputPayloadMapping>(
  key: Key,
  payload?: InputPayloadMapping[Key]
): Promise<OutputPayloadMapping[Key]> {
  return ipcRenderer.invoke(key, payload);
}

export function ipcRendererOn<Key extends keyof OutputPayloadMapping>(
  key: Key,
  callback: (payload: OutputPayloadMapping[Key]) => void
) {
  const cb = (
    _: Electron.IpcRendererEvent,
    payload: OutputPayloadMapping[Key]
  ) => callback(payload);
  ipcRenderer.on(key, cb);
  return () => ipcRenderer.off(key, cb);
}

export function ipcRendererSend<Key extends keyof InputPayloadMapping>(
  key: Key,
  payload: InputPayloadMapping[Key]
) {
  ipcRenderer.send(key, payload);
}
