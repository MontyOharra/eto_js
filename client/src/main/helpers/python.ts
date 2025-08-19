import { spawn } from "child_process";
import { getPythonExecutablePath, getPythonScriptPath } from "./utils.js";

type PythonExecutionErrorDetails = {
  reason: string;
  pythonExecutablePath: string;
  scriptPath: string;
  spawnArgs: string[];
  payloadLength: number;
  argPreviewStart?: string;
  argPreviewEnd?: string;
  exitCode?: number | null;
  signal?: NodeJS.Signals | null;
  stdoutLength: number;
  stderrLength: number;
  stdoutSample?: string;
  stderrSample?: string;
  cwd: string;
  envPath?: string;
  nodeError?: {
    code?: string | number;
    errno?: string | number;
    syscall?: string;
    message?: string;
  };
  timestamp: string;
};

export async function executePythonScript<T>(
  scriptName: string,
  payload: T
): Promise<string> {
  let outputData = "";
  let errorData = "";

  const pythonPath = getPythonExecutablePath();
  const scriptPath = getPythonScriptPath(scriptName);
  const serializedPayload =
    typeof payload === "string" ? payload : JSON.stringify(payload);

  // Preflight: avoid Windows command-line length limits causing opaque ENAMETOOLONG
  // Windows max command line length is ~32,767 chars; keep a safety margin
  const MAX_SAFE_ARG_LENGTH_WINDOWS = 30000;
  if (
    process.platform === "win32" &&
    serializedPayload.length > MAX_SAFE_ARG_LENGTH_WINDOWS
  ) {
    const details: PythonExecutionErrorDetails = {
      reason: "ARGUMENT_TOO_LARGE",
      pythonExecutablePath: pythonPath,
      scriptPath,
      spawnArgs: [scriptPath, "<payload omitted due to size>"],
      payloadLength: serializedPayload.length,
      argPreviewStart: serializedPayload.slice(0, 128),
      argPreviewEnd: serializedPayload.slice(-128),
      exitCode: null,
      signal: null,
      stdoutLength: 0,
      stderrLength: 0,
      cwd: process.cwd(),
      envPath: process.env.PATH,
      timestamp: new Date().toISOString(),
    };
    const err = new Error(
      `Python invocation aborted: argument too large for Windows command line (length=${serializedPayload.length})`
    ) as Error & { details?: PythonExecutionErrorDetails };
    err.name = "PythonArgumentSizeError";
    err.details = details;
    return Promise.reject(err);
  }

  const spawnArgs = [scriptPath, serializedPayload];

  const pyOutput = new Promise<string>((resolve, reject) => {
    const py = spawn(pythonPath, spawnArgs);

    py.stdout.on("data", (data) => {
      outputData += data.toString();
    });

    py.stderr.on("data", (data) => {
      errorData += data.toString();
    });

    py.on("close", (code, signal) => {
      if (code === 0) {
        resolve(outputData);
        return;
      }

      const details: PythonExecutionErrorDetails = {
        reason: "PROCESS_EXIT_NON_ZERO",
        pythonExecutablePath: pythonPath,
        scriptPath,
        spawnArgs,
        payloadLength: serializedPayload.length,
        argPreviewStart: serializedPayload.slice(0, 128),
        argPreviewEnd: serializedPayload.slice(-128),
        exitCode: code ?? null,
        signal: (signal as NodeJS.Signals) ?? null,
        stdoutLength: outputData.length,
        stderrLength: errorData.length,
        stdoutSample: outputData.slice(0, 512),
        stderrSample: errorData.slice(0, 1024),
        cwd: process.cwd(),
        envPath: process.env.PATH,
        timestamp: new Date().toISOString(),
      };

      const err = new Error(
        `Python script failed (code=${code}, signal=${signal ?? "none"})`
      ) as Error & { details?: PythonExecutionErrorDetails };
      err.name = "PythonScriptError";
      err.details = details;
      reject(err);
    });

    py.on("error", (err: NodeJS.ErrnoException) => {
      const details: PythonExecutionErrorDetails = {
        reason: "SPAWN_FAILED",
        pythonExecutablePath: pythonPath,
        scriptPath,
        spawnArgs,
        payloadLength: serializedPayload.length,
        argPreviewStart: serializedPayload.slice(0, 128),
        argPreviewEnd: serializedPayload.slice(-128),
        exitCode: null,
        signal: null,
        stdoutLength: outputData.length,
        stderrLength: errorData.length,
        stdoutSample: outputData.slice(0, 512),
        stderrSample: errorData.slice(0, 1024),
        cwd: process.cwd(),
        envPath: process.env.PATH,
        nodeError: {
          code: err.code,
          errno: (err as any)?.errno,
          syscall: err.syscall,
          message: err.message,
        },
        timestamp: new Date().toISOString(),
      };

      const wrapped = new Error(
        `Failed to start Python process (code=${err.code}, syscall=${err.syscall})`
      ) as Error & { details?: PythonExecutionErrorDetails };
      wrapped.name = "PythonSpawnError";
      wrapped.details = details;
      reject(wrapped);
    });
  });

  return await pyOutput;
}
