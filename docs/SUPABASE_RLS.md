# Row Level Security (RLS) Setup for Supabase

This document explains how Row Level Security is implemented in this application and how to set it up on Supabase.

## Overview

Row Level Security (RLS) is a PostgreSQL feature that allows you to control which rows users can access in database tables. This is a critical security feature for Supabase applications, as it ensures that users can only access data they're authorized to see.

## Security Model

The application uses a role-based security model with two types of users:

- **Admins** (`role='admin'`): Full access to all data
- **Students** (`role='student'`): Limited access to their own data only

### Access Rules by Table

| Table | Students (Read) | Students (Write) | Admins (Read) | Admins (Write) |
|-------|----------------|------------------|---------------|----------------|
| user | Own record only | Own record only | All users | All users |
| class | Enrolled classes | None | All classes | All classes |
| class_students | Own enrollments | None | All enrollments | All enrollments |
| assigned_reading | Own class reading | None | All assignments | All assignments |
| book | All books | None | All books | All books |
| reading_list_item | Own list | Own list | All lists | All lists |
| book_read | Own records | Own records | All records | All records |
| review | Own reviews | Own reviews | All reviews | All reviews |
| suggested_book | Own suggestions | Accept/Reject only | All suggestions | All suggestions |
| book_suggestion | Own suggestions | Own pending | All suggestions | All suggestions |
| book_edit_suggestion | Own suggestions | Own pending | All suggestions | All suggestions |
| genre | All genres | None | All genres | All genres |
| sub_genre | All sub-genres | None | All sub-genres | All sub-genres |
| topic | All topics | None | All topics | All topics |
| genre_map | All mappings | None | All mappings | All mappings |

## Prerequisites

Before enabling RLS, you need to:

1. **Set up Supabase Auth Integration**
   - Configure Supabase authentication in your project
   - Ensure user IDs in the `user` table match Supabase Auth UIDs
   - Set up auth.uid() to return the current user's ID

2. **Migrate Database to Supabase**
   - Export your local database
   - Import into Supabase
   - Verify all data is present

## Migration Steps

### Method 1: Using the Python Migration Script (Recommended)

```bash
# Ensure you're connected to your Supabase database
# Set DATABASE_URL to your Supabase connection string
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres"

# Run the migration (from project root)
python migrations/migrate_add_rls.py
```

### Method 2: Manual SQL Execution via Supabase Dashboard

1. Log into your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of `migrations/migrate_add_rls.sql`
4. Paste into the SQL editor
5. Click **Run** to execute

### Method 3: Using psql CLI

```bash
# Connect to your Supabase database
psql "postgresql://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres"

# Run the migration file (from project root)
\i migrations/migrate_add_rls.sql

# Exit
\q
```

## Important Notes on auth.uid()

The RLS policies use `auth.uid()` to identify the current user. This function:

- Returns the UUID of the authenticated user from Supabase Auth
- Is cast to integer to match your user.id column: `auth.uid()::integer`
- Returns NULL for unauthenticated requests

### Syncing User IDs

Your application must ensure that:

```sql
-- The user.id in your database matches the Supabase Auth UID
-- When creating users via Supabase Auth, insert them into your user table:

INSERT INTO "user" (id, username, email, role, ...)
VALUES (
  auth.uid()::integer,  -- Use the Supabase Auth UID
  'username',
  'email@example.com',
  'student',
  ...
);
```

**Alternative Approach**: If you can't sync IDs, you'll need to create a mapping table or modify the policies to use email/username instead.

## Verification

After applying the migration, verify RLS is working:

### 1. Check RLS is Enabled

```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;
```

All tables should show `rowsecurity = true`.

### 2. View All Policies

```sql
SELECT schemaname, tablename, policyname 
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

You should see policies for all tables.

### 3. Test Student Access

Connect as a student user and try:

```sql
-- Should only return the student's own data
SELECT * FROM reading_list_item;
SELECT * FROM book_read;
SELECT * FROM review;

-- Should return all books (public data)
SELECT * FROM book;

