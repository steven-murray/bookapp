# Row Level Security (RLS) Implementation Guide

This directory contains everything needed to add Row Level Security to your Supabase database.

## 📋 Quick Overview

Row Level Security (RLS) is a PostgreSQL feature that restricts which rows users can access in database tables. For Supabase deployments, enabling RLS is **strongly recommended** as it provides database-level security even if your application has bugs.

## 🎯 What's Included

### SQL Migration Files

1. **`migrations/migrate_add_rls_flask.sql`** ⭐ **RECOMMENDED**
   - Uses Flask session variables for authentication
   - Works with your existing Flask-Login setup
   - No Supabase Auth integration required
   - Easiest to implement

2. **`migrations/migrate_add_rls.sql`**
   - Uses Supabase Auth (`auth.uid()`)
   - Requires full Supabase Auth integration
   - More complex to set up
   - Better for pure Supabase apps

### Python Files

3. **`migrations/migrate_add_rls.py`**
   - Python script to run the SQL migration
   - Reads `migrations/migrate_add_rls.sql` and executes it
   - Provides progress feedback

4. **`rls_middleware.py`** ⭐ **RECOMMENDED**
   - Flask middleware for RLS context
   - Sets session variables before each request
   - Works with `migrations/migrate_add_rls_flask.sql`
   - Includes test function

### Documentation Files

5. **`docs/SUPABASE_RLS.md`**
   - Comprehensive RLS documentation
   - Security model explanation
   - Testing and verification steps
   - Troubleshooting guide

6. **`docs/SUPABASE_AUTH_INTEGRATION.md`**
   - Guide for integrating Supabase Auth (optional)
   - Only needed if using `migrations/migrate_add_rls.sql`
   - Skip if using Flask-Login approach

7. **`docs/RLS_IMPLEMENTATION.md`** (this file)
   - Quick start guide
   - File descriptions
   - Implementation steps

## 🚀 Quick Start (Recommended Approach)

### Option A: Flask Session Variables (Easiest)

This is the recommended approach if you want to keep using Flask-Login.

#### Step 1: Apply the SQL Migration

Choose one method:

**Method 1: Supabase Dashboard (Easiest)**
```bash
# 1. Copy the contents of migrations/migrate_add_rls_flask.sql
# 2. Log into Supabase Dashboard
# 3. Go to SQL Editor
# 4. Paste and run the SQL
```

**Method 2: psql CLI**
```bash
# Connect to Supabase
psql "postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres"

# Run migration (from project root)
\i migrations/migrate_add_rls_flask.sql
\q
```

**Method 3: Python Script**
```bash
# Set environment variable
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres"

# Run migration (from project root)
python migrations/migrate_add_rls.py
```

#### Step 2: Add RLS Middleware to Your App

Add this to your `app.py` (after creating the Flask app):

```python
# At the top of app.py
from rls_middleware import setup_rls_middleware

# After db.init_app(app) and login_manager.init_app(app)
setup_rls_middleware(app)
```

That's it! RLS is now enabled.

#### Step 3: Test RLS

```bash
# In Flask shell
flask shell

>>> from rls_middleware import test_rls_context
>>> test_rls_context()
```

Expected output:
- Students can only see their own data
- Admins can see all data

### Option B: Supabase Auth Integration (Advanced)

If you want to fully integrate with Supabase Auth, follow the guide in `docs/SUPABASE_AUTH_INTEGRATION.md`.

## 🔒 Security Model Summary

| User Role | Books | Own Data | Other Users' Data |
|-----------|-------|----------|-------------------|
| Student   | Read All | Full Access | No Access |
| Admin     | Full Access | Full Access | Full Access |

"Own Data" includes:
- Reading lists
- Books read
- Reviews
- Book suggestions
- Edit suggestions

## 📝 Configuration Options

Add these to your `config.py`:

```python
class Config:
    # ... existing config ...
    
    # Enable/disable RLS enforcement
    ENABLE_RLS = os.environ.get('ENABLE_RLS', 'true').lower() == 'true'
    
    # Debug RLS context (logs user context on each request)
    DEBUG_RLS = os.environ.get('DEBUG_RLS', 'false').lower() == 'true'
```

In your `.env` file:

