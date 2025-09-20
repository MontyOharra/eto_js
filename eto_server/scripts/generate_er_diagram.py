#!/usr/bin/env python3
"""
Generate ER Diagram from SQLAlchemy Models
Creates a visual database schema diagram from the existing models
"""
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    # Try to import eralchemy2 (newer version)
    from eralchemy2 import render_er
    eralchemy_available = True
except ImportError:
    try:
        # Fallback to eralchemy (older version)
        from eralchemy import render_er
        eralchemy_available = True
    except ImportError:
        eralchemy_available = False

def generate_er_diagram_from_models():
    """Generate ER diagram from SQLAlchemy models"""
    if not eralchemy_available:
        print("❌ ERAlchemy not installed. Install with:")
        print("   pip install eralchemy2")
        print("   - OR -")
        print("   pip install eralchemy")
        return False
    
    try:
        # Import your models to register them with SQLAlchemy
        from shared.database.models import *
        from shared.database import BaseModel
        
        # Output file
        output_file = "database_schema.png"
        
        print("🔄 Generating ER diagram from SQLAlchemy models...")
        
        # Generate diagram from the Base metadata
        render_er(BaseModel.metadata, output_file)
        
        print(f"✅ ER diagram generated: {output_file}")
        print(f"📁 Location: {os.path.abspath(output_file)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating diagram: {e}")
        return False

def generate_er_diagram_from_database():
    """Generate ER diagram by connecting to the actual database"""
    if not eralchemy_available:
        print("❌ ERAlchemy not installed")
        return False
    
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL environment variable not set")
            return False
        
        output_file = "database_schema_live.png"
        
        print("🔄 Generating ER diagram from live database...")
        print(f"📡 Connecting to: {database_url.split('@')[1] if '@' in database_url else 'database'}")
        
        # Generate diagram from live database
        render_er(database_url, output_file)
        
        print(f"✅ ER diagram generated: {output_file}")
        print(f"📁 Location: {os.path.abspath(output_file)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating diagram from database: {e}")
        return False

def main():
    """Main function"""
    print("🗃️  ETO Database ER Diagram Generator")
    print("=" * 50)
    
    # Try models first (doesn't require database connection)
    print("\n1️⃣  Attempting to generate from SQLAlchemy models...")
    if generate_er_diagram_from_models():
        return
    
    # Fallback to live database
    print("\n2️⃣  Attempting to generate from live database...")
    if generate_er_diagram_from_database():
        return
    
    print("\n❌ Failed to generate ER diagram")
    print("\n💡 Alternative options:")
    print("   • Use SQL Server Management Studio Database Diagrams")
    print("   • Install ERAlchemy: pip install eralchemy2")
    print("   • Use online tools like dbdiagram.io with your SQL schema")

if __name__ == "__main__":
    main()