"""
Migration script to create Genre and SubGenre tables and populate from genres_and_topics.toml
"""
import toml
from bookapp.app import app
from bookapp.models import db, Genre, SubGenre, Topic, GenreMap

def load_genres_from_toml():
    """Load genres and sub-genres from TOML file"""
    with open('genres_and_topics.toml', 'r') as f:
        data = toml.load(f)
    return data

def migrate():
    with app.app_context():
        print("Creating Genre, SubGenre, Topic, and GenreMap tables...")
        
        # Create tables
        db.create_all()
        
        # Check if already populated
        if Genre.query.first():
            print("Genre table already populated.")
        else:
            print("Loading data from genres_and_topics.toml...")
            data = load_genres_from_toml()
            
            # Process Fiction and Non-Fiction genres
            genres_data = data['genres']
            for book_type, genres in genres_data.items():
                print(f"\nProcessing {book_type} genres...")
                
                for genre_name, sub_genres in genres.items():
                    # Create genre
                    genre = Genre(book_type=book_type, name=genre_name)
                    db.session.add(genre)
                    db.session.flush()  # Get the genre ID
                    
                    print(f"  Added genre: {genre_name}")
                    
                    # Create sub-genres
                    for sub_genre_name in sub_genres:
                        sub_genre = SubGenre(genre_id=genre.id, name=sub_genre_name)
                        db.session.add(sub_genre)
                        print(f"    Added sub-genre: {sub_genre_name}")
            
            db.session.commit()
            genre_count = Genre.query.count()
            sub_genre_count = SubGenre.query.count()
            print(f"\n✅ Genres migrated: {genre_count} genres, {sub_genre_count} sub-genres")
        
        # Process Topics
        if Topic.query.first():
            print("\nTopic table already populated.")
        else:
            print("\nProcessing topics...")
            data = load_genres_from_toml()
            topics_data = data.get('topics', [])
            
            for topic_name in topics_data:
                topic = Topic(name=topic_name)
                db.session.add(topic)
                print(f"  Added topic: {topic_name}")
            
            db.session.commit()
            topic_count = Topic.query.count()
            print(f"\n✅ Topics migrated: {topic_count} topics")
        
        # Process Genre Maps
        if GenreMap.query.first():
            print("\nGenreMap table already populated.")
        else:
            print("\nProcessing genre mappings...")
            data = load_genres_from_toml()
            genre_maps_data = data.get('genre_maps', {})
            
            for alternative, canonical in genre_maps_data.items():
                genre_map = GenreMap(alternative_name=alternative, canonical_name=canonical)
                db.session.add(genre_map)
                print(f"  Added mapping: {alternative} -> {canonical}")
            
            db.session.commit()
            map_count = GenreMap.query.count()
            print(f"\n✅ Genre maps migrated: {map_count} mappings")
        
        print(f"\n🎉 Migration complete!")


if __name__ == '__main__':
    migrate()