```bash
# Production (Supabase)
ENABLE_RLS=true
DEBUG_RLS=false

# Development (local SQLite)
ENABLE_RLS=false
DEBUG_RLS=true
```

## ✅ Verification Checklist

After setup, verify:

- [ ] SQL migration ran without errors
- [ ] All tables have RLS enabled
- [ ] RLS middleware is registered in app.py
- [ ] Test function shows correct access control
- [ ] Students can only see their own data
- [ ] Admins can see all data
- [ ] Anonymous users can't access anything

Run verification queries:

```sql
-- Check RLS is enabled on all tables
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
-- All should show rowsecurity = true

-- Count policies
SELECT tablename, COUNT(*) as policy_count
FROM pg_policies 
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;
-- Should have policies on each table

-- Test functions exist
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
  AND routine_name IN ('get_current_user_id', 'get_current_user_role', 'is_admin');
-- Should return 3 rows
```

## 🐛 Troubleshooting

### Problem: Migration fails with "permission denied"

**Solution**: Make sure you're using the service role key, not the anon key.

```bash
# Get service role key from Supabase Dashboard > Settings > API
# Use it in connection string
```

### Problem: RLS blocks all queries

**Solution**: Check that session variables are being set:

```python
# Add this to a route temporarily
from flask import jsonify
from models import db

@app.route('/test-rls')
def test_rls():
    result = db.session.execute(db.text("""
        SELECT 
            current_setting('app.current_user_id', true) as user_id,
            current_setting('app.current_user_role', true) as role,
            get_current_user_id() as func_user_id,
            get_current_user_role() as func_role
    """)).fetchone()
    return jsonify({
        'user_id': result[0],
        'role': result[1],
        'func_user_id': result[2],
        'func_role': result[3]
    })
```

### Problem: Works in development but not production

**Solution**: Make sure RLS middleware is enabled in production:

```python
# In config.py
class ProductionConfig(Config):
    ENABLE_RLS = True  # Force enable in production
```

### Problem: "function get_current_user_id() does not exist"

**Solution**: The SQL migration didn't complete. Re-run it.

```bash
# Check if functions exist
psql [...connection string...] -c "SELECT routine_name FROM information_schema.routines WHERE routine_name LIKE 'get_current%';"
```

## 📚 Additional Resources

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)

## 🔄 Migration Path

If you're already deployed without RLS:

1. Test RLS locally first with SQLite (won't actually enforce, but won't break)
2. Apply RLS to Supabase staging/test database
3. Test thoroughly with different user roles
4. Apply to production during low-traffic window
5. Monitor logs for any RLS-related errors

## 🎉 Success Criteria

You've successfully implemented RLS when:

1. ✅ All tables have `rowsecurity = true`
2. ✅ Each table has appropriate policies
3. ✅ Students can only query their own data
4. ✅ Admins can query all data
5. ✅ No errors in application logs
6. ✅ Test function passes all checks

## 💡 Tips

- **Start simple**: Use the Flask session approach first
- **Test thoroughly**: Use the provided test function
- **Monitor logs**: Watch for RLS-related errors
- **Disable in development**: Set `ENABLE_RLS=false` locally
- **Document changes**: Note which approach you chose

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review `docs/SUPABASE_RLS.md` for detailed information
3. Verify all functions and policies are created
4. Test with the provided test function
5. Check Supabase logs in the dashboard

## 📦 File Summary

| File | Purpose | Required |
|------|---------|----------|
| `migrations/migrate_add_rls_flask.sql` | SQL migration (Flask approach) | ✅ Yes |
| `rls_middleware.py` | Flask middleware | ✅ Yes |
| `docs/SUPABASE_RLS.md` | Documentation | 📖 Reference |
| `docs/RLS_IMPLEMENTATION.md` | This guide | 📖 Reference |
| `migrations/migrate_add_rls.sql` | SQL migration (Supabase Auth) | ❌ Alternative |
| `migrations/migrate_add_rls.py` | Python migration runner | ⚙️ Optional |
| `docs/SUPABASE_AUTH_INTEGRATION.md` | Supabase Auth guide | ❌ Alternative |

**Recommended minimum**: `migrations/migrate_add_rls_flask.sql` + `rls_middleware.py`

---

**Need help?** Review the documentation files or check the troubleshooting sections.
