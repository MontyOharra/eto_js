# Production Build Guide

This guide explains how to build your Electron + Python app for production distribution.

## 🎯 Overview

Your app uses:

- **Electron** for the desktop interface
- **React** for the frontend
- **Python** for backend processing
- **Portable Python** bundled with the app (no user installation required)

## 📋 Prerequisites

- Node.js and npm installed
- Windows (for Windows builds)
- Development environment working (`npm run dev`)

## 🔧 Setup Process

### 1. Install Portable Python

```bash
npm run setup:python
```

This will:

- Download Python 3.11 embeddable package (~10MB)
- Extract it to `resources/python/`
- Test that Python works correctly
- Clean up temporary files

### 2. Build the Application

```bash
# Build all components
npm run build:all

# Or build individually:
npm run build:electron  # TypeScript + Preload bundling
npm run build:react     # React frontend
```

### 3. Create Distribution

```bash
# Windows
npm run dist:win

# Mac (if on Mac)
npm run dist:mac

# Linux (if on Linux)
npm run dist:linux

# All platforms (if supported)
npm run dist:all
```

## 📁 File Structure

### Development

```
src/
├── electron/           # Main process & preload scripts
├── app/               # React frontend
└── python/            # Python scripts
```

### Production Package

```
MyApp/
├── MyApp.exe
└── resources/
    ├── python/                    # Bundled Python runtime
    │   ├── python.exe
    │   ├── python311.dll
    │   └── ... (Python libraries)
    └── python/scripts/            # Your Python scripts
        └── test.py
```

## 🛠 Build Scripts Explained

| Script                   | Purpose                             |
| ------------------------ | ----------------------------------- |
| `npm run setup:python`   | Download & setup portable Python    |
| `npm run build:electron` | Compile TypeScript & bundle preload |
| `npm run build:react`    | Build React frontend                |
| `npm run build:all`      | Build everything for production     |
| `npm run dist:win`       | Create Windows installer/portable   |

## 🔄 How It Works

### Development Mode

- Python scripts: `src/python/test.py`
- Python executable: System `python` command
- Preload: Bundled with esbuild
- React: Served by Vite dev server

### Production Mode

- Python scripts: `resources/python/scripts/test.py`
- Python executable: `resources/python/python.exe`
- Preload: Single bundled `preload.cjs`
- React: Built static files

### Path Resolution

The app automatically detects dev vs production and uses appropriate paths:

```typescript
// Development
spawn("python", ["src/python/test.py", "arg"]);

// Production
spawn("resources/python/python.exe", [
  "resources/python/scripts/test.py",
  "arg",
]);
```

## 📦 Distribution Files

After running `npm run dist:win`, you'll find:

```
dist/
├── ETO-0.0.0.msi           # MSI installer
├── ETO-0.0.0-portable.exe  # Portable executable
└── win-unpacked/           # Unpacked app directory
    ├── ETO.exe
    └── resources/
        └── python/         # Your bundled Python
```

## 🚀 Adding More Python Dependencies

If you need Python packages (like `pywin32` for Outlook):

1. **Option A: pip-install to portable Python**

   ```bash
   resources/python/python.exe -m pip install pywin32
   ```

2. **Option B: Include wheel files**
   - Download `.whl` files to `resources/python/site-packages/`
   - Update electron-builder config to include them

## 🐛 Troubleshooting

### Python Not Found

- Ensure `npm run setup:python` completed successfully
- Check `resources/python/python.exe` exists
- Verify Python path in production logs

### Build Fails

- Clean build: `rm -rf build/ dist/`
- Rebuild: `npm run build:all`
- Check TypeScript errors: `npm run transpile:electron`

### App Won't Start

- Check main process logs in dev tools
- Verify all files included in `electron-builder.json`
- Test Python script manually: `resources/python/python.exe resources/python/scripts/test.py`

## 📋 Checklist

Before distributing:

- [ ] `npm run setup:python` completed
- [ ] `npm run build:all` succeeds
- [ ] `npm run dist:win` creates installer
- [ ] Test installer on clean Windows machine
- [ ] Python functionality works in packaged app
- [ ] All required files included in package

## 🎉 Next Steps

Your production build process is now complete! You can:

1. **Test the packaged app** on a clean machine
2. **Add more Python functionality** (Outlook integration, etc.)
3. **Set up CI/CD** for automated builds
4. **Add code signing** for trusted distribution

Happy building! 🚀
