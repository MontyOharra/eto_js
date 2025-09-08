#!/usr/bin/env python3
"""
Data Cleanup Script for ETO System

This script clears data folders (logs, storage) without affecting the database or application code.
Safe to run anytime to clean up accumulated files.

Usage:
    python clear-data.py [--confirm]
    
Options:
    --confirm    Skip confirmation prompt (for automation)
"""

import sys
import os
import shutil
import argparse
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_server_root():
    """Get the server root directory (parent of scripts folder)"""
    return Path(__file__).parent.parent

def confirm_cleanup():
    """Ask user to confirm data cleanup"""
    print("🗑️  ETO Data Cleanup")
    print("=" * 30)
    print("This will DELETE the following folders and their contents:")
    print("   - logs/ (all log files)")
    print("   - storage/ (all stored PDF files)")
    print()
    print("⚠️  WARNING: PDF files in storage will be permanently lost!")
    print("   (They can be re-downloaded from emails if needed)")
    print()
    
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    return response.lower() == 'yes'

def clear_folder(folder_path, folder_name):
    """Clear a folder if it exists"""
    if folder_path.exists():
        try:
            # Remove the entire folder
            shutil.rmtree(folder_path)
            logger.info(f"✅ Cleared folder: {folder_name}/")
            
            # Recreate the empty folder
            folder_path.mkdir(exist_ok=True)
            logger.info(f"📁 Recreated empty folder: {folder_name}/")
            
        except Exception as e:
            logger.error(f"❌ Error clearing {folder_name}/: {e}")
            return False
    else:
        logger.info(f"📂 Folder {folder_name}/ doesn't exist, skipping")
    
    return True

def clear_data_folders():
    """Clear all data folders"""
    server_root = get_server_root()
    success = True
    
    # Define folders to clear
    folders_to_clear = [
        (server_root / "logs", "logs"),
        (server_root / "storage", "storage")
    ]
    
    logger.info("Starting data folder cleanup...")
    
    for folder_path, folder_name in folders_to_clear:
        if not clear_folder(folder_path, folder_name):
            success = False
    
    return success

def main():
    parser = argparse.ArgumentParser(description='Clear ETO data folders (logs, storage)')
    parser.add_argument('--confirm', action='store_true', 
                       help='Skip confirmation prompt (for automation)')
    
    args = parser.parse_args()
    
    # Get confirmation unless --confirm flag is used
    if not args.confirm and not confirm_cleanup():
        print("❌ Data cleanup cancelled")
        sys.exit(0)
    
    try:
        # Clear data folders
        if clear_data_folders():
            print("\n✅ Data cleanup completed successfully!")
            print("   - logs/ folder cleared and recreated")
            print("   - storage/ folder cleared and recreated")
            print("   - Ready for fresh data collection")
        else:
            print("\n⚠️  Data cleanup completed with some errors")
            print("   Check the logs above for details")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        print(f"\n❌ Data cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()