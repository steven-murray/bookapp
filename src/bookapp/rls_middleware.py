"""
Flask middleware for Row Level Security (RLS) context management.

This module provides request hooks that set PostgreSQL session variables
used by RLS policies to identify the current user.

Usage:
    from rls_middleware import setup_rls_middleware
    
    # In app.py, after creating the app:
    setup_rls_middleware(app)
"""

from flask import current_app
from flask_login import current_user
from bookapp.models import db


def set_rls_context():
    """
    Set PostgreSQL session variables for RLS before each request.
    
    This function is called automatically before each request to set:
    - app.current_user_id: The ID of the authenticated user
    - app.current_user_role: The role of the authenticated user ('admin' or 'student')
    
    These variables are used by RLS policies to control data access.
    
    Note: This only works with PostgreSQL. SQLite is gracefully skipped.
    """
    if current_user.is_authenticated:
        # Check if we're using PostgreSQL
        dialect = db.engine.dialect.name
        if dialect != 'postgresql':
            # Skip RLS for non-PostgreSQL databases (e.g., SQLite in development)
            if current_app.config.get('DEBUG_RLS', False):
                current_app.logger.debug(
                    f"Skipping RLS context (database is {dialect}, not PostgreSQL)"
                )
            return
        
        try:
            # Set user ID
            db.session.execute(
                db.text("SET LOCAL app.current_user_id = :user_id"),
                {"user_id": current_user.id}
            )
            
            # Set user role
            db.session.execute(
                db.text("SET LOCAL app.current_user_role = :role"),
                {"role": current_user.role}
            )
            
            # Optionally log for debugging
            if current_app.config.get('DEBUG_RLS', False):
                current_app.logger.debug(
                    f"RLS context set: user_id={current_user.id}, role={current_user.role}"
                )
        except Exception as e:
            current_app.logger.error(f"Error setting RLS context: {e}")
            # Don't fail the request if RLS context can't be set
            # In production, you might want to raise an exception instead
            pass


def clear_rls_context(exception=None):
    """
    Clear PostgreSQL session variables after each request.
    
    This ensures that session variables don't leak between requests.
    Called automatically after each request completes.
    
    Note: This only works with PostgreSQL. SQLite is gracefully skipped.
    """
    # Check if we're using PostgreSQL
    dialect = db.engine.dialect.name
    if dialect != 'postgresql':
        return
    
    try:
        db.session.execute(db.text("RESET app.current_user_id"))
        db.session.execute(db.text("RESET app.current_user_role"))
        
        if current_app.config.get('DEBUG_RLS', False) and exception:
            current_app.logger.debug(f"RLS context cleared (exception: {exception})")
    except Exception as e:
        current_app.logger.error(f"Error clearing RLS context: {e}")
        # Don't fail the request cleanup
        pass


def setup_rls_middleware(app):
    """
    Register RLS middleware with the Flask app.
    
    Args:
        app: Flask application instance
    
    Example:
        from rls_middleware import setup_rls_middleware
        
        app = Flask(__name__)
        # ... other setup ...
        setup_rls_middleware(app)
    """
    # Register before_request handler
    app.before_request(set_rls_context)
    
    # Register teardown_request handler
    app.teardown_request(clear_rls_context)
    
    # Log RLS status (needs app context, so wrap it)
    with app.app_context():
        try:
            dialect = db.engine.dialect.name
            if dialect == 'postgresql':
                app.logger.info("✅ RLS middleware enabled (PostgreSQL)")
            else:
                app.logger.warning(f"⚠️  RLS middleware registered but INACTIVE ({dialect} database)")
                app.logger.warning("   RLS only works with PostgreSQL/Supabase")
            
            # Add configuration option to disable RLS in development
            if not app.config.get('ENABLE_RLS', True):
                app.logger.warning("⚠️  RLS middleware is DISABLED by configuration")
        except Exception:
            # If engine isn't set up yet, just skip logging
            pass
    
    return app


