import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const sourceDir = path.join(__dirname, "..", "prisma", "generated");
const targetDir = path.join(__dirname, "..", "build", "prisma", "generated");

// Function to copy directory recursively
function copyDir(src, dest) {
  if (!fs.existsSync(src)) {
    console.log(`Source directory does not exist: ${src}`);
    return;
  }

  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      try {
        fs.copyFileSync(srcPath, destPath);
      } catch (error) {
        if (error.code === "EBUSY" || error.code === "EPERM") {
          console.log(`⚠️  Skipping locked file: ${entry.name}`);
          // Try to remove existing file and copy again
          try {
            if (fs.existsSync(destPath)) {
              fs.unlinkSync(destPath);
            }
            fs.copyFileSync(srcPath, destPath);
            console.log(`✅ Successfully copied: ${entry.name}`);
          } catch (retryError) {
            console.log(
              `❌ Failed to copy: ${entry.name} - ${retryError.message}`
            );
          }
        } else {
          throw error;
        }
      }
    }
  }
}

console.log("Copying Prisma generated files...");
copyDir(sourceDir, targetDir);
console.log("✅ Prisma files copied to build directory");
