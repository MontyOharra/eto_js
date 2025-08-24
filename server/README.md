# ETO Server

Flask-based server for ETO (Email to Order) PDF processing system with Outlook COM integration.

## Project Structure

```
server/
├── src/                    # Source code
│   ├── __init__.py        # Python package marker
│   ├── app.py             # Flask application
│   ├── outlook_service.py # Outlook COM service
│   └── test_endpoints.py  # API testing script
├── scripts/               # Build and deployment scripts
│   ├── build-server.sh   # Build and deploy server
│   ├── server-start.sh   # Start server manually
│   └── refresh-server.sh # Refresh files without rebuild
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── setup-venv.sh        # Virtual environment setup
└── server-scripts.sh    # Main script runner
```

## Setup Instructions

### 1. Set up Virtual Environment

**Using Bash (Git Bash):**

```bash
# Make setup script executable
chmod +x setup-venv.sh

# Run setup script
./setup-venv.sh
```

**Manual setup:**

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/Scripts/activate  # Windows (Git Bash)
# OR
source .venv/bin/activate      # Unix/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Cursor/VS Code

The project includes `.vscode/settings.json` files that configure:

- Python interpreter path to use the virtual environment
- Source code paths for imports
- Linting and formatting settings

**To manually configure in Cursor:**

1. Open Command Palette (`Ctrl+Shift+P`)
2. Select "Python: Select Interpreter"
3. Choose `./server/.venv/Scripts/python.exe`

### 3. Build and Deploy

```bash
# Build and deploy to C:\apps\eto\server
./server-scripts.sh build

# Start the server
./server-scripts.sh start

# Refresh files (without rebuilding venv)
./server-scripts.sh refresh
```

### 4. Test the API

```bash
# Run the test script
python src/test_endpoints.py

# Or test manually with curl
curl http://localhost:8080/health
curl http://localhost:8080/api/email/status
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/email/start` - Start email monitoring
- `POST /api/email/stop` - Stop email monitoring
- `GET /api/email/status` - Get monitoring status
- `GET /api/email/recent` - Get recent emails

## Development

### Running Locally

```bash
# Activate virtual environment
source .venv/Scripts/activate

# Run directly
python main.py

# Or use the start script
./scripts/server-start.sh
```

### Testing

```bash
# Run test script
python src/test_endpoints.py

# Or test individual endpoints
curl -X POST http://localhost:8080/api/email/start \
  -H "Content-Type: application/json" \
  -d '{"email_address": "your.email@example.com"}'
```

## Requirements

- Windows (for Outlook COM integration)
- Python 3.8+
- Outlook installed and configured
- Git Bash (for bash scripts)

## Dependencies

- Flask 3.0.0
- pywin32 (for Outlook COM)
- requests (for HTTP client)
