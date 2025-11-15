#!/usr/bin/env python3
"""
Access Database Schema Extractor

Extracts schema information from Microsoft Access database files (.mdb, .accdb)
and outputs a structured JSON file for documentation and analysis.

Usage:
    python extract_schema.py <database_path> <output_path>

Example:
    python extract_schema.py C:/path/to/database.accdb schema_output.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from access_parser import AccessParser


def extract_column_info(column) -> Dict[str, Any]:
    """Extract detailed information from a table column."""
    col_info = {
        'name': column.name,
        'type': str(column.type),
    }

    # Add optional attributes if they exist
    optional_attrs = ['size', 'precision', 'scale', 'nullable', 'default']
    for attr in optional_attrs:
        if hasattr(column, attr):
            value = getattr(column, attr)
            if value is not None:
                col_info[attr] = value

    return col_info


def extract_table_info(db: AccessParser, table_name: str) -> Dict[str, Any]:
    """Extract detailed information from a table."""
    try:
        table = db.parse_table(table_name)

        table_info = {
            'name': table_name,
            'columns': []
        }

        # Extract column information
        for column in table.columns:
            table_info['columns'].append(extract_column_info(column))

        # Add row count if available
        if hasattr(table, 'row_count'):
            table_info['row_count'] = table.row_count

        return table_info

    except Exception as e:
        print(f"Warning: Could not fully parse table '{table_name}': {e}", file=sys.stderr)
        return {
            'name': table_name,
            'columns': [],
            'error': str(e)
        }


def extract_database_schema(database_path: str) -> Dict[str, Any]:
    """Extract complete schema from Access database."""
    db_path = Path(database_path)

    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {database_path}")

    if not db_path.suffix.lower() in ['.mdb', '.accdb']:
        raise ValueError(f"Invalid file type: {db_path.suffix}. Expected .mdb or .accdb")

    print(f"Opening database: {db_path}")
    db = AccessParser(str(db_path))

    print(f"Found {len(db.catalog)} tables")

    schema = {
        'database': {
            'file_name': db_path.name,
            'file_path': str(db_path.absolute()),
            'file_type': db_path.suffix
        },
        'tables': [],
        'table_count': len(db.catalog),
        'table_names': sorted(db.catalog)
    }

    # Extract each table
    for i, table_name in enumerate(sorted(db.catalog), 1):
        print(f"Processing table {i}/{len(db.catalog)}: {table_name}")
        table_info = extract_table_info(db, table_name)
        schema['tables'].append(table_info)

    return schema


def save_schema_json(schema: Dict[str, Any], output_path: str, pretty: bool = True):
    """Save schema to JSON file."""
    output_file = Path(output_path)

    # Create parent directories if they don't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        else:
            json.dump(schema, f, ensure_ascii=False)

    print(f"\nSchema successfully exported to: {output_file.absolute()}")
    print(f"File size: {output_file.stat().st_size:,} bytes")


def main():
    parser = argparse.ArgumentParser(
        description='Extract schema from Microsoft Access database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s database.accdb output.json
  %(prog)s "C:/My Database.accdb" "docs/schema.json"
  %(prog)s database.mdb schema.json --compact

Note:
  This tool extracts table and column information. It does NOT extract:
  - Query definitions (stored procedures)
  - Relationships/Foreign keys
  - Indexes
  - VBA code from forms/reports
  - Access-specific features (macros, modules)
        '''
    )

    parser.add_argument(
        'database_path',
        help='Path to the Access database file (.mdb or .accdb)'
    )

    parser.add_argument(
        'output_path',
        help='Path where the JSON schema file will be saved'
    )

    parser.add_argument(
        '--compact',
        action='store_true',
        help='Output compact JSON (no indentation)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    args = parser.parse_args()

    try:
        # Extract schema
        schema = extract_database_schema(args.database_path)

        # Save to JSON
        save_schema_json(schema, args.output_path, pretty=not args.compact)

        # Print summary
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        print(f"Database: {schema['database']['file_name']}")
        print(f"Tables extracted: {schema['table_count']}")
        print(f"Total columns: {sum(len(t['columns']) for t in schema['tables'])}")
        print("="*60)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
