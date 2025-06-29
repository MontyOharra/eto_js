import path from "path";
import { app, WebFrameMain } from "electron";
import { pathToFileURL } from "url";

export function isDev() {
  return process.env.NODE_ENV === "development";
}

export function getPreloadPath() {
  return path.join(
    app.getAppPath(),
    isDev() ? "." : "..",
    "/build/dist-electron/preload.cjs"
  );
}

export function getUIPath() {
  return path.join(app.getAppPath(), "/dist-react/index.html");
}

export function validateEventFrame(frame: WebFrameMain) {
  if (isDev() && new URL(frame.url).host === `localhost:${devServerPort}`) {
    return;
  }
  if (frame.url !== pathToFileURL(getUIPath()).toString()) {
    throw new Error("Malicious event");
  }
}

export const devServerPort = "5000";

export function getPythonExecutablePath() {
  if (isDev()) {
    // Development: Use system Python
    return "python";
  } else {
    // Production: Use bundled Python
    return path.join(process.resourcesPath, "python", "python.exe");
  }
}

export function getPythonScriptPath(scriptName: string) {
  if (isDev()) {
    // Development: Scripts in src/python/
    return path.join(process.cwd(), "src", "python", scriptName);
  } else {
    // Production: Scripts bundled in resources
    return path.join(process.resourcesPath, "python", "scripts", scriptName);
  }
}
