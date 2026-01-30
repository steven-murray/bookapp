# Row Level Security Implementation Checklist

Use this checklist to track your RLS implementation progress.

## 📋 Pre-Implementation

- [ ] Supabase project created
- [ ] Database migrated to Supabase
- [ ] Connection string obtained
- [ ] Service role key obtained (for migration)
- [ ] Backup of current database created

## 🔧 Implementation

### Step 1: Apply SQL Migration

- [ ] Opened Supabase Dashboard
- [ ] Navigated to SQL Editor
- [ ] Copied contents of `migrations/migrate_add_rls_flask.sql`
- [ ] Pasted and executed SQL
- [ ] No errors in execution
- [ ] Verified RLS is enabled on all tables

**Verification query:**
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
```

- [ ] All tables show `rowsecurity = true`

### Step 2: Add Middleware to Flask App

- [ ] Created/copied `rls_middleware.py` to project root
- [ ] Added import to `app.py`: `from rls_middleware import setup_rls_middleware`
- [ ] Added middleware setup: `setup_rls_middleware(app)`
- [ ] Middleware placed after `login_manager.init_app(app)`

### Step 3: Configure Environment

- [ ] Added `ENABLE_RLS=true` to `.env`
- [ ] Added `DEBUG_RLS=false` to `.env` (production)
- [ ] Updated `config.py` with RLS configuration (optional)

### Step 4: Test RLS

- [ ] Started Flask app successfully
- [ ] No errors in startup logs
- [ ] Saw "✅ RLS middleware enabled" in logs

**Test in Flask shell:**
```bash
flask shell
>>> from rls_middleware import test_rls_context
>>> test_rls_context()
```

- [ ] Test function executed without errors
- [ ] Students can only see their own data
- [ ] Admins can see all data
- [ ] Authenticated users can view books

## ✅ Verification

### Database Checks

Run these queries in Supabase SQL Editor:

```sql
-- Check all tables have RLS enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
```
- [ ] All tables show `rowsecurity = true`

```sql
-- Count policies per table
SELECT tablename, COUNT(*) as policy_count
FROM pg_policies 
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;
```
- [ ] Each table has multiple policies
- [ ] Total policies: ~70+

```sql
-- Verify helper functions exist
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
  AND routine_name IN ('get_current_user_id', 'get_current_user_role', 'is_admin');
```
- [ ] 3 functions returned

### Application Testing

#### As Student User:

- [ ] Can log in successfully
- [ ] Can view own reading list
- [ ] Can add books to reading list
- [ ] Can mark books as read
- [ ] Can create reviews
- [ ] Can view own books read
- [ ] CANNOT see other students' data
- [ ] CANNOT modify other students' data
- [ ] CAN view all books
- [ ] CAN view enrolled classes only

#### As Admin User:

- [ ] Can log in successfully
- [ ] Can view all students
- [ ] Can view all reading lists
- [ ] Can view all books read
- [ ] Can view all reviews
- [ ] Can create/edit/delete books
- [ ] Can create/edit/delete classes
- [ ] Can assign books to classes
- [ ] Can suggest books to students
- [ ] Can manage all data

### Session Variables Test

Add this temporary route to `app.py`:

```python
@app.route('/test-rls-session')
@login_required
def test_rls_session():
    from flask import jsonify
    result = db.session.execute(db.text("""
        SELECT 
            get_current_user_id() as user_id,
            get_current_user_role() as role
    """)).fetchone()
    return jsonify({
        'current_user_id': current_user.id,
        'current_user_role': current_user.role,
        'db_user_id': result[0],
        'db_role': result[1],
        'match': result[0] == current_user.id and result[1] == current_user.role
    })
```

- [ ] Created test route
- [ ] Visited `/test-rls-session` while logged in
- [ ] Values match: `match = true`
- [ ] Removed test route after verification

## 🚀 Deployment

- [ ] Committed RLS files to git
- [ ] Updated `.env` for production
- [ ] Set `ENABLE_RLS=true` in production
- [ ] Set `DEBUG_RLS=false` in production
- [ ] Deployed to production environment
- [ ] Tested with student account in production
- [ ] Tested with admin account in production
- [ ] Monitored logs for RLS errors
- [ ] No errors in production logs

## 📝 Documentation

- [ ] Team notified of RLS implementation
- [ ] Documentation updated
- [ ] RLS approach documented (Flask session variables)
- [ ] Configuration documented

## 🔒 Security Verification

Final security checks:

- [ ] Service role key not exposed in code
- [ ] Service role key not in git repository
- [ ] Connection string uses environment variables
- [ ] `.env` file in `.gitignore`
- [ ] Students cannot access other students' data
- [ ] Admins can access all data
- [ ] Anonymous users cannot access any data
- [ ] RLS cannot be bypassed via API

## 📊 Performance Check

- [ ] No significant performance degradation
- [ ] Query times acceptable
- [ ] No RLS-related errors in logs
- [ ] Database connection pooling working

## 🎉 Completion

- [ ] All tests passing
- [ ] All users can access appropriate data
- [ ] No security issues found
- [ ] Documentation complete
- [ ] Team trained on RLS
- [ ] Ready for production use

## 🔄 Rollback Plan (If Needed)

If issues occur, rollback by:

1. **Disable RLS middleware:**
   ```python
   # In app.py, comment out:
   # setup_rls_middleware(app)
   ```

2. **Or disable via environment:**
   ```bash
   ENABLE_RLS=false
   ```

3. **Or disable in database (emergency only):**
   ```sql
   ALTER TABLE "user" DISABLE ROW LEVEL SECURITY;
   ALTER TABLE book DISABLE ROW LEVEL SECURITY;
   -- Repeat for all tables
   ```

- [ ] Rollback plan tested
- [ ] Rollback procedure documented
- [ ] Team knows rollback process

---

## Summary

**Total Steps:** ~60

**Completed:** ___ / 60

**Status:** 
- [ ] Not Started
- [ ] In Progress
- [ ] Testing
- [ ] Complete

**Date Started:** ___________

**Date Completed:** ___________

**Implemented By:** ___________

**Verified By:** ___________

---

## Notes

Add any notes, issues, or special configurations here:

```
[Your notes here]
```

---

## Next Steps After RLS

Once RLS is complete and verified:

- [ ] Consider adding Supabase Auth (optional)
- [ ] Set up automated backups
- [ ] Configure monitoring/alerting
- [ ] Review and optimize RLS policies
- [ ] Document any custom policies added
