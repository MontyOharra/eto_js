#!/bin/bash
# Clear Data Script for ETO System (Unix/Linux/macOS)
# This script clears data folders (logs, storage) without affecting database or code

echo "🗑️  ETO Data Cleanup (Unix/Linux)"
echo "================================="
echo "This will DELETE the following folders and their contents:"
echo "   - logs/ (all log files)"
echo "   - storage/ (all stored PDF files)"
echo ""
echo "⚠️  WARNING: PDF files in storage will be permanently lost!"
echo "   (They can be re-downloaded from emails if needed)"
echo ""

read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Data cleanup cancelled"
    exit 0
fi

echo ""
echo "Starting data folder cleanup..."

# Change to server directory (parent of scripts)
cd "$(dirname "$0")/.."

# Clear logs folder
if [ -d "logs" ]; then
    echo "🗑️  Removing logs folder..."
    rm -rf "logs"
    if [ $? -eq 0 ]; then
        echo "✅ Cleared folder: logs/"
    else
        echo "❌ Error clearing logs folder"
    fi
else
    echo "📂 Folder logs/ doesn't exist, skipping"
fi

# Recreate logs folder
mkdir -p "logs"
echo "📁 Recreated empty folder: logs/"

# Clear storage folder
if [ -d "storage" ]; then
    echo "🗑️  Removing storage folder..."
    rm -rf "storage"
    if [ $? -eq 0 ]; then
        echo "✅ Cleared folder: storage/"
    else
        echo "❌ Error clearing storage folder"
    fi
else
    echo "📂 Folder storage/ doesn't exist, skipping"
fi

# Recreate storage folder
mkdir -p "storage"
echo "📁 Recreated empty folder: storage/"

echo ""
echo "✅ Data cleanup completed successfully!"
echo "   - logs/ folder cleared and recreated"
echo "   - storage/ folder cleared and recreated"
echo "   - Ready for fresh data collection"