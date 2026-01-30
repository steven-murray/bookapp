import click
from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
import os
from bookapp.config import Config
from bookapp.models import db, User, Class, Book, Review, BookRead, ReadingListItem, SuggestedBook, BookSuggestion, BookEditSuggestion, Genre, SubGenre, Topic, GenreMap
from bookapp.forms import (LoginForm, RegistrationForm, ClassForm, BookForm, CSVUploadForm, 
                   ReviewForm, SuggestBookForm, SearchBookForm, StudentBookFilterForm, BookSuggestionForm)
from bookapp.openlibrary_service import OpenLibraryService
from bookapp.book_import_service import BookImportService, enrich_book_from_openlibrary
from datetime import datetime
import io
from sqlalchemy import or_
from bookapp.rls_middleware import setup_rls_middleware

# Get project root directory (2 levels up from this file)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

app = Flask(__name__,
            template_folder=os.path.join(project_root, 'templates'),
            static_folder=os.path.join(project_root, 'static'))
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

setup_rls_middleware(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom Jinja filter to remove page parameter from request args
@app.template_filter('reject_page')
def reject_page_filter(args_dict):
    """Remove 'page' from query args dict"""
    return {k: v for k, v in args_dict.items() if k != 'page'}

# Decorator for admin-only routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Admin Routes
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    total_students = User.query.filter_by(role='student').count()
    total_books = Book.query.count()
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(5).all()
    
    # Find books in reading lists that are not owned
    # Get all unique book IDs from reading lists
    reading_list_book_ids = db.session.query(ReadingListItem.book_id).distinct().all()
    reading_list_book_ids = [book_id[0] for book_id in reading_list_book_ids]
    
    # Query books that are in reading lists and not owned
    books_needed = Book.query.filter(
        Book.id.in_(reading_list_book_ids),
        Book.owned == 'Not Owned'
    ).all()
    
    # Count how many students have each book in their reading list
    books_needed_with_counts = []
    for book in books_needed:
        student_count = ReadingListItem.query.filter_by(book_id=book.id).count()
        books_needed_with_counts.append({
            'book': book,
            'student_count': student_count
        })
    
    # Sort by student count (descending)
    books_needed_with_counts.sort(key=lambda x: x['student_count'], reverse=True)
    
    # Count pending book suggestions from students
    pending_suggestions = BookSuggestion.query.filter_by(status='pending').count()
    
    return render_template('admin/dashboard.html', 
                         classes=classes,
                         total_students=total_students,
                         total_books=total_books,
                         recent_reviews=recent_reviews,
                         books_needed=books_needed_with_counts,
                         pending_suggestions=pending_suggestions)

@app.route('/admin/classes')
@login_required
@admin_required
def admin_classes():
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    return render_template('admin/classes.html', classes=classes)

@app.route('/admin/class/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_class():
    form = ClassForm()
    if form.validate_on_submit():
        new_class = Class(
            name=form.name.data,
            description=form.description.data,
            teacher_id=current_user.id
        )
        db.session.add(new_class)
        db.session.commit()
        flash(f'Class "{new_class.name}" created successfully!', 'success')
        return redirect(url_for('admin_classes'))
    
    return render_template('admin/create_class.html', form=form)

@app.route('/admin/class/<int:class_id>')
@login_required
@admin_required
def view_class(class_id):
    cls = Class.query.get_or_404(class_id)
    if cls.teacher_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('admin_classes'))
    
    all_students = User.query.filter_by(role='student').all()
    return render_template('admin/view_class.html', cls=cls, all_students=all_students)

@app.route('/admin/class/<int:class_id>/add_student/<int:student_id>')
@login_required
@admin_required
def add_student_to_class(class_id, student_id):
    cls = Class.query.get_or_404(class_id)
    student = User.query.get_or_404(student_id)
    
    if cls.teacher_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('admin_classes'))
    
    if student not in cls.students:
        cls.students.append(student)
        db.session.commit()
        flash(f'{student.first_name} {student.last_name} added to class.', 'success')
    else:
        flash('Student already in this class.', 'info')
    
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/admin/class/<int:class_id>/remove_student/<int:student_id>')
@login_required
@admin_required
def remove_student_from_class(class_id, student_id):
    cls = Class.query.get_or_404(class_id)
    student = User.query.get_or_404(student_id)
    
    if cls.teacher_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('admin_classes'))
    
    if student in cls.students:
        cls.students.remove(student)
        db.session.commit()
        flash(f'{student.first_name} {student.last_name} removed from class.', 'success')
    
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/admin/student/<int:student_id>')
@login_required
@admin_required
def view_student(student_id):
    student = User.query.get_or_404(student_id)
    if student.role != 'student':
        flash('Invalid student.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    books_read = BookRead.query.filter_by(user_id=student_id).all()
    reviews = Review.query.filter_by(user_id=student_id).all()
    reading_list = ReadingListItem.query.filter_by(user_id=student_id).order_by(ReadingListItem.order).all()
    
    # Calculate chart data
    type_counts = {'Fiction': 0, 'Non-Fiction': 0}
    genre_counts = {}
    grade_counts = {}
    
    for br in books_read:
        # Type breakdown
        if br.book.book_type in ['Fiction', 'Non-Fiction']:
            type_counts[br.book.book_type] += 1
        
        # Genre breakdown
        if br.book.genre:
            genre_counts[br.book.genre] = genre_counts.get(br.book.genre, 0) + 1
        
        # Grade breakdown
        if br.book.grade is not None:
            grade_counts[br.book.grade] = grade_counts.get(br.book.grade, 0) + 1
    
    return render_template('admin/view_student.html', 
                         student=student,
                         books_read=books_read,
                         reviews=reviews,
                         reading_list=reading_list,
                         type_counts=type_counts,
                         genre_counts=genre_counts,
                         grade_counts=grade_counts)

@app.route('/admin/books')
@login_required
@admin_required
def admin_books():
    search_form = SearchBookForm()
    
    # Build filter form with dynamic choices
    filter_form = StudentBookFilterForm(request.args)
    # Populate genre/sub-genre choices dynamically from DB
    genres = [g[0] for g in db.session.query(Book.genre).distinct() if g[0]]
    sub_genres = [sg[0] for sg in db.session.query(Book.sub_genre).distinct() if sg[0]]
    filter_form.genre.choices = [('', 'Any'), ('__not_set__', 'Not Set')] + [(g, g) for g in sorted(genres)]
    filter_form.sub_genre.choices = [('', 'Any'), ('__not_set__', 'Not Set')] + [(sg, sg) for sg in sorted(sub_genres)]

    # Apply filters
    query = Book.query
    if filter_form.book_type.data:
        if filter_form.book_type.data == '__not_set__':
            query = query.filter(or_(Book.book_type == None, Book.book_type == ''))
        else:
            query = query.filter(Book.book_type == filter_form.book_type.data)
    if filter_form.genre.data:
        if filter_form.genre.data == '__not_set__':
            query = query.filter(or_(Book.genre == None, Book.genre == ''))
        else:
            query = query.filter(Book.genre == filter_form.genre.data)
    if filter_form.sub_genre.data:
        if filter_form.sub_genre.data == '__not_set__':
            query = query.filter(or_(Book.sub_genre == None, Book.sub_genre == ''))
        else:
            query = query.filter(Book.sub_genre == filter_form.sub_genre.data)
    if filter_form.min_grade.data is not None:
        query = query.filter(Book.grade >= filter_form.min_grade.data)
    if filter_form.max_grade.data is not None:
        query = query.filter(Book.grade <= filter_form.max_grade.data)
    if filter_form.owned.data:
        query = query.filter(Book.owned == filter_form.owned.data)
    if filter_form.search.data:
        term = f"%{filter_form.search.data.strip()}%"
        query = query.filter(or_(Book.title.ilike(term), Book.author.ilike(term)))
    if filter_form.missing_olid.data:
        query = query.filter(or_(Book.openlibrary_id == None, Book.openlibrary_id == ''))

    books = query.all()
    return render_template('admin/books.html', books=books, search_form=search_form, filter_form=filter_form)

@app.route('/admin/book/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_book():
    form = BookForm()
    if form.validate_on_submit():
        # Check if book with same author and title already exists
        existing_book = Book.query.filter_by(
            author=form.author.data,
            title=form.title.data
        ).first()
        
        if existing_book:
            flash(f'A book titled "{form.title.data}" by {form.author.data} already exists in the library.', 'danger')
            return render_template('admin/create_book.html', form=form)
        
        book = Book(
            title=form.title.data,
            author=form.author.data,
            openlibrary_id=form.openlibrary_id.data or None,
            publication_year=form.publication_year.data if form.publication_year.data is not None else None,
            book_type=form.book_type.data or None,
            sub_genre=form.sub_genre.data or None,
            genre=form.genre.data,
            topic=form.topic.data,
            lexile_rating=form.lexile_rating.data,
            grade=form.grade.data if form.grade.data is not None else None,
            owned=form.owned.data or 'Not Owned',
            description=form.description.data
        )
        
        try:
            db.session.add(book)
            db.session.commit()
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin_books'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding book: {str(e)}', 'danger')
            return render_template('admin/create_book.html', form=form)
    
    return render_template('admin/create_book.html', form=form)

@app.route('/admin/book/enrich', methods=['POST'])
@login_required
@admin_required
def enrich_book_from_title_author():
    """Return best-guess fields from OpenLibrary based on provided title and author."""
    print("ENRICHING BOOK")
    data = request.get_json(silent=True) or request.form
    title = (data.get('title') or '').strip()
    author = (data.get('author') or '').strip()
    if not title or not author:
        return jsonify({'ok': False, 'error': 'Title and author are required'}), 400

    # Create a temporary Book-like instance and enrich it
    temp = Book(title=title, author=author)
    print("MADE BOOK")
    try:
        enrich_book_from_openlibrary(temp)
        print("HERE IS WHAT I GOT", temp)
        return jsonify({
            'ok': True,
            'title': temp.title,
            'author': temp.author,
            'book_type': temp.book_type,
            'genre': temp.genre,
            'sub_genre': temp.sub_genre,
            'publication_year': temp.publication_year,
            'openlibrary_id': temp.openlibrary_id,
            'cover_url': getattr(temp, 'cover_url', None)
        })
    except Exception as e:
        print(e)
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/admin/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm()

    if form.validate_on_submit():
        # Check if another book with same author and title exists (excluding current book)
        duplicate = Book.query.filter(
            Book.author == form.author.data,
            Book.title == form.title.data,
            Book.id != book.id
        ).first()
        
        if duplicate:
            flash(f'Another book titled "{form.title.data}" by {form.author.data} already exists.', 'danger')
            return render_template('admin/edit_book.html', form=form, book=book)
        
        # Update fields
        book.title = form.title.data
        book.author = form.author.data or None
        book.openlibrary_id = form.openlibrary_id.data or None
        book.publication_year = form.publication_year.data if form.publication_year.data is not None else None
        book.book_type = form.book_type.data or None
        book.sub_genre = form.sub_genre.data or None
        book.genre = form.genre.data or None
        book.topic = form.topic.data or None
        book.lexile_rating = form.lexile_rating.data or None
        book.grade = form.grade.data if form.grade.data is not None else None
        book.owned = form.owned.data or 'Not Owned'
        book.description = form.description.data or None

        try:
            db.session.commit()
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin_books'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating book: {str(e)}', 'danger')
            return render_template('admin/edit_book.html', form=form, book=book)

    # Pre-fill form with current values
    if request.method == 'GET':
        form.title.data = book.title
        form.author.data = book.author
        form.openlibrary_id.data = book.openlibrary_id
        form.publication_year.data = book.publication_year
        form.book_type.data = book.book_type
        form.sub_genre.data = book.sub_genre
        form.genre.data = book.genre
        form.topic.data = book.topic
        form.lexile_rating.data = book.lexile_rating
        form.grade.data = book.grade
        form.owned.data = book.owned or 'Not Owned'
        form.description.data = book.description

    return render_template('admin/edit_book.html', form=form, book=book)

