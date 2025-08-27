#!/usr/bin/env python3
"""
Test database connection for ETO system
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from database import init_database, get_db_service
    
    print("Testing database connection...")
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment")
        sys.exit(1)
    
    print(f"✅ DATABASE_URL found")
    
    # Try to initialize database
    try:
        db_service = init_database(database_url)
        print("✅ Database initialized successfully")
        
        # Test a simple query
        session = db_service.get_session()
        try:
            # Try to count emails table
            from database import Email
            email_count = session.query(Email).count()
            print(f"✅ Database query successful - Found {email_count} emails")
            
            # Check if eto_runs table has the required columns
            from database import EtoRun
            
            # Try a simple query that uses the problematic columns
            pending_runs = session.query(EtoRun).filter(
                EtoRun.status == 'pending'
            ).count()
            print(f"✅ ETO runs query successful - Found {pending_runs} pending runs")
            
            print("\n🎉 Database connection test PASSED!")
            
        finally:
            session.close()
            
    except Exception as init_error:
        print(f"❌ Database initialization failed: {init_error}")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)