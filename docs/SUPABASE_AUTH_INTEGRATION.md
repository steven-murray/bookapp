# Supabase Auth Integration Guide

This guide shows how to integrate Supabase Authentication with your Flask application to enable Row Level Security (RLS).

## Overview

Currently, the application uses Flask-Login for authentication. To use Supabase RLS, you have two options:

1. **Hybrid Approach (Recommended)**: Keep Flask-Login but sync with Supabase Auth
2. **Full Migration**: Replace Flask-Login with Supabase Auth SDK

This guide covers the **Hybrid Approach** which is simpler and maintains your existing code.

## Prerequisites

- Supabase project created
- Database migrated to Supabase
- RLS policies applied (see docs/SUPABASE_RLS.md)

## Step 1: Install Supabase Client

```bash
pip install supabase
```

Update `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "supabase>=2.0.0",
]
```

## Step 2: Configure Supabase in config.py

Add Supabase configuration to your `config.py`:

```python
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Existing database config
    _db_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URI')
    if _db_url and _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url or 'sqlite:///' + os.path.join(basedir, 'bookapp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # NEW: Supabase configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY')  # For client-side operations
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')  # For server-side operations
    
    OPENLIBRARY_API_URL = 'https://openlibrary.org'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
```

## Step 3: Add Environment Variables

Create/update your `.env` file:

```bash
# Database connection
DATABASE_URL=postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:6543/postgres

# Supabase configuration
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=eyJhbGc...  # Get from Supabase dashboard > Settings > API
SUPABASE_SERVICE_KEY=eyJhbGc...  # Get from Supabase dashboard > Settings > API

# Flask secret key
SECRET_KEY=your-secret-key-here
```

⚠️ **Security Note**: The service key bypasses RLS - only use it server-side!

## Step 4: Create Supabase Utility Module

Create a new file `supabase_utils.py`:

```python
"""
Supabase authentication utilities for RLS integration.
"""
from supabase import create_client, Client
from flask import g
from config import Config

# Initialize Supabase client
supabase: Client = None

def init_supabase(app=None):
    """Initialize Supabase client"""
    global supabase
    
    if app:
        url = app.config.get('SUPABASE_URL')
        key = app.config.get('SUPABASE_SERVICE_KEY')  # Use service key for server operations
    else:
        url = Config.SUPABASE_URL
        key = Config.SUPABASE_SERVICE_KEY
    
    if url and key:
        supabase = create_client(url, key)
        return supabase
    else:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")


def set_user_context(user_id):
    """
    Set the RLS context for the current database session.
    This makes RLS policies think this user is making the request.
    
    Args:
        user_id: The ID of the user to impersonate for RLS
    """
    from models import db
    
    # Set the PostgreSQL session variable that RLS uses
    # This is a simplified approach - in production you'd use JWT
    sql = f"SET LOCAL request.jwt.claim.sub = '{user_id}';"
    db.session.execute(db.text(sql))


def clear_user_context():
    """Clear the RLS user context"""
    from models import db
    
    sql = "RESET request.jwt.claim.sub;"
    db.session.execute(db.text(sql))
```

## Step 5: Update User Model for Supabase Sync

Add methods to `models.py` User class:

```python
class User(UserMixin, db.Model):
    # ... existing fields ...
    
    supabase_user_id = db.Column(db.String(255))  # Optional: store Supabase UUID
    
    # ... existing methods ...
    
    @staticmethod
    def create_with_supabase(username, email, password, role='student', first_name='', last_name=''):
        """
        Create a user in both Flask and Supabase Auth.
        Returns the created user or None if creation fails.
        """
        from supabase_utils import supabase
        
        try:
            # Create user in Supabase Auth
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })
            
            if auth_response.user:
                # Create user in our database
                user = User(
                    id=int(auth_response.user.id, 16) % 2147483647,  # Convert UUID to int
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    supabase_user_id=auth_response.user.id
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                return user
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user with Supabase: {e}")
            return None
    
    def sync_to_supabase(self):
        """Sync existing user to Supabase Auth (for migration)"""
        from supabase_utils import supabase
        
        try:
            # Create user in Supabase with admin API
            # Note: This requires Supabase service key
            auth_response = supabase.auth.admin.create_user({
                "email": self.email,
                "email_confirm": True,
                "user_metadata": {
                    "username": self.username,
                    "role": self.role,
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                }
            })
            
            if auth_response.user:
                self.supabase_user_id = auth_response.user.id
                db.session.commit()
                return True
        except Exception as e:
            print(f"Error syncing user to Supabase: {e}")
            return False
```

