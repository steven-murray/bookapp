from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from config import Config
from models import db, User, Class, Book, Review, BookRead, ReadingListItem, SuggestedBook
from forms import (LoginForm, RegistrationForm, ClassForm, BookForm, CSVUploadForm, 
                   ReviewForm, SuggestBookForm, SearchBookForm, StudentBookFilterForm)
from openlibrary_service import OpenLibraryService
from book_import_service import BookImportService
from datetime import datetime
import io
from sqlalchemy import or_

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    
    return render_template('admin/dashboard.html', 
                         classes=classes,
                         total_students=total_students,
                         total_books=total_books,
                         recent_reviews=recent_reviews)

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
    books = Book.query.all()
    return render_template('admin/books.html', books=books, search_form=search_form)

@app.route('/admin/book/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_book():
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            isbn=form.isbn.data,
            book_type=form.book_type.data or None,
            sub_genre=form.sub_genre.data or None,
            genre=form.genre.data,
            topic=form.topic.data,
            lexile_rating=form.lexile_rating.data,
            grade=form.grade.data if form.grade.data is not None else None,
            owned=form.owned.data or 'Not Owned',
            description=form.description.data
        )
        
        # Try to enrich from OpenLibrary if ISBN provided
        if book.isbn:
            ol_data = OpenLibraryService.get_book_by_isbn(book.isbn)
            if ol_data:
                if not book.title:
                    book.title = ol_data.get('title', '')
                if not book.author:
                    book.author = ol_data.get('author', '')
                book.openlibrary_id = ol_data.get('openlibrary_id', '')
                book.cover_url = ol_data.get('cover_url', '')
                book.publication_year = ol_data.get('publication_year')
                # Infer type/sub-genre when not provided from the form
                subjects = ol_data.get('subjects') or []
                lower_subjects = [s.lower() for s in subjects]
                if not book.book_type:
                    if any(('nonfiction' in s) or ('non-fiction' in s) for s in lower_subjects):
                        book.book_type = 'Non-Fiction'
                    elif any('fiction' in s for s in lower_subjects):
                        book.book_type = 'Fiction'
                if not book.sub_genre and subjects:
                    preferred = next((s for s in subjects if 'fiction' not in s.lower() and 'non' not in s.lower()), None)
                    if preferred:
                        book.sub_genre = preferred
        
        db.session.add(book)
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('admin_books'))
    
    return render_template('admin/create_book.html', form=form)

