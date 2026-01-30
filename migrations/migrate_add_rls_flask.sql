-- ============================================================================
-- Row Level Security (RLS) Migration for Bookapp - Flask Session Approach
-- ============================================================================
-- This version uses PostgreSQL session variables instead of Supabase Auth.
-- This is ideal if you want to keep using Flask-Login without integrating
-- Supabase Auth.
--
-- Your Flask app will set session variables before each request:
--   SET LOCAL app.current_user_id = <user_id>;
--   SET LOCAL app.current_user_role = 'admin' or 'student';
--
-- Security Model:
-- - Admins (role='admin') have full access to all tables
-- - Students (role='student') can only access their own data
-- - Public tables (books, genres, etc.) are readable by all authenticated users
-- - Metadata tables are admin-only for writes, readable by all
-- ============================================================================

-- ============================================================================
-- ENABLE ROW LEVEL SECURITY ON ALL TABLES
-- ============================================================================

ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "class" ENABLE ROW LEVEL SECURITY;
ALTER TABLE class_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE assigned_reading ENABLE ROW LEVEL SECURITY;
ALTER TABLE book ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_list_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_read ENABLE ROW LEVEL SECURITY;
ALTER TABLE review ENABLE ROW LEVEL SECURITY;
ALTER TABLE suggested_book ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_suggestion ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_edit_suggestion ENABLE ROW LEVEL SECURITY;
ALTER TABLE genre ENABLE ROW LEVEL SECURITY;
ALTER TABLE sub_genre ENABLE ROW LEVEL SECURITY;
ALTER TABLE topic ENABLE ROW LEVEL SECURITY;
ALTER TABLE genre_map ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- HELPER FUNCTIONS: Get current user from session variables
-- ============================================================================

CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS INTEGER AS $$
BEGIN
  -- Return user ID from session variable, or -1 if not set
  RETURN COALESCE(nullif(current_setting('app.current_user_id', true), '')::integer, -1);
EXCEPTION
  WHEN OTHERS THEN
    RETURN -1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION get_current_user_role()
RETURNS TEXT AS $$
BEGIN
  -- Return user role from session variable, or 'anonymous' if not set
  RETURN COALESCE(nullif(current_setting('app.current_user_role', true), ''), 'anonymous');
EXCEPTION
  WHEN OTHERS THEN
    RETURN 'anonymous';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN get_current_user_role() = 'admin';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;


-- ============================================================================
-- USER TABLE POLICIES
-- ============================================================================

CREATE POLICY "Students can view own profile"
  ON "user" FOR SELECT
  USING (id = get_current_user_id());

CREATE POLICY "Admins can view all users"
  ON "user" FOR SELECT
  USING (is_admin());

CREATE POLICY "Students can update own profile"
  ON "user" FOR UPDATE
  USING (id = get_current_user_id())
  WITH CHECK (id = get_current_user_id());

CREATE POLICY "Admins can insert users"
  ON "user" FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update all users"
  ON "user" FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete users"
  ON "user" FOR DELETE
  USING (is_admin());


-- ============================================================================
-- CLASS TABLE POLICIES
-- ============================================================================

CREATE POLICY "Students can view enrolled classes"
  ON "class" FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM class_students
      WHERE class_students.class_id = class.id
      AND class_students.student_id = get_current_user_id()
    )
  );

CREATE POLICY "Admins can view all classes"
  ON "class" FOR SELECT
  USING (is_admin());

CREATE POLICY "Admins can insert classes"
  ON "class" FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update classes"
  ON "class" FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete classes"
  ON "class" FOR DELETE
  USING (is_admin());


-- ============================================================================
-- CLASS_STUDENTS ASSOCIATION TABLE POLICIES
-- ============================================================================

CREATE POLICY "Students can view own enrollments"
  ON class_students FOR SELECT
  USING (student_id = get_current_user_id());

CREATE POLICY "Admins can view all enrollments"
  ON class_students FOR SELECT
  USING (is_admin());

CREATE POLICY "Admins can insert enrollments"
  ON class_students FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can delete enrollments"
  ON class_students FOR DELETE
  USING (is_admin());


-- ============================================================================
-- ASSIGNED_READING ASSOCIATION TABLE POLICIES
-- ============================================================================

CREATE POLICY "Students can view assigned reading"
  ON assigned_reading FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM class_students
      WHERE class_students.class_id = assigned_reading.class_id
      AND class_students.student_id = get_current_user_id()
    )
  );

CREATE POLICY "Admins can view all assigned reading"
  ON assigned_reading FOR SELECT
  USING (is_admin());