## Step 6: Update Database Schema

Add the new field to your database:

```python
# In your migration script or via SQL
ALTER TABLE "user" ADD COLUMN supabase_user_id VARCHAR(255);
```

## Step 7: Middleware to Set RLS Context (Optional)

If you want to enforce RLS even in your Flask app, add this middleware to `app.py`:

```python
from supabase_utils import init_supabase, set_user_context, clear_user_context

# Initialize Supabase
init_supabase(app)

@app.before_request
def set_rls_context():
    """Set RLS context for authenticated users"""
    if current_user.is_authenticated:
        # Only set context for non-admin users in production
        # This ensures RLS is tested
        if not current_user.is_admin() and app.config.get('ENFORCE_RLS', False):
            set_user_context(current_user.id)

@app.teardown_request
def clear_rls_context(exception=None):
    """Clear RLS context after request"""
    try:
        clear_user_context()
    except:
        pass
```

## Alternative: Simple Approach Without Full Supabase Auth

If you just want RLS to work but don't want to integrate Supabase Auth yet, you can use this simplified approach:

### Option A: Service Role Connection (Bypasses RLS)

Use the Supabase service key in your connection string. RLS won't apply, but it's still there as a safety net:

```python
# In config.py
# Use service key in connection string (get from Supabase dashboard)
SQLALCHEMY_DATABASE_URI = "postgresql://postgres.[PROJECT-REF]:[SERVICE-KEY]@[HOST]:6543/postgres"
```

### Option B: Create a Custom RLS Context Function

Modify the `is_admin()` function in the migration to work with session variables you set:

```sql
-- In migrations/migrate_add_rls.sql, replace the is_admin() function with:

CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
  -- Check session variable set by application
  RETURN COALESCE(
    (current_setting('app.current_user_role', true) = 'admin'),
    false
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS INTEGER AS $$
BEGIN
  RETURN COALESCE(
    current_setting('app.current_user_id', true)::integer,
    -1  -- Return -1 for unauthenticated
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

Then in your Flask app:

```python
@app.before_request
def set_user_session():
    """Set PostgreSQL session variables for RLS"""
    if current_user.is_authenticated:
        db.session.execute(
            db.text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": current_user.id}
        )
        db.session.execute(
            db.text("SET LOCAL app.current_user_role = :role"),
            {"role": current_user.role}
        )
```

And update all RLS policies to use `get_current_user_id()` instead of `auth.uid()::integer`:

```sql
-- Example: Update reading_list_item policies
DROP POLICY IF EXISTS "Users can view own reading list" ON reading_list_item;
CREATE POLICY "Users can view own reading list"
  ON reading_list_item
  FOR SELECT
  USING (user_id = get_current_user_id());
```

## Testing RLS

Create a test script `test_rls.py`:

```python
"""Test RLS policies"""
from app import app
from models import db, User, Book, ReadingListItem
from supabase_utils import set_user_context, clear_user_context

with app.app_context():
    # Get a student user
    student = User.query.filter_by(role='student').first()
    admin = User.query.filter_by(role='admin').first()
    
    print("Testing RLS...")
    print(f"Student ID: {student.id}")
    print(f"Admin ID: {admin.id}")
    
    # Test as student
    set_user_context(student.id)
    student_items = ReadingListItem.query.all()
    print(f"\nAs student: Can see {len(student_items)} reading list items")
    
    # Test as admin
    clear_user_context()
    set_user_context(admin.id)
    admin_items = ReadingListItem.query.all()
    print(f"As admin: Can see {len(admin_items)} reading list items")
    
    clear_user_context()
```

## Migration Checklist

- [ ] Install Supabase Python client
- [ ] Add Supabase environment variables
- [ ] Add `supabase_user_id` column to user table
- [ ] Apply RLS migration (migrations/migrate_add_rls.sql)
- [ ] Choose integration approach (full Supabase Auth or session variables)
- [ ] Test RLS with student and admin users
- [ ] Update registration flow if using Supabase Auth
- [ ] Document which approach you chose

## Troubleshooting

**RLS blocks all queries**: Check that session variables are being set correctly

```sql
-- Check current session variables
SELECT current_setting('app.current_user_id', true);
SELECT current_setting('app.current_user_role', true);
```

**Can't create users**: Make sure you're using the service key for admin operations

**Local development**: Consider disabling RLS locally:
```python
# In config.py for local development
ENFORCE_RLS = os.environ.get('ENFORCE_RLS', 'false').lower() == 'true'
```

## Resources

- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [PostgreSQL Session Variables](https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADMIN-SET)