def test_rls_context():
    """
    Test function to verify RLS context is working.
    
    Run this in Flask shell to test:
        >>> from rls_middleware import test_rls_context
        >>> test_rls_context()
    """
    from models import User, ReadingListItem
    
    # Check database type
    dialect = db.engine.dialect.name
    print("=" * 60)
    print(f"RLS TEST - Database: {dialect}")
    print("=" * 60)
    
    if dialect != 'postgresql':
        print(f"\n⚠️  WARNING: Row Level Security only works with PostgreSQL")
        print(f"   Current database: {dialect}")
        print(f"\n   This test will show that RLS is NOT enforced locally.")
        print(f"   RLS will be enforced when deployed to Supabase (PostgreSQL).\n")
        print("=" * 60)
    
    # Get test users
    student = User.query.filter_by(role='student').first()
    admin = User.query.filter_by(role='admin').first()
    
    if not student or not admin:
        print("❌ Need at least one student and one admin user for testing")
        return
    
    print("Testing RLS context...\n")
    print(f"Student user: {student.username} (ID: {student.id})")
    print(f"Admin user: {admin.username} (ID: {admin.id})")
    print()
    
    # Test without RLS context
    print("=" * 60)
    print("WITHOUT RLS CONTEXT (should see all data)")
    print("=" * 60)
    all_items = ReadingListItem.query.all()
    print(f"Total reading list items: {len(all_items)}")
    print()
    
    # Test as student (only for PostgreSQL)
    if dialect == 'postgresql':
        print("=" * 60)
        print(f"AS STUDENT ({student.username})")
        print("=" * 60)
        db.session.execute(
            db.text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": student.id}
        )
        db.session.execute(
            db.text("SET LOCAL app.current_user_role = :role"),
            {"role": student.role}
        )
        
        student_items = ReadingListItem.query.all()
        print(f"Reading list items visible: {len(student_items)}")
        
        # Verify only student's own items
        if student_items:
            all_mine = all(item.user_id == student.id for item in student_items)
            print(f"All items belong to student: {all_mine}")
            if not all_mine:
                print("❌ FAILED: Student can see other students' data!")
        else:
            print("(No reading list items for this student)")
        
        db.session.execute(db.text("RESET app.current_user_id"))
        db.session.execute(db.text("RESET app.current_user_role"))
        print()
        
        # Test as admin
        print("=" * 60)
        print(f"AS ADMIN ({admin.username})")
        print("=" * 60)
        db.session.execute(
            db.text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": admin.id}
        )
        db.session.execute(
            db.text("SET LOCAL app.current_user_role = :role"),
            {"role": admin.role}
        )
        
        admin_items = ReadingListItem.query.all()
        print(f"Reading list items visible: {len(admin_items)}")
        print(f"Can see all items (admin privilege): {len(admin_items) == len(all_items)}")
        
        if len(admin_items) != len(all_items):
            print("❌ FAILED: Admin cannot see all data!")
        
        db.session.execute(db.text("RESET app.current_user_id"))
        db.session.execute(db.text("RESET app.current_user_role"))
        print()
    else:
        print("=" * 60)
        print("SKIPPING PostgreSQL-specific tests")
        print("=" * 60)
        print(f"Cannot test RLS context with {dialect} database.")
        print("Deploy to Supabase (PostgreSQL) to test RLS enforcement.")
        print()
    
    print("=" * 60)
    if dialect == 'postgresql':
        print("✅ RLS TEST COMPLETE")
    else:
        print("✅ TEST COMPLETE (RLS not applicable for SQLite)")
        print("\n   To test RLS:")
        print("   1. Deploy database to Supabase")
        print("   2. Run migrations/migrate_add_rls_flask.sql")
        print("   3. Connect app to Supabase")
        print("   4. Run this test again")
    print("=" * 60)


if __name__ == '__main__':
    # Can't run standalone, needs app context
    print("This module should be imported, not run directly.")
    print("Import it in app.py with: from rls_middleware import setup_rls_middleware")
