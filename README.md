# 📚 Book Tracker for Students

My little test of vibe-coding..

A comprehensive web application designed for students to track their reading progress, with features for both students and administrators (teachers). Built with Flask and Python.


## Features

### For Students 👨‍🎓
- **Reading List Management**: Create and maintain an ordered list of books to read next
- **Mark Books as Read**: Track completed books with timestamps
- **Guided Reviews**: Write structured reviews with ratings (1-5 stars) answering prompts like:
  - What did you like about this book?
  - What was your favorite part?
  - What did you learn?
  - Who would you recommend this to?
- **View Reading History**: See all books read and reviews written
- **Book Suggestions**: Receive personalized book recommendations from teachers

### For Administrators (Teachers) 👨‍🏫
- **Class Management**: Create and manage multiple classes with students
- **Student Progress Tracking**: View individual student reading statistics, including:
  - Books read count
  - Reviews written
  - Reading by genre breakdown
- **Assign Reading Lists**: Assign specific books to classes
- **Suggest Books**: Recommend specific books to individual students with personalized reasons
- **Book Library Management**: 
  - Add books manually
  - Upload books via CSV file
  - Search OpenLibrary.org for book metadata
- **Genre & Topic Categorization**: Guide students toward diverse reading

### General Features
- **OpenLibrary Integration**: Automatic book metadata fetching (cover images, descriptions, authors)
- **Lexile Rating Support**: Track reading levels to suggest appropriate books
- **User Authentication**: Secure login system with role-based access (student/admin)
- **Responsive Design**: Works on desktop and mobile devices

## Installation

### Prerequisites
- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

### Setup Steps

1. **Clone or download this repository**
   ```powershell
   cd c:\Users\steve\Documents\personal\bookapp
   ```

2. **Install uv (if not already installed)**
   ```powershell
   pip install uv
   ```
   
   Or using the standalone installer:
   ```powershell
   irm https://astral.sh/uv/install.ps1 | iex
   ```

3. **Sync dependencies (creates virtual environment automatically)**
   ```powershell
   uv sync
   ```

5. **Create environment configuration**
   ```powershell
   Copy-Item .env.example .env
   ```
   
   Edit `.env` and set a secure secret key:
   ```
   SECRET_KEY=your-very-secret-random-key-here
   DATABASE_URI=sqlite:///bookapp.db
   FLASK_ENV=development
   ```

6. **Initialize the database**
   ```powershell
   uv run python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database created!')"
   ```

7. **Create an admin user**
   ```powershell
   uv run python create_admin.py
   ```
   Follow the prompts to create your first administrator account.

## Running the Application

1. **Start the Flask development server**
   ```powershell
   uv run python app.py
   ```
   
   Or use the shorthand:
   ```powershell
   uv run flask run
   ```

2. **Open your browser and navigate to**
   ```
   http://localhost:5000
   ```

3. **Log in with your admin credentials** or register a new student account

## Usage Guide

### For Administrators

1. **Creating a Class**
   - Navigate to "Classes" → "Create New Class"
   - Enter class name and optional description
   - Click "Create Class"

2. **Adding Students to a Class**
   - Click on a class name
   - Use the dropdown to select and add students
   - Students must be registered first

3. **Adding Books**
   - **Manual Entry**: Books → Add Book Manually
   - **CSV Upload**: Books → Upload CSV
   - **Search OpenLibrary**: Use the search form to find books from OpenLibrary.org

4. **Viewing Student Progress**
   - Click on a student's name from any class
   - View their reading statistics, books read, and reviews
   - See genre distribution to guide reading diversity

5. **Suggesting Books to Students**
   - From a student's profile, click "Suggest a Book"
   - Select a book and provide a reason for the suggestion
   - The student will see this on their dashboard

### For Students

1. **Building Your Reading List**
   - Go to "Reading List"
   - Browse available books
   - Click "Add to List" for books you want to read

2. **Marking Books as Read**
   - From your reading list or dashboard
   - Click "Mark as Read" on any book
   - You'll be prompted to write a review

3. **Writing Reviews**
   - Rate the book (1-5 stars)
   - Answer guided questions about the book
   - Submit your review

4. **Viewing Your Progress**
   - Dashboard shows your reading statistics
   - "Books Read" page displays all completed books and reviews

5. **Accepting Book Suggestions**
   - Teachers' suggestions appear on your dashboard
   - Click "Add to Reading List" to accept a suggestion

## CSV Upload Format

To bulk upload books, create a CSV file with the following columns:

