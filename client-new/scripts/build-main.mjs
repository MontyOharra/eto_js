import { build } from "esbuild";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, "..");

async function buildMain() {
  try {
    await build({
      entryPoints: [path.join(rootDir, "src/main/index.ts")],
      outfile: path.join(rootDir, "build/dist-electron/main/index.cjs"),
      bundle: true,
      platform: "node",
      target: "node16",
      format: "cjs",
      external: ["electron", "keytar"],
      sourcemap: process.env.NODE_ENV === "development",
      minify: process.env.NODE_ENV === "production",
      loader: {
        ".ts": "ts",
      },
      resolveExtensions: [".ts", ".js"],
      logLevel: "info",
      define: {
        // Pass NODE_ENV to the bundled code
        "process.env.NODE_ENV": JSON.stringify(
          process.env.NODE_ENV || "production"
        ),
      },
    });

    console.log("✅ Main bundle built successfully!");
  } catch (error) {
    console.error("❌ Main bundle failed:", error);
    process.exit(1);
  }
}

buildMain();