@app.route('/admin/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm()

    if form.validate_on_submit():
        # Unique ISBN check if changed
        new_isbn = form.isbn.data.strip() if form.isbn.data else None
        if new_isbn and new_isbn != (book.isbn or None):
            exists = Book.query.filter(Book.isbn == new_isbn, Book.id != book.id).first()
            if exists:
                flash('Another book with this ISBN already exists.', 'danger')
                return render_template('admin/edit_book.html', form=form, book=book)

        # Update fields
        book.title = form.title.data
        book.author = form.author.data or None
        book.isbn = new_isbn
        book.book_type = form.book_type.data or None
        book.sub_genre = form.sub_genre.data or None
        book.genre = form.genre.data or None
        book.topic = form.topic.data or None
        book.lexile_rating = form.lexile_rating.data or None
        book.grade = form.grade.data if form.grade.data is not None else None
        book.owned = form.owned.data or 'Not Owned'
        book.description = form.description.data or None

        db.session.commit()
        flash('Book updated successfully!', 'success')
        return redirect(url_for('admin_books'))

    # Pre-fill form with current values
    if request.method == 'GET':
        form.title.data = book.title
        form.author.data = book.author
        form.isbn.data = book.isbn
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
        result = BookImportService.import_from_csv(form.csv_file.data)
        
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
    isbn = request.form.get('isbn')
    openlibrary_id = request.form.get('openlibrary_id')
    cover_id = request.form.get('cover_id')
    publication_year = request.form.get('publication_year')
    
    # Check if book already exists by ISBN
    if isbn:
        existing_book = Book.query.filter_by(isbn=isbn).first()
        if existing_book:
            flash(f'Book "{title}" already exists in the library.', 'info')
            return redirect(url_for('admin_books'))
    
    # Create new book
    book = Book(
        title=title,
        author=author,
        isbn=isbn if isbn else None,
        openlibrary_id=openlibrary_id if openlibrary_id else None,
        publication_year=int(publication_year) if publication_year and publication_year != 'None' else None
    )
    
    # Set cover URL if available
    if cover_id and cover_id != 'None':
        book.cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    
    # Try to get additional details from OpenLibrary if ISBN is available
    if isbn and isbn != 'None':
        ol_data = OpenLibraryService.get_book_by_isbn(isbn)
        if ol_data:
            if not book.description:
                book.description = ol_data.get('description', '')
            if not book.genre:
                book.genre = ol_data.get('genre', '')
            # Infer book_type and sub_genre from OpenLibrary subjects, when possible
            subjects = ol_data.get('subjects') or []
            lower_subjects = [s.lower() for s in subjects]
            if not book.book_type:
                if any(('nonfiction' in s) or ('non-fiction' in s) for s in lower_subjects):
                    book.book_type = 'Non-Fiction'
                elif any('fiction' in s for s in lower_subjects):
                    book.book_type = 'Fiction'
            if not book.sub_genre and subjects:
                # choose the first subject that isn't a generic fiction/nonfiction label
                preferred = next((s for s in subjects if 'fiction' not in s.lower() and 'non' not in s.lower()), None)
                if preferred:
                    book.sub_genre = preferred
    
    db.session.add(book)
    db.session.commit()
    
    flash(f'Book "{title}" added to library successfully!', 'success')
    return redirect(url_for('admin_books'))

@app.route('/admin/book/<int:book_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Remove suggestions referencing this book to avoid FK issues
    SuggestedBook.query.filter_by(book_id=book_id).delete(synchronize_session=False)
    
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('admin_books'))

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

    all_books = [b for b in query.all() if b.id not in read_book_ids]

    return render_template('student/reading_list.html', reading_list=reading_list, all_books=all_books, filter_form=filter_form)

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

# Initialize database
@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized!')

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
    """Lightweight DB upgrade: add new columns if missing (SQLite only)."""
    # Check existing columns in 'book' table
    result = db.session.execute(db.text("PRAGMA table_info(book)"))
    existing_cols = {row[1] for row in result}
    alters = []
    if 'book_type' not in existing_cols:
        alters.append("ALTER TABLE book ADD COLUMN book_type VARCHAR(20)")
    if 'sub_genre' not in existing_cols:
        alters.append("ALTER TABLE book ADD COLUMN sub_genre VARCHAR(100)")
    if 'grade' not in existing_cols:
        alters.append("ALTER TABLE book ADD COLUMN grade INTEGER")
    if 'owned' not in existing_cols:
        alters.append("ALTER TABLE book ADD COLUMN owned VARCHAR(20) DEFAULT 'Not Owned'")
    for stmt in alters:
        db.session.execute(db.text(stmt))
    if alters:
        db.session.commit()
        print('Database upgraded: added columns ->', ', '.join([s.split()[-1] if 'DEFAULT' not in s else s.split()[5] for s in alters]))
    else:
        print('Database already up to date.')

@app.cli.command('upgrade-db')
def upgrade_db():
    """Upgrade the database schema (SQLite): add missing columns like book_type and sub_genre."""
    run_upgrade()

@app.cli.command('enrich-missing-books')
def enrich_missing_books():
    """Backfill book_type and sub_genre for books missing them using OpenLibrary subjects (requires ISBN)."""
    updated = 0
    books = Book.query.all()
    for b in books:
        if (b.book_type and b.sub_genre) or not b.isbn:
            continue
        ol_data = OpenLibraryService.get_book_by_isbn(b.isbn)
        if not ol_data:
            continue
        subjects = ol_data.get('subjects') or []
        lower_subjects = [s.lower() for s in subjects]
        changed = False
        if not b.book_type:
            if any(('nonfiction' in s) or ('non-fiction' in s) for s in lower_subjects):
                b.book_type = 'Non-Fiction'
                changed = True
            elif any('fiction' in s for s in lower_subjects):
                b.book_type = 'Fiction'
                changed = True
        if not b.sub_genre and subjects:
            preferred = next((s for s in subjects if 'fiction' not in s.lower() and 'non' not in s.lower()), None)
            if preferred:
                b.sub_genre = preferred
                changed = True
        if changed:
            updated += 1
    if updated:
        db.session.commit()
    print(f"Enriched {updated} book(s)")

if __name__ == '__main__':
    app.run(debug=True)
