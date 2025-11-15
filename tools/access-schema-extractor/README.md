# Access Database Schema Extractor

A standalone utility to extract schema information from Microsoft Access database files (.mdb, .accdb) and export it as structured JSON for documentation and analysis.

## Purpose

This tool creates a JSON representation of an Access database schema that can be referenced in documentation, provided to AI assistants for context, or used for migration planning. It's particularly useful for understanding legacy database structures without requiring Access to be installed.

## Features

- ✅ Extracts table names and structures
- ✅ Captures column names, data types, and properties
- ✅ Works with both .mdb (Access 2003) and .accdb (Access 2007+) files
- ✅ No Access installation required
- ✅ Cross-platform compatible (Windows, Linux, macOS)
- ✅ Outputs human-readable or compact JSON
- ✅ Self-contained with its own virtual environment

## Limitations

This tool extracts **table schema only**. It does NOT extract:
- Query definitions (stored procedures)
- Table relationships / Foreign keys
- Indexes
- VBA code from forms/reports
- Access-specific features (macros, modules)

For these advanced features, you'll need to use Access's built-in Database Documenter or a VBA script.

## Quick Start

### 1. Setup (First Time Only)

```bash
cd tools/access-schema-extractor
make setup
```

This creates a virtual environment and installs the `access-parser` library.

### 2. Extract Schema

```bash
make extract DB="C:/path/to/database.accdb" OUT="schema.json"
```

### 3. View Output

The output JSON file will contain:
- Database metadata (file name, path, type)
- List of all tables
- For each table: columns with names, types, and properties

## Usage

### Basic Extraction

```bash
make extract DB="path/to/database.accdb" OUT="output.json"
```

### Compact Output (No Indentation)

```bash
make extract-compact DB="path/to/database.accdb" OUT="output.json"
```

### Using Paths with Spaces

```bash
make extract DB="C:/My Documents/Database.accdb" OUT="docs/schema.json"
```

### Direct Python Script (If Venv Already Active)

```bash
python extract_schema.py database.accdb output.json
python extract_schema.py database.accdb output.json --compact
python extract_schema.py --help
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make setup` | Set up virtual environment and install dependencies |
| `make extract` | Extract schema (requires DB and OUT variables) |
| `make extract-compact` | Extract schema with compact JSON output |
| `make clean` | Remove virtual environment and cached files |
| `make reinstall` | Clean and reinstall virtual environment |
| `make update` | Update dependencies to latest versions |
| `make info` | Show environment information |
| `make help` | Display all available commands |

## Output Format

### Example JSON Structure

```json
{
  "database": {
    "file_name": "HTC_Database.accdb",
    "file_path": "C:/path/to/HTC_Database.accdb",
    "file_type": ".accdb"
  },
  "tables": [
    {
      "name": "HTC300_G040_T010A Open Orders",
      "columns": [
        {
          "name": "M_COID",
          "type": "INTEGER",
          "size": 4,
          "nullable": false
        },
        {
          "name": "M_BrID",
          "type": "INTEGER",
          "size": 4,
          "nullable": false
        },
        {
          "name": "m_Orderno",
          "type": "DOUBLE",
          "size": 8,
          "nullable": false
        },
        {
          "name": "m_customer",
          "type": "TEXT",
          "size": 50,
          "nullable": true
        }
      ]
    }
  ],
  "table_count": 45,
  "table_names": [
    "HTC200F_G020_T000 Work Table",
    "HTC300_G040_T010A Open Orders",
    "HTC300_G040_T012A Open Order Dims"
  ]
}
```

## Example Use Cases

### 1. Provide Database Context to AI Assistant

```bash
# Extract schema
make extract DB="C:/apps/eto/server/storage/HTC_Database.accdb" OUT="docs/database/schema.json"

# Then in your conversation with Claude:
# "I've attached the database schema at docs/database/schema.json.
#  Please review the table structure before we discuss the migration."
```

### 2. Document Database Structure

```bash
# Extract to documentation folder
make extract DB="database.accdb" OUT="docs/database/current_schema.json"

# Commit to version control to track schema changes over time
git add docs/database/current_schema.json
git commit -m "docs: Update database schema snapshot"
```

### 3. Compare Schema Versions

```bash
# Extract current schema
make extract DB="database_v1.accdb" OUT="schema_v1.json"
make extract DB="database_v2.accdb" OUT="schema_v2.json"

# Use diff tool to compare
diff schema_v1.json schema_v2.json
```

## Troubleshooting

### "access-parser" Installation Issues

If you encounter issues installing `access-parser`:

```bash
make clean
make setup
```

### Database File Not Found

Ensure the path is correct and use quotes for paths with spaces:

```bash
# Wrong (if path has spaces)
make extract DB=C:/My Documents/db.accdb OUT=out.json

# Correct
make extract DB="C:/My Documents/db.accdb" OUT=out.json
```

### Permission Denied

Ensure the database file is not open in Access and you have read permissions:

```bash
# Check file permissions
ls -l database.accdb
```

### Large Database Files

For very large databases, the extraction may take several minutes. You'll see progress output:

```
Opening database: HTC_Database.accdb
Found 45 tables
Processing table 1/45: Table_Name_1
Processing table 2/45: Table_Name_2
...
```

## Technical Details

### Dependencies

- **Python**: 3.7+
- **access-parser**: 0.0.6 (automatically installed)

### Virtual Environment

The tool uses its own isolated virtual environment located in `venv/` directory. This ensures:
- No conflicts with other Python projects
- Reproducible dependency versions
- Easy cleanup (just delete `venv/` folder)

### Platform Compatibility

- **Windows**: Full support (tested)
- **Linux/macOS**: Full support via `access-parser` library
- **No Access installation required** on any platform

## Development

### Project Structure

```
tools/access-schema-extractor/
├── extract_schema.py   # Main extraction script
├── requirements.txt    # Python dependencies
├── Makefile           # Automation commands
├── README.md          # This file
└── venv/             # Virtual environment (created by make setup)
```

### Updating Dependencies

```bash
# Update to latest compatible versions
make update

# Or manually edit requirements.txt and run:
make reinstall
```

### Adding Features

The `extract_schema.py` script is well-structured for extensions:

- `extract_column_info()`: Customize column metadata extraction
- `extract_table_info()`: Add index/relationship extraction
- `extract_database_schema()`: Add query/VBA extraction (if access-parser supports it)

## Related Documentation

- [access-parser on PyPI](https://pypi.org/project/access-parser/)
- [access-parser on GitHub](https://github.com/claroty/access_parser)
- [VBA Analysis Documentation](../../docs/vba-analysis/)

## License

This utility is part of the ETO JavaScript migration project.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review the `make help` output for command usage
3. Consult the VBA migration documentation in `docs/`
