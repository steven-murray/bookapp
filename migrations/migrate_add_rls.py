"""
Migration script to enable Row Level Security (RLS) on all tables.

This script applies RLS policies to secure the database for Supabase deployment.
It reads the SQL file and executes it against the database.

IMPORTANT: This should only be run AFTER setting up Supabase Auth integration.
"""
import os
from bookapp.app import app
from bookapp.models import db


def migrate():
    with app.app_context():
        print("=" * 80)
        print("ENABLING ROW LEVEL SECURITY")
        print("=" * 80)
        
        # Read the SQL migration file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file = os.path.join(script_dir, 'migrate_add_rls.sql')
        
        if not os.path.exists(sql_file):
            print(f"❌ Error: {sql_file} not found.")
            print("   Please ensure the SQL file exists in the migrations/ directory.")
            return
        
        print(f"\nReading SQL migration from {sql_file}...")
        
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Split by statement (simple approach - assumes statements end with ;)
        # Filter out comments and empty lines
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            # Skip comment-only lines
            if line.strip().startswith('--') or not line.strip():
                continue
            
            current_statement.append(line)
            
            # Check if line ends with semicolon (end of statement)
            if line.strip().endswith(';'):
                statement = '\n'.join(current_statement)
                statements.append(statement)
                current_statement = []
        
        print(f"Found {len(statements)} SQL statements to execute.\n")
        
        # Get database dialect
        dialect = db.engine.dialect.name
        
        if dialect != 'postgresql':
            print(f"⚠️  WARNING: This migration is designed for PostgreSQL (Supabase).")
            print(f"   Current database is: {dialect}")
            print(f"   RLS is only supported on PostgreSQL.\n")
            
            response = input("Do you want to continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return
        
        # Execute statements
        print("Executing RLS migration...\n")
        
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            # Get first meaningful line for display
            first_line = statement.strip().split('\n')[0][:60]
            
            try:
                db.session.execute(db.text(statement))
                db.session.commit()
                success_count += 1
                print(f"✅ [{i}/{len(statements)}] {first_line}...")
            except Exception as e:
                error_count += 1
                print(f"❌ [{i}/{len(statements)}] {first_line}...")
                print(f"   Error: {str(e)[:100]}")
                
                # Don't fail the entire migration on errors
                # Some statements might fail if already applied
                db.session.rollback()
                continue
        
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {error_count}")
        print(f"📊 Total: {len(statements)}")
        
        if error_count == 0:
            print("\n🎉 Row Level Security successfully enabled!")
        else:
            print("\n⚠️  Migration completed with some errors.")
            print("   This is normal if policies already exist.")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("1. Verify RLS is enabled:")
        print("   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';")
        print("\n2. View all policies:")
        print("   SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public';")
        print("\n3. Test with a student account to ensure access is properly restricted.")
        print("\n4. See docs/SUPABASE_RLS.md for more information.")
        print("=" * 80)


if __name__ == '__main__':
    migrate()
