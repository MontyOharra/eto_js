# ETO Server

Node.js backend server for the ETO PDF processing system.

## Features

- **Email Ingest**: Polls email inbox for PDF attachments
- **PDF Processing**: Extracts objects from PDFs using Python
- **Signature Matching**: Matches PDFs against templates
- **Extraction Rules**: Applies field extraction rules
- **REST API**: Provides endpoints for client communication
- **Job Queue**: Background processing with retry logic

## Prerequisites

- Node.js 18+
- SQL Server
- Python 3.12+ with pdfplumber
- NSSM (for Windows service)

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Database Setup

1. Create SQL Server database
2. Run Prisma migrations:

```bash
npm run prisma:generate
npm run prisma:migrate
```

### 3. Environment Configuration

Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
```

Key settings:

- `DATABASE_URL`: SQL Server connection string
- `EMAIL_HOST`: IMAP server (e.g., outlook.office365.com)
- `EMAIL_USERNAME`: Email username
- `EMAIL_PASSWORD`: Email app password
- `STORAGE_PATH`: Path for PDF storage

### 4. Python Setup

Create virtual environment and install dependencies:

```bash
python -m venv python/.venv
python/.venv/Scripts/activate  # Windows
pip install pdfplumber pillow pdfminer.six
```

## Development

### Start Development Server

```bash
npm run dev
```

### Build for Production

```bash
npm run build
```

### Run Tests

```bash
npm test
```

## Deployment

### Manual Deployment

1. Build the project:

```bash
npm run build
```

2. Run deployment script (as Administrator):

```powershell
.\deploy.ps1
```

### Git-based Deployment

1. Push code to repository
2. On server, pull latest changes:

```bash
git pull origin main
npm install
npm run build
.\deploy.ps1
```

## API Endpoints

### Health Check

- `GET /health` - Server health status

### Email Ingest

- `POST /api/email/ingest` - Manually trigger email ingest

### PDF Processing

- `POST /api/pdfs/extract` - Extract objects from PDF
- `POST /api/pdfs/upload` - Upload PDF file

### Signatures

- `GET /api/signatures` - List signatures
- `POST /api/signatures` - Create signature

### Processing

- `POST /api/process/:fileId` - Process PDF file

## Service Management

### Start Service

```powershell
Start-Service eto-server
```

### Stop Service

```powershell
Stop-Service eto-server
```

### Check Status

```powershell
Get-Service eto-server
```

### View Logs

```powershell
Get-Content C:\apps\eto\server\logs\service.log -Tail 50
```

## Architecture

```
server/
├── src/
│   ├── modules/
│   │   ├── email-ingest/     # Email polling and attachment processing
│   │   ├── pdf-processor/    # PDF object extraction
│   │   ├── signature-matcher/ # Template matching
│   │   ├── extraction-runner/ # Field extraction
│   │   ├── review-api/       # Review interface
│   │   └── jobs/             # Background job processing
│   ├── database/             # Database models and migrations
│   ├── python/               # Python scripts
│   └── utils/                # Shared utilities
├── prisma/                   # Database schema
├── logs/                     # Application logs
└── storage/                  # PDF file storage
```

## Troubleshooting

### Service Won't Start

1. Check logs: `C:\apps\eto\server\logs\service-error.log`
2. Verify environment variables in NSSM
3. Check database connection
4. Ensure Python virtual environment is accessible

### Email Ingest Issues

1. Verify email credentials
2. Check IMAP server settings
3. Ensure app password is used (not regular password)
4. Check firewall settings

### Database Issues

1. Verify SQL Server is running
2. Check connection string format
3. Ensure database user has proper permissions
4. Run Prisma migrations if schema changed
