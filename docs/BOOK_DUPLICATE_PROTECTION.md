# Book Duplicate Prevention and Review Protection

## Changes Made

### 1. Unique Constraint on Author + Title

**Problem:** Books could be added multiple times with the same author and title, and if a book was deleted, the ID could be reused, causing student reviews to incorrectly appear on new books.

**Solution:** Added a unique constraint on the combination of `author` and `title` in the Book model.

#### Model Changes (models.py)
- Added `__table_args__` to Book model with `UniqueConstraint('author', 'title', name='uq_author_title')`
- This ensures no two books can have the same author and title combination

#### Application-Level Validation (app.py)
Since database constraints can throw errors, we added validation in all book creation/editing routes:

1. **create_book()**: Checks for existing book with same author+title before creating
2. **edit_book()**: Checks that no other book has the same author+title (excluding the current book)
3. **add_book_from_openlibrary()**: Checks by both openlibrary_id and author+title
4. **CSV Import (book_import_service.py)**: Already had fuzzy matching; added constraint violation handling

All routes now:
- Check for duplicates before attempting database operations
- Wrap database operations in try-except blocks
- Show user-friendly error messages
- Rollback on errors

### 2. Prevent Deletion of Books with Reviews

**Problem:** Deleting a book with student reviews would orphan those reviews or cause data integrity issues.

**Solution:** Added review checking before allowing deletion.

#### Model Changes (models.py)
- Added `has_reviews()` method to Book model
- Returns True if the book has any student reviews

#### Application Changes (app.py)

**Individual Book Deletion:**
- `delete_book()` now checks `book.has_reviews()` before deleting
- Shows error message: "Cannot delete [title] - this book has student reviews."
- Book is not deleted if it has reviews

**Bulk Deletion:**
- `bulk_book_action()` checks all selected books for reviews
- If any have reviews, shows error listing affected books
- No books are deleted if any have reviews (all-or-nothing approach)
- Error message shows up to 3 book titles with review count

## Migration

### For New Databases
The unique constraint will be automatically created when you run `db.create_all()`.

### For Existing Databases
Run the migration script:

```bash
python migrations/migrate_add_unique_constraint.py
```

This script will:
1. Find and display any duplicate books (same author + title)
2. Keep the oldest version of each duplicate
3. Delete newer duplicates and their related records (reading list items, books read, suggestions)
4. Add the unique constraint to the database (PostgreSQL only)
5. For SQLite, the constraint is enforced at the application level

**Important:** Backup your database before running the migration!

## User-Facing Changes

### Administrators will see:
1. **When creating/editing books:** Clear error messages if trying to create a duplicate
2. **When deleting books:** Cannot delete books that have student reviews
3. **When bulk deleting:** All books must be deletable (no reviews) or none are deleted
4. **CSV Import:** Duplicate books are skipped with clear error messages

### Students:
- No visible changes
- Their reviews are now protected from accidental deletion
- No risk of their review appearing on the wrong book

## Technical Details

### Database Constraint
```python
__table_args__ = (
    db.UniqueConstraint('author', 'title', name='uq_author_title'),
)
```

### Review Check Method
```python
def has_reviews(self):
    """Check if this book has any student reviews"""
    return len(self.reviews) > 0
```

### Example Error Handling
```python
try:
    db.session.add(book)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    flash(f'Error adding book: {str(e)}', 'danger')
```

## Testing Recommendations

1. **Test duplicate prevention:**
   - Try to add the same book twice
   - Try to edit a book to match another book's title/author
   - Import CSV with duplicate entries

2. **Test deletion protection:**
   - Create a book, have a student review it, try to delete it
   - Try bulk deletion with mix of reviewed and non-reviewed books
   - Delete a book without reviews (should work)

3. **Test migration:**
   - Create duplicate books in test database
   - Run migration script
   - Verify only one copy remains
   - Verify constraint prevents new duplicates
