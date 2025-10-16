import path from "path";
import fs from "fs";
import { app, WebFrameMain } from "electron";
import { pathToFileURL } from "url";

export const devServerPort = "5002";

export function isDev() {
  return process.env.NODE_ENV === "development";
}

export function getPreloadPath() {
  return path.join(
    app.getAppPath(),
    isDev() ? "." : "..",
    "build/dist-electron/preload.cjs"
  );
}

export function getUIPath() {
  return path.join(app.getAppPath(), "build/dist-react/index.html");
}

const UI_URL = pathToFileURL(getUIPath()).toString(); // …/index.html

function stripFragmentAndQuery(raw: string) {
  const u = new URL(raw);
  u.hash = "";
  u.search = "";
  return u.toString();
}

export function validateEventFrame(frame: WebFrameMain) {
  // Allow dev hot-reloads
  if (isDev() && new URL(frame.url).host === `localhost:${devServerPort}`)
    return;

  if (stripFragmentAndQuery(frame.url) !== UI_URL) {
    console.log(`Frame URL: ${frame.url}`);
    console.log(`Expected UI Path: ${pathToFileURL(getUIPath()).toString()}`);
    throw new Error(`Malicious event: ${frame.url} does not match ${UI_URL}`);
  }
}

export function getPythonExecutablePath() {
  if (isDev()) {
    // Development: Prefer local venv interpreter if present, else fallback to system Python
    const cwd = process.cwd();
    const winVenvPython = path.join(cwd, ".venv", "Scripts", "python.exe");
    const posixVenvPython = path.join(cwd, ".venv", "bin", "python");
    if (process.platform === "win32" && fs.existsSync(winVenvPython)) {
      return winVenvPython;
    }
    if (process.platform !== "win32" && fs.existsSync(posixVenvPython)) {
      return posixVenvPython;
    }
    return "python";
  } else {
    // Production: Use bundled Python
    return path.join(process.resourcesPath, "python", "python.exe");
  }
}

export function getPythonScriptPath(scriptDirStructure: string) {
  if (isDev()) {
    // Development: Scripts in src/python/
    return path.join(process.cwd(), "src", "python", scriptDirStructure);
  } else {
    // Production: Scripts bundled in resources
    return path.join(
      process.resourcesPath,
      "python",
      "scripts",
      scriptDirStructure
    );
  }
}