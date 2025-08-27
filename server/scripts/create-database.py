#!/usr/bin/env python3
"""
Simple script to create the ETO database
Run this before starting the server for the first time
"""

import pyodbc
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create the ETO database"""
    try:
        # Get connection info from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("ERROR: DATABASE_URL not found in environment")
            return False
        
        # Parse connection string to get components
        # Example: mssql+pyodbc://test:testing@localhost:49172/eto_name?driver=...
        parts = database_url.split('/')
        db_name = parts[-1].split('?')[0]  # Get database name
        
        # Extract server, username, password
        auth_server = parts[2]  # test:testing@localhost:49172
        username, rest = auth_server.split(':', 1)
        password, server_port = rest.split('@', 1)
        
        print(f"Creating database '{db_name}' on server '{server_port}'")
        print(f"Using username: {username}")
        
        # Connect to master database to create new database
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_port};DATABASE=master;UID={username};PWD={password};TrustServerCertificate=yes"
        
        print("Connecting to master database...")
        with pyodbc.connect(conn_str) as conn:
            conn.autocommit = True  # Required for CREATE DATABASE
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT name FROM sys.databases WHERE name = ?", db_name)
            if cursor.fetchone():
                print(f"Database '{db_name}' already exists!")
                return True
            
            # Create database
            print(f"Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE [{db_name}]")
            print(f"Database '{db_name}' created successfully!")
            
            # Grant permissions to user
            try:
                cursor.execute(f"USE [{db_name}]")
                cursor.execute(f"CREATE USER [{username}] FOR LOGIN [{username}]")
                cursor.execute(f"ALTER ROLE db_owner ADD MEMBER [{username}]")
                print(f"Granted permissions to user '{username}'")
            except Exception as perm_error:
                print(f"Warning: Could not grant permissions: {perm_error}")
                print("You may need to grant permissions manually")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to create database: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure SQL Server is running")
        print("2. Check that the 'test' user exists and has permissions")
        print("3. Verify the server address and port")
        print("4. Try creating the database manually in SQL Server Management Studio")
        return False

if __name__ == "__main__":
    print("ETO Database Creation Script")
    print("=" * 40)
    
    if create_database():
        print("\n[SUCCESS] Database creation successful!")
        print("You can now start the ETO server.")
    else:
        print("\n[FAILED] Database creation failed!")
        print("Please create the database manually or fix the connection issues.")
        sys.exit(1)