```csv
title,author,isbn,book_type,genre,sub_genre,topic,lexile_rating,grade,owned
The Hunger Games,Suzanne Collins,9780439023481,Fiction,Science Fiction,Dystopian,Courage,810L,7,Physical
Wonder,R.J. Palacio,9780375869020,Fiction,Realistic Fiction,School Life,Kindness,790L,5,Kindle
I Am Malala,Malala Yousafzai,9780316322423,Non-Fiction,Biography,Memoir,Activism,1000L,8,Not Owned
```

**Columns:**
- `title` (required): Book title
- `author`: Author name
- `isbn`: ISBN-13 or ISBN-10 (will fetch data from OpenLibrary)
- `book_type`: Fiction or Non-Fiction
- `genre`: Book genre/category
- `sub_genre`: A more specific category (e.g., Dystopian, Memoir)
- `topic`: Specific topic or theme
- `lexile_rating`: Reading level (e.g., 750L)
- `grade`: Intended grade level (1-12)
- `owned`: Ownership status (Physical, Kindle, or Not Owned)

Download a sample CSV from the admin interface: Books → Download Sample CSV

## Project Structure

```
bookapp/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── models.py                   # Database models
├── forms.py                    # WTForms form definitions
├── openlibrary_service.py      # OpenLibrary API integration
├── book_import_service.py      # CSV import functionality
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── templates/                 # HTML templates
│   ├── base.html             # Base template
│   ├── index.html            # Landing page
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── admin/                # Admin templates
│   │   ├── dashboard.html
│   │   ├── classes.html
│   │   ├── view_class.html
│   │   ├── view_student.html
│   │   ├── books.html
│   │   ├── create_book.html
│   │   ├── upload_books.html
│   │   └── suggest_book.html
│   └── student/              # Student templates
│       ├── dashboard.html
│       ├── reading_list.html
│       ├── books_read.html
│       └── create_review.html
└── static/                   # Static files
    ├── css/
    │   └── style.css        # Main stylesheet
    └── js/
        └── script.js        # JavaScript functionality
```

## Database Schema

The application uses SQLite with the following main models:

- **User**: Students and administrators with authentication
- **Class**: Classes created by teachers
- **Book**: Book library with metadata
- **ReadingListItem**: Student reading lists (ordered)
- **BookRead**: Books marked as read by students
- **Review**: Student book reviews with ratings and guided questions
- **SuggestedBook**: Teacher suggestions to students

## Technologies Used

- **Backend**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF and WTForms
- **API Integration**: OpenLibrary.org for book metadata
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Custom CSS with responsive design

## OpenLibrary Integration

The app integrates with OpenLibrary.org to:
- Search for books by title, author, or ISBN
- Automatically fetch book metadata:
  - Cover images
  - Author information
  - Publication details
  - Descriptions
  - Subject/genre information

## Security Features

- Password hashing with Werkzeug
- Session-based authentication with Flask-Login
- Role-based access control (admin/student)
- CSRF protection with Flask-WTF
- Secure file upload handling

## Customization

### Changing the Theme
Edit `static/css/style.css` and modify the CSS variables in the `:root` section:

```css
:root {
    --primary-color: #4a90e2;
    --secondary-color: #7b68ee;
    --success-color: #2ecc71;
    /* ... */
}
```

### Adding More Review Questions
Edit `models.py` to add fields to the `Review` model, and update `forms.py` and the review template.

### Modifying Lexile Ratings
The lexile_rating field accepts any string value. You can validate or constrain it by modifying the form validators in `forms.py`.

## Troubleshooting

### Import Errors
If you see "Import could not be resolved" errors in your editor, make sure:
1. Dependencies are synced: `uv sync`
2. Your Python interpreter is set to the uv-managed virtual environment (`.venv`)
3. Restart your editor after syncing dependencies

### Database Issues
To reset the database:
```powershell
Remove-Item bookapp.db
uv run python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database recreated!')"
```

### Database Upgrades (adding new columns)
If you pull new changes that add fields (like `book_type` or `sub_genre`) and you're using an existing SQLite DB, run the lightweight upgrade:

```powershell
uv run flask --app app upgrade-db
```

This command is idempotent and safe to run multiple times; it only adds missing columns.

### Port Already in Use
If port 5000 is already in use, modify `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Change port
```

## Future Enhancements

Potential features to add:
- Reading goals and achievements/badges
- Book clubs within classes
- Reading statistics and charts
- Export reading history as PDF
- Book recommendations based on reading history
- Parent portal to view student progress
- Mobile app version
- Social features (share reviews, reading challenges)

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

This project is open source and available for educational purposes.

## Support

For issues or questions, please review the code comments and documentation within each file.

## Acknowledgments

- **OpenLibrary.org** for providing free book metadata API
- **Flask** community for excellent documentation
- All the open-source libraries that made this project possible

---

**Happy Reading! 📚**
