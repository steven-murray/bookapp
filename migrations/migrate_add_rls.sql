-- ============================================================================
-- Row Level Security (RLS) Migration for Bookapp
-- ============================================================================
-- This migration enables RLS on all tables and creates appropriate policies
-- for admin and student users based on the user.role column.
--
-- Security Model:
-- - Admins (role='admin') have full access to all tables
-- - Students (role='student') can only access their own data
-- - Public tables (books, genres, etc.) are readable by all authenticated users
-- - Metadata tables are admin-only for writes, readable by all
--
-- Run this migration AFTER your initial database setup.
-- ============================================================================

-- ============================================================================
-- ENABLE ROW LEVEL SECURITY ON ALL TABLES
-- ============================================================================

-- Enable RLS on user table
ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;

-- Enable RLS on class table
ALTER TABLE "class" ENABLE ROW LEVEL SECURITY;

-- Enable RLS on class_students association table
ALTER TABLE class_students ENABLE ROW LEVEL SECURITY;

-- Enable RLS on assigned_reading association table
ALTER TABLE assigned_reading ENABLE ROW LEVEL SECURITY;

-- Enable RLS on book table
ALTER TABLE book ENABLE ROW LEVEL SECURITY;

-- Enable RLS on reading_list_item table
ALTER TABLE reading_list_item ENABLE ROW LEVEL SECURITY;

-- Enable RLS on book_read table
ALTER TABLE book_read ENABLE ROW LEVEL SECURITY;

-- Enable RLS on review table
ALTER TABLE review ENABLE ROW LEVEL SECURITY;

-- Enable RLS on suggested_book table
ALTER TABLE suggested_book ENABLE ROW LEVEL SECURITY;

-- Enable RLS on book_suggestion table
ALTER TABLE book_suggestion ENABLE ROW LEVEL SECURITY;

-- Enable RLS on book_edit_suggestion table
ALTER TABLE book_edit_suggestion ENABLE ROW LEVEL SECURITY;

-- Enable RLS on genre table
ALTER TABLE genre ENABLE ROW LEVEL SECURITY;

-- Enable RLS on sub_genre table
ALTER TABLE sub_genre ENABLE ROW LEVEL SECURITY;

-- Enable RLS on topic table
ALTER TABLE topic ENABLE ROW LEVEL SECURITY;

-- Enable RLS on genre_map table
ALTER TABLE genre_map ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- HELPER FUNCTION: Check if current user is admin
-- ============================================================================

CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM "user"
    WHERE id = auth.uid()::integer
    AND role = 'admin'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================================================
-- USER TABLE POLICIES
-- ============================================================================

-- Students can view their own user record
CREATE POLICY "Students can view own profile"
  ON "user"
  FOR SELECT
  USING (id = auth.uid()::integer);

-- Admins can view all users
CREATE POLICY "Admins can view all users"
  ON "user"
  FOR SELECT
  USING (is_admin());

-- Students can update their own profile (limited fields)
CREATE POLICY "Students can update own profile"
  ON "user"
  FOR UPDATE
  USING (id = auth.uid()::integer)
  WITH CHECK (id = auth.uid()::integer);

-- Admins can insert new users
CREATE POLICY "Admins can insert users"
  ON "user"
  FOR INSERT
  WITH CHECK (is_admin());

-- Admins can update all users
CREATE POLICY "Admins can update all users"
  ON "user"
  FOR UPDATE
  USING (is_admin());

-- Admins can delete users
CREATE POLICY "Admins can delete users"
  ON "user"
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- CLASS TABLE POLICIES
-- ============================================================================

-- Students can view classes they're enrolled in
CREATE POLICY "Students can view enrolled classes"
  ON "class"
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM class_students
      WHERE class_students.class_id = class.id
      AND class_students.student_id = auth.uid()::integer
    )
  );

-- Admins can view all classes
CREATE POLICY "Admins can view all classes"
  ON "class"
  FOR SELECT
  USING (is_admin());

