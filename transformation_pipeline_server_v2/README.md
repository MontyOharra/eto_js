# Transformation Pipeline Server v2

A new FastAPI-based server for the transformation pipeline system with node-based architecture and Dask execution.

## Quick Start

1. **Setup development environment:**
   ```bash
   make setup
   ```

2. **Start development server:**
   ```bash
   make dev
   ```

3. **Access the server:**
   - Health endpoint: http://localhost:8090/api/health
   - API docs: http://localhost:8090/docs
   - ReDoc: http://localhost:8090/redoc

## Development

### Project Structure
```
transformation_pipeline_server_v2/
├── src/
│   ├── api/routers/         # FastAPI route handlers
│   ├── shared/
│   │   ├── database/        # Database models and repositories
│   │   ├── services/        # Business logic services
│   │   └── utils/          # Utility functions
│   ├── features/           # Feature-specific modules
│   └── app.py             # FastAPI application factory
├── main.py                # Server entry point
├── requirements.txt       # Python dependencies
├── Makefile              # Development commands
└── .env                  # Environment configuration
```

### Available Commands
- `make help` - Show available commands
- `make setup` - Install dependencies and create directories
- `make dev` - Start development server with reload
- `make clean-data` - Clean logs and storage
- `make clean` - Remove virtual environment
- `make reset-all` - Reset everything

## Configuration

Environment variables in `.env`:
- `PIPELINE_PORT` - Server port (default: 8090)
- `PIPELINE_HOST` - Server host (default: 0.0.0.0)
- `DEBUG` - Debug mode (default: true)
- `LOG_LEVEL` - Logging level (default: INFO)

## Architecture

This server follows the proposed transformation pipeline design with:
- Node-based pipeline system with dynamic I/O
- Dask-based DAG execution (to be implemented)
- Transform/Action/Logic module types
- Immutable pipeline compilation with checksums
- Comprehensive validation and type safety