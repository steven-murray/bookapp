from bookapp.app import db, app
from bookapp.models import Review, User, Book

app.app_context().push()

# To see all reviews:
for r in Review.query.all():
    print(f"Review ID: {r.id}, User: {r.user_id}, Book: {r.book_id}, Rating: {r.rating}, Type: {type(r.rating)}, Created: {r.created_at}")