-- Admins can insert classes
CREATE POLICY "Admins can insert classes"
  ON "class"
  FOR INSERT
  WITH CHECK (is_admin());

-- Admins can update classes
CREATE POLICY "Admins can update classes"
  ON "class"
  FOR UPDATE
  USING (is_admin());

-- Admins can delete classes
CREATE POLICY "Admins can delete classes"
  ON "class"
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- CLASS_STUDENTS ASSOCIATION TABLE POLICIES
-- ============================================================================

-- Students can view their own class enrollments
CREATE POLICY "Students can view own enrollments"
  ON class_students
  FOR SELECT
  USING (student_id = auth.uid()::integer);

-- Admins can view all enrollments
CREATE POLICY "Admins can view all enrollments"
  ON class_students
  FOR SELECT
  USING (is_admin());

-- Admins can manage enrollments
CREATE POLICY "Admins can insert enrollments"
  ON class_students
  FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can delete enrollments"
  ON class_students
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- ASSIGNED_READING ASSOCIATION TABLE POLICIES
-- ============================================================================

-- Students can view assigned reading for their classes
CREATE POLICY "Students can view assigned reading"
  ON assigned_reading
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM class_students
      WHERE class_students.class_id = assigned_reading.class_id
      AND class_students.student_id = auth.uid()::integer
    )
  );

-- Admins can view all assigned reading
CREATE POLICY "Admins can view all assigned reading"
  ON assigned_reading
  FOR SELECT
  USING (is_admin());

-- Admins can manage assigned reading
CREATE POLICY "Admins can insert assigned reading"
  ON assigned_reading
  FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can delete assigned reading"
  ON assigned_reading
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- BOOK TABLE POLICIES
-- ============================================================================

-- All authenticated users can view books
CREATE POLICY "All users can view books"
  ON book
  FOR SELECT
  TO authenticated
  USING (true);

-- Admins can insert books
CREATE POLICY "Admins can insert books"
  ON book
  FOR INSERT
  WITH CHECK (is_admin());

-- Admins can update books
CREATE POLICY "Admins can update books"
  ON book
  FOR UPDATE
  USING (is_admin());

-- Admins can delete books
CREATE POLICY "Admins can delete books"
  ON book
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- READING_LIST_ITEM TABLE POLICIES
-- ============================================================================

-- Users can view their own reading list
CREATE POLICY "Users can view own reading list"
  ON reading_list_item
  FOR SELECT
  USING (user_id = auth.uid()::integer);

-- Admins can view all reading lists
CREATE POLICY "Admins can view all reading lists"
  ON reading_list_item
  FOR SELECT
  USING (is_admin());

-- Users can insert to their own reading list
CREATE POLICY "Users can insert to own reading list"
  ON reading_list_item
  FOR INSERT
  WITH CHECK (user_id = auth.uid()::integer);

-- Users can update their own reading list
CREATE POLICY "Users can update own reading list"
  ON reading_list_item
  FOR UPDATE
  USING (user_id = auth.uid()::integer)
  WITH CHECK (user_id = auth.uid()::integer);

-- Users can delete from their own reading list
CREATE POLICY "Users can delete from own reading list"
  ON reading_list_item
  FOR DELETE
  USING (user_id = auth.uid()::integer);

-- Admins can manage all reading lists
CREATE POLICY "Admins can insert all reading lists"
  ON reading_list_item
  FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update all reading lists"
  ON reading_list_item
  FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete all reading lists"
  ON reading_list_item
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- BOOK_READ TABLE POLICIES
-- ============================================================================

-- Users can view their own books read
CREATE POLICY "Users can view own books read"
  ON book_read
  FOR SELECT
  USING (user_id = auth.uid()::integer);

-- Admins can view all books read
CREATE POLICY "Admins can view all books read"
  ON book_read
  FOR SELECT
  USING (is_admin());