@app.route('/admin/books/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_books():
    form = CSVUploadForm()
    if form.validate_on_submit():
        result = BookImportService.import_from_csv(
            form.csv_file.data, 
            skip_enrichment=form.skip_enrichment.data
        )
        
        if result['success_count'] > 0:
            flash(f"Successfully imported {result['success_count']} books!", 'success')
        if result['error_count'] > 0:
            flash(f"{result['error_count']} errors occurred during import.", 'warning')
            for error in result['errors'][:5]:  # Show first 5 errors
                flash(error, 'danger')
        
        return redirect(url_for('admin_books'))
    
    return render_template('admin/upload_books.html', form=form)

@app.route('/admin/books/sample_csv')
@login_required
@admin_required
def download_sample_csv():
    csv_content = BookImportService.create_sample_csv()
    return send_file(
        io.BytesIO(csv_content.encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='sample_books.csv'
    )

@app.route('/admin/search_openlibrary', methods=['POST'])
@login_required
@admin_required
def search_openlibrary():
    form = SearchBookForm()
    if form.validate_on_submit():
        results = OpenLibraryService.search_books(form.query.data)
        return render_template('admin/search_results.html', results=results, query=form.query.data, form=form)
    
    return redirect(url_for('admin_books'))

@app.route('/admin/add_book_from_openlibrary', methods=['POST'])
@login_required
@admin_required
def add_book_from_openlibrary():
    title = request.form.get('title')
    author = request.form.get('author')
    openlibrary_id = request.form.get('openlibrary_id')
    cover_id = request.form.get('cover_id')
    publication_year = request.form.get('publication_year')
    
    # Check if book already exists by openlibrary_id or author+title
    if openlibrary_id:
        existing_book = Book.query.filter_by(openlibrary_id=openlibrary_id).first()
        if existing_book:
            flash(f'Book "{title}" already exists in the library.', 'info')
            return redirect(url_for('admin_books'))
    
    # Also check by author and title
    existing_book = Book.query.filter_by(author=author, title=title).first()
    if existing_book:
        flash(f'Book "{title}" by {author} already exists in the library.', 'info')
        return redirect(url_for('admin_books'))
    
    # Create new book
    book = Book(
        title=title,
        author=author,
        openlibrary_id=openlibrary_id if openlibrary_id else None,
        publication_year=int(publication_year) if publication_year and publication_year != 'None' else None
    )
    
    # Set cover URL if available
    if cover_id and cover_id != 'None':
        book.cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    
    try:
        db.session.add(book)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding book: {str(e)}', 'danger')
        return redirect(url_for('admin_books'))
    
    flash(f'Book "{title}" added to library successfully!', 'success')
    return redirect(url_for('admin_books'))

@app.route('/admin/book/<int:book_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if book has reviews
    if book.has_reviews():
        flash(f'Cannot delete "{book.title}" - this book has student reviews.', 'danger')
        return redirect(url_for('admin_books'))
    
    # Remove suggestions referencing this book to avoid FK issues
    SuggestedBook.query.filter_by(book_id=book_id).delete(synchronize_session=False)
    
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('admin_books'))

@app.route('/admin/books/bulk-action', methods=['POST'])
@login_required
@admin_required
def bulk_book_action():
    action = request.form.get('action')
    book_ids = request.form.getlist('book_ids')
    
    # Collect filter parameters to preserve them
    filter_params = {}
    if request.form.get('search'):
        filter_params['search'] = request.form.get('search')
    if request.form.get('book_type'):
        filter_params['book_type'] = request.form.get('book_type')
    if request.form.get('genre'):
        filter_params['genre'] = request.form.get('genre')
    if request.form.get('sub_genre'):
        filter_params['sub_genre'] = request.form.get('sub_genre')
    if request.form.get('min_grade'):
        filter_params['min_grade'] = request.form.get('min_grade')
    if request.form.get('max_grade'):
        filter_params['max_grade'] = request.form.get('max_grade')
    if request.form.get('owned'):
        filter_params['owned'] = request.form.get('owned')
    if request.form.get('missing_olid'):
        filter_params['missing_olid'] = '1'
    
    if not book_ids:
        flash('No books selected.', 'warning')
        return redirect(url_for('admin_books', **filter_params))
    
    book_ids = [int(bid) for bid in book_ids]
    
    if action == 'delete':
        # Check if any selected books have reviews
        books_with_reviews = Book.query.filter(
            Book.id.in_(book_ids),
            Book.reviews.any()
        ).all()
        
        if books_with_reviews:
            titles = [b.title for b in books_with_reviews[:3]]
            msg = f"Cannot delete {len(books_with_reviews)} book(s) with student reviews: {', '.join(titles)}"
            if len(books_with_reviews) > 3:
                msg += f" and {len(books_with_reviews) - 3} more"
            flash(msg, 'danger')
            return redirect(url_for('admin_books', **filter_params))
        
        # Remove suggestions first
        SuggestedBook.query.filter(SuggestedBook.book_id.in_(book_ids)).delete(synchronize_session=False)
        # Delete books
        Book.query.filter(Book.id.in_(book_ids)).delete(synchronize_session=False)
        db.session.commit()
        flash(f'{len(book_ids)} book(s) deleted successfully!', 'success')
    
    elif action == 'set_type':
        book_type = request.form.get('book_type')
        if book_type:
            Book.query.filter(Book.id.in_(book_ids)).update({'book_type': book_type}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(book_ids)} book(s) updated to type "{book_type}".', 'success')
    
    elif action == 'set_owned':
        owned = request.form.get('owned')
        if owned:
            Book.query.filter(Book.id.in_(book_ids)).update({'owned': owned}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(book_ids)} book(s) updated to owned status "{owned}".', 'success')
    
    elif action == 'set_genre':
        genre = request.form.get('genre')
        if genre:
            Book.query.filter(Book.id.in_(book_ids)).update({'genre': genre}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(book_ids)} book(s) updated to genre "{genre}".', 'success')
    
    else:
        flash('Invalid action.', 'danger')
    
    return redirect(url_for('admin_books', **filter_params))

@app.route('/admin/suggest_book/<int:student_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggest_book(student_id):
    student = User.query.get_or_404(student_id)
    form = SuggestBookForm()
    
    # Get all books for selection
    books = Book.query.all()
    
    if form.validate_on_submit():
        suggestion = SuggestedBook(
            student_id=student_id,
            book_id=form.book_id.data,
            suggested_by_id=current_user.id,
            reason=form.reason.data
        )
        db.session.add(suggestion)
        db.session.commit()
        flash(f'Book suggested to {student.first_name}!', 'success')
        return redirect(url_for('view_student', student_id=student_id))
    
    return render_template('admin/suggest_book.html', student=student, books=books, form=form)

# Student Routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    reading_list = ReadingListItem.query.filter_by(user_id=current_user.id).order_by(ReadingListItem.order).all()
    books_read = BookRead.query.filter_by(user_id=current_user.id).order_by(BookRead.completed_at.desc()).all()
    recent_reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).limit(3).all()
    suggestions = SuggestedBook.query.filter_by(student_id=current_user.id, is_accepted=False).all()
    
    # Calculate chart data
    type_counts = {'Fiction': 0, 'Non-Fiction': 0}
    genre_counts = {}
    grade_counts = {}
    
    for br in books_read:
        # Type breakdown
        if br.book.book_type in ['Fiction', 'Non-Fiction']:
            type_counts[br.book.book_type] += 1
        
        # Genre breakdown
        if br.book.genre:
            genre_counts[br.book.genre] = genre_counts.get(br.book.genre, 0) + 1
        
        # Grade breakdown
        if br.book.grade is not None:
            grade_counts[br.book.grade] = grade_counts.get(br.book.grade, 0) + 1
    
    return render_template('student/dashboard.html',
                         reading_list=reading_list,
                         books_read=books_read,
                         recent_reviews=recent_reviews,
                         suggestions=suggestions,
                         type_counts=type_counts,
                         genre_counts=genre_counts,
                         grade_counts=grade_counts)

@app.route('/student/reading_list')
@login_required
def student_reading_list():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    

    reading_list = ReadingListItem.query.filter_by(user_id=current_user.id).order_by(ReadingListItem.order).all()
    books_read = BookRead.query.filter_by(user_id=current_user.id).all()
    read_book_ids = {br.book_id for br in books_read}

    # Build filter form with dynamic choices
    filter_form = StudentBookFilterForm(request.args)
    # Populate genre/sub-genre choices dynamically from DB
    genres = [g[0] for g in db.session.query(Book.genre).distinct() if g[0]]
    sub_genres = [sg[0] for sg in db.session.query(Book.sub_genre).distinct() if sg[0]]
    filter_form.genre.choices = [('', 'Any')] + [(g, g) for g in sorted(genres)]
    filter_form.sub_genre.choices = [('', 'Any')] + [(sg, sg) for sg in sorted(sub_genres)]

    # Get page number from query params
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Apply filters to browseable books
    query = Book.query
    if filter_form.book_type.data:
        query = query.filter(Book.book_type == filter_form.book_type.data)
    if filter_form.genre.data:
        query = query.filter(Book.genre == filter_form.genre.data)
    if filter_form.sub_genre.data:
        query = query.filter(Book.sub_genre == filter_form.sub_genre.data)
    if filter_form.min_grade.data is not None:
        query = query.filter(Book.grade >= filter_form.min_grade.data)
    if filter_form.max_grade.data is not None:
        query = query.filter(Book.grade <= filter_form.max_grade.data)
    if filter_form.owned.data:
        query = query.filter(Book.owned == filter_form.owned.data)
    if filter_form.search.data:
        term = f"%{filter_form.search.data.strip()}%"
        query = query.filter(or_(Book.title.ilike(term), Book.author.ilike(term)))

    # Filter out books already read
    all_books_filtered = [b for b in query.all() if b.id not in read_book_ids]
    
    # Calculate pagination
    total_books = len(all_books_filtered)
    total_pages = (total_books + per_page - 1) // per_page  # Ceiling division
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    all_books = all_books_filtered[start_idx:end_idx]

    return render_template('student/reading_list.html', 
                          reading_list=reading_list, 
                          all_books=all_books, 
                          filter_form=filter_form,
                          page=page,
                          total_pages=total_pages,
                          total_books=total_books)

@app.route('/student/add_to_reading_list/<int:book_id>')
@login_required
def add_to_reading_list(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if already in reading list
    existing = ReadingListItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if existing:
        flash('Book already in your reading list.', 'info')
    else:
        # Get next order number
        max_order = db.session.query(db.func.max(ReadingListItem.order)).filter_by(user_id=current_user.id).scalar() or 0
        
        item = ReadingListItem(
            user_id=current_user.id,
            book_id=book_id,
            order=max_order + 1
        )
        db.session.add(item)
        db.session.commit()
        flash(f'"{book.title}" added to your reading list!', 'success')
    
    return redirect(request.referrer or url_for('student_reading_list'))

@app.route('/student/remove_from_reading_list/<int:item_id>')
@login_required
def remove_from_reading_list(item_id):
    item = ReadingListItem.query.get_or_404(item_id)
    
    if item.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    db.session.delete(item)
    db.session.commit()
    flash('Book removed from reading list.', 'success')
    
    return redirect(url_for('student_reading_list'))

@app.route('/student/mark_read/<int:book_id>')
@login_required
def mark_book_read(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if already marked as read
    existing = BookRead.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if existing:
        flash('You already marked this book as read.', 'info')
    else:
        book_read = BookRead(user_id=current_user.id, book_id=book_id)
        db.session.add(book_read)
        
        # Remove from reading list if present
        reading_item = ReadingListItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        if reading_item:
            db.session.delete(reading_item)
        
        db.session.commit()
        flash(f'"{book.title}" marked as read! Now add a review.', 'success')
        return redirect(url_for('create_review', book_id=book_id))
    
    return redirect(request.referrer or url_for('student_dashboard'))

@app.route('/student/books_read')
@login_required
def books_read():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))

    # Filter form for books read (applies to underlying book fields)
    filter_form = StudentBookFilterForm(request.args)
    genres = [g[0] for g in db.session.query(Book.genre).distinct() if g[0]]
    sub_genres = [sg[0] for sg in db.session.query(Book.sub_genre).distinct() if sg[0]]
    filter_form.genre.choices = [('', 'Any')] + [(g, g) for g in sorted(genres)]
    filter_form.sub_genre.choices = [('', 'Any')] + [(sg, sg) for sg in sorted(sub_genres)]

    q = BookRead.query.filter_by(user_id=current_user.id).join(Book, BookRead.book_id == Book.id)
    if filter_form.book_type.data:
        q = q.filter(Book.book_type == filter_form.book_type.data)
    if filter_form.genre.data:
        q = q.filter(Book.genre == filter_form.genre.data)
    if filter_form.sub_genre.data:
        q = q.filter(Book.sub_genre == filter_form.sub_genre.data)
    if filter_form.min_grade.data is not None:
        q = q.filter(Book.grade >= filter_form.min_grade.data)
    if filter_form.max_grade.data is not None:
        q = q.filter(Book.grade <= filter_form.max_grade.data)
    if filter_form.owned.data:
        q = q.filter(Book.owned == filter_form.owned.data)
    if filter_form.search.data:
        term = f"%{filter_form.search.data.strip()}%"
        q = q.filter(or_(Book.title.ilike(term), Book.author.ilike(term)))

    books_read = q.order_by(BookRead.completed_at.desc()).all()
    reviews = {r.book_id: r for r in Review.query.filter_by(user_id=current_user.id).all()}
    
    return render_template('student/books_read.html', books_read=books_read, reviews=reviews, filter_form=filter_form)

@app.route('/student/review/<int:book_id>', methods=['GET', 'POST'])
@login_required
def create_review(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if book is marked as read
    book_read = BookRead.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if not book_read:
        flash('You must mark the book as read before reviewing it.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Check if review already exists
    existing_review = Review.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    
    form = ReviewForm()
    print("DEBUG: form.rating.data =", form.rating.data)
    print("DEBUG: request.form.get('rating') =", request.form.get('rating'))
        
    if form.validate_on_submit():
        if existing_review:
            # Update existing review
            existing_review.rating = form.rating.data
            existing_review.what_liked = form.what_liked.data
            existing_review.what_learned = form.what_learned.data
            existing_review.recommend_to = form.recommend_to.data
            existing_review.favorite_part = form.favorite_part.data
            flash('Review updated!', 'success')
        else:
            # Create new review
            review = Review(
                user_id=current_user.id,
                book_id=book_id,
                rating=form.rating.data,
                what_liked=form.what_liked.data,
                what_learned=form.what_learned.data,
                recommend_to=form.recommend_to.data,
                favorite_part=form.favorite_part.data
            )
            db.session.add(review)
            flash('Review submitted!', 'success')
        
        db.session.commit()
        return redirect(url_for('books_read'))
    
    # Pre-fill form if editing
    if existing_review and request.method == 'GET':
        form.rating.data = existing_review.rating
        form.what_liked.data = existing_review.what_liked
        form.what_learned.data = existing_review.what_learned
        form.recommend_to.data = existing_review.recommend_to
        form.favorite_part.data = existing_review.favorite_part
    
    return render_template('student/create_review.html', form=form, book=book, existing_review=existing_review)

@app.route('/student/accept_suggestion/<int:suggestion_id>')
@login_required
def accept_suggestion(suggestion_id):
    suggestion = SuggestedBook.query.get_or_404(suggestion_id)
    
    if suggestion.student_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    suggestion.is_accepted = True
    
    # Add to reading list
    max_order = db.session.query(db.func.max(ReadingListItem.order)).filter_by(user_id=current_user.id).scalar() or 0
    item = ReadingListItem(
        user_id=current_user.id,
        book_id=suggestion.book_id,
        order=max_order + 1
    )
    db.session.add(item)
    db.session.commit()
    
    flash('Book added to your reading list!', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/student/suggest_new_book', methods=['GET', 'POST'])
@login_required
def student_suggest_new_book():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    form = BookSuggestionForm()
    if form.validate_on_submit():
        # Check if book already exists in library
        existing_book = Book.query.filter_by(
            author=form.author.data,
            title=form.title.data
        ).first()
        
        if existing_book:
            flash(f'"{form.title.data}" by {form.author.data} is already in the library!', 'info')
            return redirect(url_for('student_reading_list'))
        
        # Check if student already suggested this book
        existing_suggestion = BookSuggestion.query.filter_by(
            student_id=current_user.id,
            author=form.author.data,
            title=form.title.data,
            status='pending'
        ).first()
        
        if existing_suggestion:
            flash('You have already suggested this book. It is pending review.', 'info')
            return redirect(url_for('student_suggest_new_book'))
        
        # Create new suggestion
        suggestion = BookSuggestion(
            student_id=current_user.id,
            title=form.title.data,
            author=form.author.data,
            reason=form.reason.data
        )
        db.session.add(suggestion)
        db.session.commit()
        
        flash(f'Thank you for suggesting "{form.title.data}"! Your teacher will review it.', 'success')
        return redirect(url_for('student_dashboard'))
    
    # Get student's previous suggestions
    my_suggestions = BookSuggestion.query.filter_by(student_id=current_user.id).order_by(BookSuggestion.suggested_at.desc()).all()
    
    return render_template('student/suggest_new_book.html', form=form, my_suggestions=my_suggestions)

@app.route('/admin/book_suggestions')
@login_required
@admin_required
def admin_book_suggestions():
    # Get all pending suggestions
    pending = BookSuggestion.query.filter_by(status='pending').order_by(BookSuggestion.suggested_at.desc()).all()
    # Get recently reviewed suggestions
    reviewed = BookSuggestion.query.filter(BookSuggestion.status.in_(['approved', 'rejected', 'added'])).order_by(BookSuggestion.reviewed_at.desc()).limit(20).all()
    
    return render_template('admin/book_suggestions.html', pending=pending, reviewed=reviewed)

@app.route('/admin/book_suggestion/<int:suggestion_id>/review', methods=['POST'])
@login_required
@admin_required
def review_book_suggestion(suggestion_id):
    suggestion = BookSuggestion.query.get_or_404(suggestion_id)
    action = request.form.get('action')
    admin_notes = request.form.get('admin_notes', '')
    
    if action == 'approve':
        suggestion.status = 'approved'
        suggestion.reviewed_by_id = current_user.id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.admin_notes = admin_notes
        db.session.commit()
        flash(f'Approved suggestion for "{suggestion.title}". You can now add it to the library.', 'success')
    
    elif action == 'reject':
        suggestion.status = 'rejected'
        suggestion.reviewed_by_id = current_user.id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.admin_notes = admin_notes
        db.session.commit()
        flash(f'Rejected suggestion for "{suggestion.title}".', 'info')
    
    elif action == 'add':
        # Create the book and mark suggestion as added
        existing_book = Book.query.filter_by(author=suggestion.author, title=suggestion.title).first()
        
        if existing_book:
            flash(f'Book already exists in library!', 'warning')
            suggestion.book_id = existing_book.id
            suggestion.status = 'added'
        else:
            # Create book with basic info
            book = Book(
                title=suggestion.title,
                author=suggestion.author,
                description=f"Suggested by {suggestion.student.first_name} {suggestion.student.last_name}"
            )
            
            # Try to enrich from OpenLibrary
            try:
                enrich_book_from_openlibrary(book)
                flash(f'Added "{suggestion.title}" to the library with OpenLibrary metadata!', 'success')
            except Exception as e:
                # If enrichment fails, still add the book
                flash(f'Added "{suggestion.title}" to the library (OpenLibrary lookup failed).', 'success')
            
            db.session.add(book)
            db.session.flush()
            
            suggestion.book_id = book.id
            suggestion.status = 'added'
            suggestion.reviewed_by_id = current_user.id
            suggestion.reviewed_at = datetime.utcnow()
            suggestion.admin_notes = admin_notes
        
        db.session.commit()
    
    return redirect(url_for('admin_book_suggestions'))

# Student: Suggest Edit to Book
@app.route('/student/book/<int:book_id>/suggest-edit', methods=['POST'])
@login_required
def suggest_book_edit(book_id):
    if current_user.role != 'student':
        flash('Only students can suggest edits.', 'danger')
        return redirect(url_for('index'))
    
    book = Book.query.get_or_404(book_id)
    data = request.get_json()
    
    # Create edit suggestion with only changed fields
    suggestion = BookEditSuggestion(
        book_id=book_id,
        student_id=current_user.id,
        reason=data.get('reason', '')
    )
    
    # Only set fields that are different from current values
    if data.get('title') and data.get('title') != book.title:
        suggestion.suggested_title = data.get('title')
    if data.get('author') and data.get('author') != book.author:
        suggestion.suggested_author = data.get('author')
    if data.get('openlibrary_id') and data.get('openlibrary_id') != book.openlibrary_id:
        suggestion.suggested_openlibrary_id = data.get('openlibrary_id')
    if data.get('publication_year') and data.get('publication_year') != book.publication_year:
        suggestion.suggested_publication_year = data.get('publication_year')
    if data.get('book_type') and data.get('book_type') != book.book_type:
        suggestion.suggested_book_type = data.get('book_type')
    if data.get('genre') and data.get('genre') != book.genre:
        suggestion.suggested_genre = data.get('genre')
    if data.get('sub_genre') and data.get('sub_genre') != book.sub_genre:
        suggestion.suggested_sub_genre = data.get('sub_genre')
    if data.get('topic') and data.get('topic') != book.topic:
        suggestion.suggested_topic = data.get('topic')
    if data.get('lexile_rating') and data.get('lexile_rating') != book.lexile_rating:
        suggestion.suggested_lexile_rating = data.get('lexile_rating')
    if data.get('grade') and data.get('grade') != book.grade:
        suggestion.suggested_grade = data.get('grade')
    if data.get('description') and data.get('description') != book.description:
        suggestion.suggested_description = data.get('description')
    
    try:
        db.session.add(suggestion)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Edit suggestion submitted successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Admin: View Book Edit Suggestions
@app.route('/admin/book-edit-suggestions')
@login_required
@admin_required
def admin_book_edit_suggestions():
    pending = BookEditSuggestion.query.filter_by(status='pending').order_by(BookEditSuggestion.suggested_at.desc()).all()
    reviewed = BookEditSuggestion.query.filter(BookEditSuggestion.status.in_(['approved', 'rejected'])).order_by(BookEditSuggestion.reviewed_at.desc()).limit(20).all()
    return render_template('admin/book_edit_suggestions.html', pending=pending, reviewed=reviewed)

# Admin: Review Book Edit Suggestion
@app.route('/admin/book-edit-suggestion/<int:suggestion_id>/review', methods=['POST'])
@login_required
@admin_required
def review_book_edit_suggestion(suggestion_id):
    suggestion = BookEditSuggestion.query.get_or_404(suggestion_id)
    action = request.form.get('action')
    admin_notes = request.form.get('admin_notes', '')
    
    if action == 'approve':
        # Apply the suggested changes to the book
        book = suggestion.book
        if suggestion.suggested_title:
            book.title = suggestion.suggested_title
        if suggestion.suggested_author:
            book.author = suggestion.suggested_author
        if suggestion.suggested_openlibrary_id:
            book.openlibrary_id = suggestion.suggested_openlibrary_id
        if suggestion.suggested_publication_year:
            book.publication_year = suggestion.suggested_publication_year
        if suggestion.suggested_book_type:
            book.book_type = suggestion.suggested_book_type
        if suggestion.suggested_genre:
            book.genre = suggestion.suggested_genre
        if suggestion.suggested_sub_genre:
            book.sub_genre = suggestion.suggested_sub_genre
        if suggestion.suggested_topic:
            book.topic = suggestion.suggested_topic
        if suggestion.suggested_lexile_rating:
            book.lexile_rating = suggestion.suggested_lexile_rating
        if suggestion.suggested_grade:
            book.grade = suggestion.suggested_grade
        if suggestion.suggested_description:
            book.description = suggestion.suggested_description
        
        suggestion.status = 'approved'
        suggestion.reviewed_by_id = current_user.id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.admin_notes = admin_notes
        db.session.commit()
        flash(f'Approved edits for "{book.title}"!', 'success')
    
    elif action == 'reject':
        suggestion.status = 'rejected'
        suggestion.reviewed_by_id = current_user.id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.admin_notes = admin_notes
        db.session.commit()
        flash('Edit suggestion rejected.', 'info')
    
    return redirect(url_for('admin_book_edit_suggestions'))

# Initialize database
@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized!')

@app.cli.command()
@click.argument("file_path")
def process_csv(file_path):
    """Process book CSV import."""
    with open(file_path, 'r', encoding='utf-8') as fl:
        result = BookImportService.import_from_csv(fl, debug=True)
    
@app.cli.command()
def create_admin():
    """Create an admin user."""
    username = input('Username: ')
    email = input('Email: ')
    first_name = input('First Name: ')
    last_name = input('Last Name: ')
    password = input('Password: ')
    
    admin = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role='admin'
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f'Admin user {username} created successfully!')

def run_upgrade():
    """Lightweight DB upgrade: create tables and add missing columns."""
    # First, create all tables if they don't exist
    db.create_all()
    
    # Then check for missing columns in the book table
    # Use dialect-agnostic approach
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    
    # Check if book table exists
    if 'book' not in inspector.get_table_names():
        print('Database initialized with all tables.')
        return
    
    existing_cols = {col['name'] for col in inspector.get_columns('book')}
    alters = []
    
    # Determine database type
    dialect_name = db.engine.dialect.name
    
    if 'book_type' not in existing_cols:
        alters.append("ALTER TABLE book ADD COLUMN book_type VARCHAR(20)")
    if 'sub_genre' not in existing_cols:
        alters.append("ALTER TABLE book ADD COLUMN sub_genre VARCHAR(100)")
    if 'grade' not in existing_cols:
        alters.append("ALTER TABLE book ADD COLUMN grade INTEGER")
    if 'owned' not in existing_cols:
        if dialect_name == 'sqlite':
            alters.append("ALTER TABLE book ADD COLUMN owned VARCHAR(20) DEFAULT 'Not Owned'")
        else:  # PostgreSQL
            alters.append("ALTER TABLE book ADD COLUMN owned VARCHAR(20) DEFAULT 'Not Owned'")
    
    for stmt in alters:
        try:
            db.session.execute(db.text(stmt))
        except Exception as e:
            print(f'Warning: {e}')
    
    if alters:
        db.session.commit()
        print('Database upgraded: added columns ->', ', '.join([s.split()[5] for s in alters]))
    else:
        print('Database already up to date.')

@app.cli.command('upgrade-db')
def upgrade_db():
    """Upgrade the database schema (SQLite): add missing columns like book_type and sub_genre."""
    run_upgrade()

@app.cli.command('enrich-missing-books')
@click.option("--max", default=None, type=int, help="Maximum number of books to process")
def enrich_missing_books(max: int):
    """Backfill book_type and sub_genre for books missing them using OpenLibrary subjects (requires ISBN)."""
    updated = 0
    books = Book.query.all()
    for ib, b in enumerate(books):
        if max is not None and ib >= max:
            break

        updated += int(enrich_book_from_openlibrary(b))
        
    if updated:
        db.session.commit()
        
    print(f"Enriched {updated} book(s)")


# Routes for managing genres, sub-genres, topics, and genre maps
@app.route('/admin/genres')
@login_required
@admin_required
def admin_genres():
    genres = Genre.query.order_by(Genre.book_type, Genre.name).all()
    topics = Topic.query.order_by(Topic.name).all()
    genre_maps = GenreMap.query.order_by(GenreMap.alternative_name).all()
    
    return render_template('admin/genres.html',
                          genres=genres,
                          topics=topics,
                          genre_maps=genre_maps)


@app.route('/admin/genre/add', methods=['POST'])
@login_required
@admin_required
def add_genre():
    book_type = request.form.get('book_type')
    name = request.form.get('name')
    
    if not book_type or not name:
        flash('Book type and genre name are required.', 'danger')
        return redirect(url_for('admin_genres'))
    
    # Check if genre already exists
    existing = Genre.query.filter_by(book_type=book_type, name=name).first()
    if existing:
        flash(f'Genre "{name}" already exists for {book_type}.', 'danger')
        return redirect(url_for('admin_genres'))
    
    genre = Genre(book_type=book_type, name=name)
    db.session.add(genre)
    db.session.commit()
    
    flash(f'Genre "{name}" added successfully!', 'success')
    return redirect(url_for('admin_genres'))


@app.route('/admin/genre/<int:genre_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_genre(genre_id):
    genre = Genre.query.get_or_404(genre_id)
    
    # Check if any books use this genre
    books_with_genre = Book.query.filter_by(genre=genre.name).count()
    if books_with_genre > 0:
        flash(f'Cannot delete genre "{genre.name}" because {books_with_genre} book(s) use it.', 'danger')
        return redirect(url_for('admin_genres'))
    
    db.session.delete(genre)
    db.session.commit()
    
    flash(f'Genre "{genre.name}" deleted successfully!', 'success')
    return redirect(url_for('admin_genres'))


@app.route('/admin/subgenre/add', methods=['POST'])
@login_required
@admin_required
def add_subgenre():
    genre_id = request.form.get('genre_id')
    name = request.form.get('name')
    
    if not genre_id or not name:
        flash('Genre and sub-genre name are required.', 'danger')
        return redirect(url_for('admin_genres'))
    
    genre = Genre.query.get_or_404(genre_id)
    
    # Check if sub-genre already exists for this genre
    existing = SubGenre.query.filter_by(genre_id=genre_id, name=name).first()
    if existing:
        flash(f'Sub-genre "{name}" already exists for {genre.name}.', 'danger')
        return redirect(url_for('admin_genres'))
    
    subgenre = SubGenre(genre_id=genre_id, name=name)
    db.session.add(subgenre)
    db.session.commit()
    
    flash(f'Sub-genre "{name}" added successfully!', 'success')
    return redirect(url_for('admin_genres'))


@app.route('/admin/subgenre/<int:subgenre_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subgenre(subgenre_id):
    subgenre = SubGenre.query.get_or_404(subgenre_id)
    
    # Check if any books use this sub-genre
    books_with_subgenre = Book.query.filter_by(sub_genre=subgenre.name).count()
    if books_with_subgenre > 0:
        flash(f'Cannot delete sub-genre "{subgenre.name}" because {books_with_subgenre} book(s) use it.', 'danger')
        return redirect(url_for('admin_genres'))
    
    db.session.delete(subgenre)
    db.session.commit()
    
    flash(f'Sub-genre "{subgenre.name}" deleted successfully!', 'success')
    return redirect(url_for('admin_genres'))


@app.route('/admin/topic/add', methods=['POST'])
@login_required
@admin_required
def add_topic():
    name = request.form.get('name')
    
    if not name:
        flash('Topic name is required.', 'danger')
        return redirect(url_for('admin_genres'))
    
    # Check if topic already exists
    existing = Topic.query.filter_by(name=name).first()
    if existing:
        flash(f'Topic "{name}" already exists.', 'danger')
        return redirect(url_for('admin_genres'))
    
    topic = Topic(name=name)
    db.session.add(topic)
    db.session.commit()
    
    flash(f'Topic "{name}" added successfully!', 'success')
    return redirect(url_for('admin_genres'))


@app.route('/admin/topic/<int:topic_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    
    # Check if any books use this topic
    books_with_topic = Book.query.filter_by(topic=topic.name).count()
    if books_with_topic > 0:
        flash(f'Cannot delete topic "{topic.name}" because {books_with_topic} book(s) use it.', 'danger')
        return redirect(url_for('admin_genres'))
    
    db.session.delete(topic)
    db.session.commit()
    
    flash(f'Topic "{topic.name}" deleted successfully!', 'success')
    return redirect(url_for('admin_genres'))


@app.route('/admin/genremap/add', methods=['POST'])
@login_required
@admin_required
def add_genre_map():
    alternative_name = request.form.get('alternative_name')
    canonical_name = request.form.get('canonical_name')
    
    if not alternative_name or not canonical_name:
        flash('Both alternative name and canonical name are required.', 'danger')
        return redirect(url_for('admin_genres'))
    
    # Check if mapping already exists
    existing = GenreMap.query.filter_by(alternative_name=alternative_name).first()
    if existing:
        flash(f'Mapping for "{alternative_name}" already exists.', 'danger')
        return redirect(url_for('admin_genres'))
    
    genre_map = GenreMap(alternative_name=alternative_name, canonical_name=canonical_name)
    db.session.add(genre_map)
    db.session.commit()
    
    flash(f'Genre mapping added successfully!', 'success')
    return redirect(url_for('admin_genres'))


@app.route('/admin/genremap/<int:map_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_genre_map(map_id):
    genre_map = GenreMap.query.get_or_404(map_id)
    
    db.session.delete(genre_map)
    db.session.commit()
    
    flash(f'Genre mapping deleted successfully!', 'success')
    return redirect(url_for('admin_genres'))


@app.route('/api/genres/<book_type>')
def api_get_genres(book_type):
    """API endpoint to get genres for a given book type"""
    if book_type not in ['Fiction', 'Non-Fiction']:
        return jsonify([])
    
    genres = Genre.query.filter_by(book_type=book_type).order_by(Genre.name).all()
    return jsonify([{'id': g.id, 'name': g.name} for g in genres])


@app.route('/api/subgenres/<int:genre_id>')
def api_get_subgenres(genre_id):
    """API endpoint to get sub-genres for a given genre"""
    genre = Genre.query.get_or_404(genre_id)
    subgenres = SubGenre.query.filter_by(genre_id=genre_id).order_by(SubGenre.name).all()
    return jsonify([{'id': sg.id, 'name': sg.name} for sg in subgenres])


@app.route('/api/subgenres-by-name/<book_type>/<genre_name>')
def api_get_subgenres_by_name(book_type, genre_name):
    """API endpoint to get sub-genres by book type and genre name"""
    genre = Genre.query.filter_by(book_type=book_type, name=genre_name).first()
    if not genre:
        return jsonify([])
    
    subgenres = SubGenre.query.filter_by(genre_id=genre.id).order_by(SubGenre.name).all()
    return jsonify([{'id': sg.id, 'name': sg.name} for sg in subgenres])

@app.route('/api/fetch-openlibrary-metadata', methods=['POST'])
@login_required
@admin_required
def fetch_openlibrary_metadata():
    """Fetch metadata from OpenLibrary by work ID"""
    from csv_cli import CSVBookRecord
    
    data = request.get_json()
    olid = data.get('openlibrary_id', '').strip()
    
    if not olid:
        return jsonify({'error': 'OpenLibrary ID is required'}), 400
        
    try:
        record = CSVBookRecord.from_openlibrary_id(olid, ask=False, quick=True)
        return jsonify(record.asdict())
    
    except Exception as e:
        print(f"Error fetching OpenLibrary metadata: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