-- Should only return classes the student is enrolled in
SELECT * FROM class;

-- Should fail (no access to other students' data)
SELECT * FROM "user" WHERE id != auth.uid()::integer;
```

### 4. Test Admin Access

Connect as an admin user and try:

```sql
-- Should return all data
SELECT * FROM "user";
SELECT * FROM reading_list_item;
SELECT * FROM book_read;

-- Should be able to modify any data
UPDATE book SET title = 'Test' WHERE id = 1;
```

## Troubleshooting

### Problem: Policies not working / Users can see all data

**Solution**: Ensure auth.uid() returns the correct user ID:

```sql
-- Check what auth.uid() returns when you're logged in
SELECT auth.uid();

-- Verify it matches your user table
SELECT id, username, role FROM "user" WHERE id = auth.uid()::integer;
```

### Problem: Users can't access any data

**Solution**: Check that:
1. User is authenticated (auth.uid() is not NULL)
2. User exists in the user table with correct ID
3. Policies are created correctly

```sql
-- View policies for a specific table
SELECT * FROM pg_policies WHERE tablename = 'book';
```

### Problem: Need to disable RLS temporarily for testing

```sql
-- Disable RLS on a table (use with caution!)
ALTER TABLE book DISABLE ROW LEVEL SECURITY;

-- Re-enable when done
ALTER TABLE book ENABLE ROW LEVEL SECURITY;
```

### Problem: Migration fails with "already exists" errors

This is normal if you're re-running the migration. The script will skip existing policies and continue. If you need to completely reset:

```sql
-- Drop all policies on a table (example for book table)
DROP POLICY IF EXISTS "All users can view books" ON book;
DROP POLICY IF EXISTS "Admins can insert books" ON book;
-- ... repeat for all policies

-- Then re-run the migration
```

## Application Code Changes

After enabling RLS, you may need to modify your application code:

### 1. Database Connection

Ensure your application connects with proper authentication:

```python
# In config.py - add Supabase connection
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
```

### 2. Service Role vs User Role

Supabase provides two types of keys:
- **Service Role Key**: Bypasses RLS (use for admin operations)
- **Anon Key**: Respects RLS (use for user operations)

For this Flask app, you'll typically use the Service Role Key for the database connection since the application handles authorization. The RLS policies act as a safety net.

### 3. Testing RLS in Development

You can simulate RLS in development by setting the user context:

```sql
-- Set the current user for testing
SET request.jwt.claim.sub = '1';  -- User ID 1

-- Now queries will be filtered as if user 1 was making them
SELECT * FROM reading_list_item;  -- Only user 1's items
```

## Additional Security Considerations

1. **API Keys**: Keep your Supabase keys secret
2. **Service Role**: Only use service role key server-side
3. **Anon Key**: Safe to use in client-side code
4. **Functions**: Create SECURITY DEFINER functions carefully
5. **Triggers**: Can bypass RLS - use with caution

## Rollback

If you need to remove RLS:

```sql
-- Disable RLS on all tables
DO $$ 
DECLARE 
  r RECORD;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    EXECUTE 'ALTER TABLE ' || quote_ident(r.tablename) || ' DISABLE ROW LEVEL SECURITY';
  END LOOP;
END $$;

-- Drop all policies
DO $$ 
DECLARE 
  r RECORD;
BEGIN
  FOR r IN SELECT schemaname, tablename, policyname 
           FROM pg_policies 
           WHERE schemaname = 'public'
  LOOP
    EXECUTE 'DROP POLICY IF EXISTS ' || quote_ident(r.policyname) || 
            ' ON ' || quote_ident(r.tablename);
  END LOOP;
END $$;
```

## Resources

- [Supabase RLS Documentation](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)

## Summary

After completing this setup:

1. ✅ All tables have RLS enabled
2. ✅ Students can only access their own data
3. ✅ Admins can access all data
4. ✅ Public data (books, genres) is accessible to all authenticated users
5. ✅ Database is secure even if API keys are compromised