-- Users can mark books as read
CREATE POLICY "Users can mark books as read"
  ON book_read
  FOR INSERT
  WITH CHECK (user_id = auth.uid()::integer);

-- Users can update their own books read
CREATE POLICY "Users can update own books read"
  ON book_read
  FOR UPDATE
  USING (user_id = auth.uid()::integer)
  WITH CHECK (user_id = auth.uid()::integer);

-- Users can delete their own books read
CREATE POLICY "Users can delete own books read"
  ON book_read
  FOR DELETE
  USING (user_id = auth.uid()::integer);

-- Admins can manage all books read
CREATE POLICY "Admins can insert all books read"
  ON book_read
  FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update all books read"
  ON book_read
  FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete all books read"
  ON book_read
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- REVIEW TABLE POLICIES
-- ============================================================================

-- Users can view their own reviews
CREATE POLICY "Users can view own reviews"
  ON review
  FOR SELECT
  USING (user_id = auth.uid()::integer);

-- Admins can view all reviews
CREATE POLICY "Admins can view all reviews"
  ON review
  FOR SELECT
  USING (is_admin());

-- Users can create reviews
CREATE POLICY "Users can create reviews"
  ON review
  FOR INSERT
  WITH CHECK (user_id = auth.uid()::integer);

-- Users can update their own reviews
CREATE POLICY "Users can update own reviews"
  ON review
  FOR UPDATE
  USING (user_id = auth.uid()::integer)
  WITH CHECK (user_id = auth.uid()::integer);

-- Users can delete their own reviews
CREATE POLICY "Users can delete own reviews"
  ON review
  FOR DELETE
  USING (user_id = auth.uid()::integer);

-- Admins can manage all reviews
CREATE POLICY "Admins can update all reviews"
  ON review
  FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete all reviews"
  ON review
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- SUGGESTED_BOOK TABLE POLICIES
-- ============================================================================

-- Students can view suggestions made to them
CREATE POLICY "Students can view own suggestions"
  ON suggested_book
  FOR SELECT
  USING (student_id = auth.uid()::integer);

-- Admins can view all suggestions
CREATE POLICY "Admins can view all suggestions"
  ON suggested_book
  FOR SELECT
  USING (is_admin());

-- Admins can create suggestions
CREATE POLICY "Admins can create suggestions"
  ON suggested_book
  FOR INSERT
  WITH CHECK (is_admin());

-- Students can update their own suggestions (accept/reject)
CREATE POLICY "Students can update own suggestions"
  ON suggested_book
  FOR UPDATE
  USING (student_id = auth.uid()::integer)
  WITH CHECK (student_id = auth.uid()::integer);

-- Admins can update all suggestions
CREATE POLICY "Admins can update all suggestions"
  ON suggested_book
  FOR UPDATE
  USING (is_admin());

-- Admins can delete suggestions
CREATE POLICY "Admins can delete suggestions"
  ON suggested_book
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- BOOK_SUGGESTION TABLE POLICIES
-- ============================================================================

-- Students can view their own book suggestions
CREATE POLICY "Students can view own book suggestions"
  ON book_suggestion
  FOR SELECT
  USING (student_id = auth.uid()::integer);

-- Admins can view all book suggestions
CREATE POLICY "Admins can view all book suggestions"
  ON book_suggestion
  FOR SELECT
  USING (is_admin());

-- Students can create book suggestions
CREATE POLICY "Students can create book suggestions"
  ON book_suggestion
  FOR INSERT
  WITH CHECK (student_id = auth.uid()::integer);

-- Students can update their own pending book suggestions
CREATE POLICY "Students can update own book suggestions"
  ON book_suggestion
  FOR UPDATE
  USING (student_id = auth.uid()::integer AND status = 'pending')
  WITH CHECK (student_id = auth.uid()::integer AND status = 'pending');

-- Admins can update all book suggestions (review them)
CREATE POLICY "Admins can update all book suggestions"
  ON book_suggestion
  FOR UPDATE
  USING (is_admin());