CREATE POLICY "Admins can insert assigned reading"
  ON assigned_reading FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can delete assigned reading"
  ON assigned_reading FOR DELETE
  USING (is_admin());


-- ============================================================================
-- BOOK TABLE POLICIES
-- ============================================================================

CREATE POLICY "Authenticated users can view books"
  ON book FOR SELECT
  USING (get_current_user_id() > 0);

CREATE POLICY "Admins can insert books"
  ON book FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update books"
  ON book FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete books"
  ON book FOR DELETE
  USING (is_admin());


-- ============================================================================
-- READING_LIST_ITEM TABLE POLICIES
-- ============================================================================

CREATE POLICY "Users can view own reading list"
  ON reading_list_item FOR SELECT
  USING (user_id = get_current_user_id());

CREATE POLICY "Admins can view all reading lists"
  ON reading_list_item FOR SELECT
  USING (is_admin());

CREATE POLICY "Users can insert to own reading list"
  ON reading_list_item FOR INSERT
  WITH CHECK (user_id = get_current_user_id());

CREATE POLICY "Users can update own reading list"
  ON reading_list_item FOR UPDATE
  USING (user_id = get_current_user_id())
  WITH CHECK (user_id = get_current_user_id());

CREATE POLICY "Users can delete from own reading list"
  ON reading_list_item FOR DELETE
  USING (user_id = get_current_user_id());

CREATE POLICY "Admins can insert all reading lists"
  ON reading_list_item FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update all reading lists"
  ON reading_list_item FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete all reading lists"
  ON reading_list_item FOR DELETE
  USING (is_admin());


-- ============================================================================
-- BOOK_READ TABLE POLICIES
-- ============================================================================

CREATE POLICY "Users can view own books read"
  ON book_read FOR SELECT
  USING (user_id = get_current_user_id());

CREATE POLICY "Admins can view all books read"
  ON book_read FOR SELECT
  USING (is_admin());

CREATE POLICY "Users can mark books as read"
  ON book_read FOR INSERT
  WITH CHECK (user_id = get_current_user_id());

CREATE POLICY "Users can update own books read"
  ON book_read FOR UPDATE
  USING (user_id = get_current_user_id())
  WITH CHECK (user_id = get_current_user_id());

CREATE POLICY "Users can delete own books read"
  ON book_read FOR DELETE
  USING (user_id = get_current_user_id());

CREATE POLICY "Admins can insert all books read"
  ON book_read FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update all books read"
  ON book_read FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete all books read"
  ON book_read FOR DELETE
  USING (is_admin());


-- ============================================================================
-- REVIEW TABLE POLICIES
-- ============================================================================

CREATE POLICY "Users can view own reviews"
  ON review FOR SELECT
  USING (user_id = get_current_user_id());

CREATE POLICY "Admins can view all reviews"
  ON review FOR SELECT
  USING (is_admin());

CREATE POLICY "Users can create reviews"
  ON review FOR INSERT
  WITH CHECK (user_id = get_current_user_id());

CREATE POLICY "Users can update own reviews"
  ON review FOR UPDATE
  USING (user_id = get_current_user_id())
  WITH CHECK (user_id = get_current_user_id());

CREATE POLICY "Users can delete own reviews"
  ON review FOR DELETE
  USING (user_id = get_current_user_id());

CREATE POLICY "Admins can update all reviews"
  ON review FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete all reviews"
  ON review FOR DELETE
  USING (is_admin());


-- ============================================================================
-- SUGGESTED_BOOK TABLE POLICIES
-- ============================================================================

CREATE POLICY "Students can view own suggestions"
  ON suggested_book FOR SELECT
  USING (student_id = get_current_user_id());

CREATE POLICY "Admins can view all suggestions"
  ON suggested_book FOR SELECT
  USING (is_admin());

CREATE POLICY "Admins can create suggestions"
  ON suggested_book FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Students can update own suggestions"
  ON suggested_book FOR UPDATE
  USING (student_id = get_current_user_id())
  WITH CHECK (student_id = get_current_user_id());

CREATE POLICY "Admins can update all suggestions"
  ON suggested_book FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete suggestions"
  ON suggested_book FOR DELETE
  USING (is_admin());


-- ============================================================================
-- BOOK_SUGGESTION TABLE POLICIES
-- ============================================================================

CREATE POLICY "Students can view own book suggestions"
  ON book_suggestion FOR SELECT
  USING (student_id = get_current_user_id());

CREATE POLICY "Admins can view all book suggestions"
  ON book_suggestion FOR SELECT
  USING (is_admin());

CREATE POLICY "Students can create book suggestions"
  ON book_suggestion FOR INSERT
  WITH CHECK (student_id = get_current_user_id());

