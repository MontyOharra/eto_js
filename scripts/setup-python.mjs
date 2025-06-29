import https from "https";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, "..");
const resourcesDir = path.join(rootDir, "resources");
const pythonDir = path.join(resourcesDir, "python");

// Python 3.11 embeddable package for Windows x64
const PYTHON_URL =
  "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip";
const PYTHON_ZIP = path.join(resourcesDir, "python-embed.zip");

async function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    console.log(`📥 Downloading ${url}...`);
    const file = fs.createWriteStream(dest);

    https
      .get(url, (response) => {
        response.pipe(file);
        file.on("finish", () => {
          file.close();
          console.log(`✅ Downloaded to ${dest}`);
          resolve();
        });
      })
      .on("error", (err) => {
        fs.unlink(dest, () => {}); // Delete the file async
        reject(err);
      });
  });
}

async function extractZip(zipPath, extractTo) {
  console.log(`📦 Extracting ${zipPath} to ${extractTo}...`);

  try {
    // Use PowerShell to extract (Windows built-in)
    execSync(
      `powershell -command "Expand-Archive -Path '${zipPath}' -DestinationPath '${extractTo}' -Force"`,
      {
        stdio: "inherit",
      }
    );
    console.log(`✅ Extracted successfully`);
  } catch (error) {
    console.error(`❌ Extraction failed:`, error.message);
    throw error;
  }
}

async function setupPython() {
  try {
    // Create directories
    console.log(`📁 Creating directories...`);
    fs.mkdirSync(resourcesDir, { recursive: true });
    fs.mkdirSync(pythonDir, { recursive: true });

    // Download Python if not exists
    if (!fs.existsSync(PYTHON_ZIP)) {
      await downloadFile(PYTHON_URL, PYTHON_ZIP);
    } else {
      console.log(`📦 Python zip already exists, skipping download`);
    }

    // Extract Python
    await extractZip(PYTHON_ZIP, pythonDir);

    // Create a simple test to verify Python works
    const testScript = path.join(pythonDir, "test_python.py");
    fs.writeFileSync(testScript, 'print("Python setup successful!")');

    // Test Python executable
    console.log(`🧪 Testing Python installation...`);
    const pythonExe = path.join(pythonDir, "python.exe");

    try {
      execSync(`"${pythonExe}" "${testScript}"`, { stdio: "inherit" });
      console.log(`✅ Python is working correctly!`);
    } catch (error) {
      console.error(`❌ Python test failed:`, error.message);
      throw error;
    }

    // Clean up
    fs.unlinkSync(testScript);
    fs.unlinkSync(PYTHON_ZIP);

    console.log(`🎉 Python setup complete!`);
    console.log(`📍 Python installed at: ${pythonDir}`);
    console.log(`🐍 Executable: ${pythonExe}`);
  } catch (error) {
    console.error(`❌ Setup failed:`, error);
    process.exit(1);
  }
}

setupPython();