-- Students can delete their own pending book suggestions
CREATE POLICY "Students can delete own book suggestions"
  ON book_suggestion
  FOR DELETE
  USING (student_id = auth.uid()::integer AND status = 'pending');

-- Admins can delete any book suggestion
CREATE POLICY "Admins can delete all book suggestions"
  ON book_suggestion
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- BOOK_EDIT_SUGGESTION TABLE POLICIES
-- ============================================================================

-- Students can view their own edit suggestions
CREATE POLICY "Students can view own edit suggestions"
  ON book_edit_suggestion
  FOR SELECT
  USING (student_id = auth.uid()::integer);

-- Admins can view all edit suggestions
CREATE POLICY "Admins can view all edit suggestions"
  ON book_edit_suggestion
  FOR SELECT
  USING (is_admin());

-- Students can create edit suggestions
CREATE POLICY "Students can create edit suggestions"
  ON book_edit_suggestion
  FOR INSERT
  WITH CHECK (student_id = auth.uid()::integer);

-- Students can update their own pending edit suggestions
CREATE POLICY "Students can update own edit suggestions"
  ON book_edit_suggestion
  FOR UPDATE
  USING (student_id = auth.uid()::integer AND status = 'pending')
  WITH CHECK (student_id = auth.uid()::integer AND status = 'pending');

-- Admins can update all edit suggestions (review them)
CREATE POLICY "Admins can update all edit suggestions"
  ON book_edit_suggestion
  FOR UPDATE
  USING (is_admin());

-- Students can delete their own pending edit suggestions
CREATE POLICY "Students can delete own edit suggestions"
  ON book_edit_suggestion
  FOR DELETE
  USING (student_id = auth.uid()::integer AND status = 'pending');

-- Admins can delete any edit suggestion
CREATE POLICY "Admins can delete all edit suggestions"
  ON book_edit_suggestion
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- GENRE TABLE POLICIES
-- ============================================================================

-- All authenticated users can view genres
CREATE POLICY "All users can view genres"
  ON genre
  FOR SELECT
  TO authenticated
  USING (true);

-- Admins can manage genres
CREATE POLICY "Admins can insert genres"
  ON genre
  FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update genres"
  ON genre
  FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete genres"
  ON genre
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- SUB_GENRE TABLE POLICIES
-- ============================================================================

-- All authenticated users can view sub-genres
CREATE POLICY "All users can view sub_genres"
  ON sub_genre
  FOR SELECT
  TO authenticated
  USING (true);

-- Admins can manage sub-genres
CREATE POLICY "Admins can insert sub_genres"
  ON sub_genre
  FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update sub_genres"
  ON sub_genre
  FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete sub_genres"
  ON sub_genre
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- TOPIC TABLE POLICIES
-- ============================================================================

-- All authenticated users can view topics
CREATE POLICY "All users can view topics"
  ON topic
  FOR SELECT
  TO authenticated
  USING (true);

-- Admins can manage topics
CREATE POLICY "Admins can insert topics"
  ON topic
  FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update topics"
  ON topic
  FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete topics"
  ON topic
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- GENRE_MAP TABLE POLICIES
-- ============================================================================

-- All authenticated users can view genre maps
CREATE POLICY "All users can view genre_maps"
  ON genre_map
  FOR SELECT
  TO authenticated
  USING (true);

-- Admins can manage genre maps
CREATE POLICY "Admins can insert genre_maps"
  ON genre_map
  FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update genre_maps"
  ON genre_map
  FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete genre_maps"
  ON genre_map
  FOR DELETE
  USING (is_admin());


-- ============================================================================
-- GRANT USAGE ON SEQUENCES TO AUTHENTICATED USERS
-- ============================================================================
-- This ensures users can insert records and get auto-generated IDs

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these queries to verify RLS is properly enabled:
--
-- SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
-- SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'public';
--
-- ============================================================================
