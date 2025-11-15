#!/usr/bin/env python3
"""
Extract schema for a single Access database table using pyodbc.

Usage:
    python extract_single_table.py <database_path> <table_name> <output_path>
"""

import argparse
import json
import sys
from pathlib import Path
import pyodbc


def extract_table_schema(database_path: str, table_name: str):
    """Extract schema for a single table from Access database."""
    # Build connection string
    conn_str = (
        r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={database_path};'
    )

    try:
        print(f"Connecting to database: {database_path}")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        print(f"Extracting schema for table: {table_name}")

        # Get columns for the table
        columns = []
        for col in cursor.columns(table=table_name):
            column_info = {
                'name': col.column_name,
                'type': col.type_name,
                'size': col.column_size,
                'nullable': col.nullable == 1,
                'position': col.ordinal_position
            }

            # Add default value if present
            if col.column_def is not None:
                column_info['default'] = col.column_def

            columns.append(column_info)

        if not columns:
            raise ValueError(f"Table '{table_name}' not found or has no columns")

        # Get primary keys
        primary_keys = []
        try:
            for pk in cursor.primaryKeys(table=table_name):
                primary_keys.append({
                    'column': pk.column_name,
                    'key_sequence': pk.key_seq
                })
        except:
            pass  # Primary keys might not be available

        # Get indexes
        indexes = []
        try:
            index_dict = {}
            for idx in cursor.statistics(table=table_name):
                if idx.index_name:
                    if idx.index_name not in index_dict:
                        index_dict[idx.index_name] = {
                            'name': idx.index_name,
                            'unique': idx.non_unique == 0,
                            'columns': []
                        }
                    index_dict[idx.index_name]['columns'].append({
                        'name': idx.column_name,
                        'position': idx.ordinal_position
                    })
            indexes = list(index_dict.values())
        except:
            pass  # Indexes might not be available

        # Get foreign keys
        foreign_keys = []
        try:
            for fk in cursor.foreignKeys(table=table_name):
                foreign_keys.append({
                    'column': fk.fkcolumn_name,
                    'referenced_table': fk.pktable_name,
                    'referenced_column': fk.pkcolumn_name,
                    'constraint_name': fk.fk_name
                })
        except:
            pass  # Foreign keys might not be available

        cursor.close()
        conn.close()

        schema = {
            'table': {
                'name': table_name,
                'column_count': len(columns)
            },
            'columns': columns
        }

        if primary_keys:
            schema['primary_keys'] = primary_keys

        if indexes:
            schema['indexes'] = indexes

        if foreign_keys:
            schema['foreign_keys'] = foreign_keys

        return schema

    except pyodbc.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Extract schema for a single table from Access database'
    )

    parser.add_argument(
        'database_path',
        help='Path to the Access database file'
    )

    parser.add_argument(
        'table_name',
        help='Name of the table to extract'
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

    args = parser.parse_args()

    try:
        # Extract schema
        schema = extract_table_schema(args.database_path, args.table_name)

        # Save to JSON
        output_file = Path(args.output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            if args.compact:
                json.dump(schema, f, ensure_ascii=False)
            else:
                json.dump(schema, f, indent=2, ensure_ascii=False)

        print(f"\nSchema successfully exported to: {output_file.absolute()}")
        print(f"\n{'='*60}")
        print("EXTRACTION SUMMARY")
        print('='*60)
        print(f"Table: {schema['table']['name']}")
        print(f"Columns: {schema['table']['column_count']}")
        if 'primary_keys' in schema:
            print(f"Primary keys: {len(schema['primary_keys'])}")
        if 'indexes' in schema:
            print(f"Indexes: {len(schema['indexes'])}")
        if 'foreign_keys' in schema:
            print(f"Foreign keys: {len(schema['foreign_keys'])}")
        print('='*60)

        return 0

    except Exception as e:
        print(f"Failed to extract schema: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