CREATE POLICY "Students can update own book suggestions"
  ON book_suggestion FOR UPDATE
  USING (student_id = get_current_user_id() AND status = 'pending')
  WITH CHECK (student_id = get_current_user_id() AND status = 'pending');

CREATE POLICY "Admins can update all book suggestions"
  ON book_suggestion FOR UPDATE
  USING (is_admin());

CREATE POLICY "Students can delete own book suggestions"
  ON book_suggestion FOR DELETE
  USING (student_id = get_current_user_id() AND status = 'pending');

CREATE POLICY "Admins can delete all book suggestions"
  ON book_suggestion FOR DELETE
  USING (is_admin());


-- ============================================================================
-- BOOK_EDIT_SUGGESTION TABLE POLICIES
-- ============================================================================

CREATE POLICY "Students can view own edit suggestions"
  ON book_edit_suggestion FOR SELECT
  USING (student_id = get_current_user_id());

CREATE POLICY "Admins can view all edit suggestions"
  ON book_edit_suggestion FOR SELECT
  USING (is_admin());

CREATE POLICY "Students can create edit suggestions"
  ON book_edit_suggestion FOR INSERT
  WITH CHECK (student_id = get_current_user_id());

CREATE POLICY "Students can update own edit suggestions"
  ON book_edit_suggestion FOR UPDATE
  USING (student_id = get_current_user_id() AND status = 'pending')
  WITH CHECK (student_id = get_current_user_id() AND status = 'pending');

CREATE POLICY "Admins can update all edit suggestions"
  ON book_edit_suggestion FOR UPDATE
  USING (is_admin());

CREATE POLICY "Students can delete own edit suggestions"
  ON book_edit_suggestion FOR DELETE
  USING (student_id = get_current_user_id() AND status = 'pending');

CREATE POLICY "Admins can delete all edit suggestions"
  ON book_edit_suggestion FOR DELETE
  USING (is_admin());


-- ============================================================================
-- GENRE TABLE POLICIES
-- ============================================================================

CREATE POLICY "Authenticated users can view genres"
  ON genre FOR SELECT
  USING (get_current_user_id() > 0);

CREATE POLICY "Admins can insert genres"
  ON genre FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update genres"
  ON genre FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete genres"
  ON genre FOR DELETE
  USING (is_admin());


-- ============================================================================
-- SUB_GENRE TABLE POLICIES
-- ============================================================================

CREATE POLICY "Authenticated users can view sub_genres"
  ON sub_genre FOR SELECT
  USING (get_current_user_id() > 0);

CREATE POLICY "Admins can insert sub_genres"
  ON sub_genre FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update sub_genres"
  ON sub_genre FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete sub_genres"
  ON sub_genre FOR DELETE
  USING (is_admin());


-- ============================================================================
-- TOPIC TABLE POLICIES
-- ============================================================================

CREATE POLICY "Authenticated users can view topics"
  ON topic FOR SELECT
  USING (get_current_user_id() > 0);

CREATE POLICY "Admins can insert topics"
  ON topic FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update topics"
  ON topic FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete topics"
  ON topic FOR DELETE
  USING (is_admin());


-- ============================================================================
-- GENRE_MAP TABLE POLICIES
-- ============================================================================

CREATE POLICY "Authenticated users can view genre_maps"
  ON genre_map FOR SELECT
  USING (get_current_user_id() > 0);

CREATE POLICY "Admins can insert genre_maps"
  ON genre_map FOR INSERT
  WITH CHECK (is_admin());

CREATE POLICY "Admins can update genre_maps"
  ON genre_map FOR UPDATE
  USING (is_admin());

CREATE POLICY "Admins can delete genre_maps"
  ON genre_map FOR DELETE
  USING (is_admin());


-- ============================================================================
-- GRANT USAGE ON SEQUENCES TO ALL USERS
-- ============================================================================

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO PUBLIC;


-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================
-- 
-- In your Flask app, add this before each request:
--
-- @app.before_request
-- def set_rls_context():
--     if current_user.is_authenticated:
--         db.session.execute(
--             db.text("SET LOCAL app.current_user_id = :user_id"),
--             {"user_id": current_user.id}
--         )
--         db.session.execute(
--             db.text("SET LOCAL app.current_user_role = :role"),
--             {"role": current_user.role}
--         )
--
-- @app.teardown_request  
-- def clear_rls_context(exception=None):
--     try:
--         db.session.execute(db.text("RESET app.current_user_id"))
--         db.session.execute(db.text("RESET app.current_user_role"))
--     except:
--         pass
--
-- ============================================================================

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
-- SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'public';
-- ============================================================================
