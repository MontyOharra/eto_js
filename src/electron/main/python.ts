import { spawn } from "child_process";
import { getPythonExecutablePath, getPythonScriptPath } from "./utils.js";

export async function executePythonScript<T>(
  scriptName: string,
  payload: T
): Promise<string> {
  let outputData = "";
  let errorData = "";

  const pyOutput = new Promise<string>((resolve, reject) => {
    const scriptPath = getPythonScriptPath(scriptName);
    // Serialize payload to string for Python process
    const serializedPayload =
      typeof payload === "string" ? payload : JSON.stringify(payload);
    const py = spawn(getPythonExecutablePath(), [
      scriptPath,
      serializedPayload,
    ]);

    py.stdout.on("data", (data) => {
      outputData += data.toString();
    });

    py.stderr.on("data", (data) => {
      errorData += data.toString();
    });

    py.on("close", (code) => {
      if (code === 0) {
        resolve(outputData);
      } else {
        reject(
          new Error(`Python script failed with code ${code}: ${errorData}`)
        );
      }
    });

    py.on("error", (err) => {
      reject(new Error(`Failed to start Python process: ${err.message}`));
    });
  });

  return await pyOutput;
}
