import { build } from "esbuild";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, "..");

async function copyPrismaEngine() {
  const sourceEngine = path.join(
    rootDir,
    "prisma/generated/client/query_engine-windows.dll.node"
  );
  const targetDir = path.join(rootDir, "build/dist-electron/main");
  const targetEngine = path.join(targetDir, "query_engine-windows.dll.node");

  // Ensure target directory exists
  await fs.promises.mkdir(targetDir, { recursive: true });

  // Copy the Prisma query engine binary if it exists
  if (fs.existsSync(sourceEngine)) {
    await fs.promises.copyFile(sourceEngine, targetEngine);
    console.log("✅ Prisma query engine copied");
  } else {
    console.log(
      "⚠️  Prisma query engine not found, run 'npm run prisma:generate' first"
    );
  }
}

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

    // Copy Prisma query engine after successful build
    await copyPrismaEngine();

    console.log("✅ Main bundle built successfully!");
  } catch (error) {
    console.error("❌ Main bundle failed:", error);
    process.exit(1);
  }
}

buildMain();
