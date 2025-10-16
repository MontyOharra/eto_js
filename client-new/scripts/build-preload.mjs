import { build } from "esbuild";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, "..");

async function buildPreload() {
  try {
    await build({
      // Entry point - your main preload file
      entryPoints: [path.join(rootDir, "src/preload/index.ts")],

      // Output configuration
      outfile: path.join(rootDir, "build/dist-electron/preload.cjs"),

      // Bundle everything into one file
      bundle: true,

      // Target environment
      platform: "node",
      target: "node16",

      // Output format
      format: "cjs",

      // Don't include external dependencies (electron APIs)
      external: ["electron"],

      // Source maps for debugging
      sourcemap: process.env.NODE_ENV === "development",

      // Minify for production
      minify: process.env.NODE_ENV === "production",

      // TypeScript support
      loader: {
        ".cts": "ts",
        ".ts": "ts",
      },

      // Resolve TypeScript files
      resolveExtensions: [".cts", ".ts", ".js", ".cjs"],

      // Don't split code
      splitting: false,

      // Clean output
      logLevel: "info",
    });
    console.log(process.env.NODE_ENV);
    console.log("✅ Preload bundle built successfully!");
  } catch (error) {
    console.error("❌ Preload bundle failed:", error);
    process.exit(1);
  }
}

buildPreload();
