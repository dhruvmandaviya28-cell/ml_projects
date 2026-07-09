"""Application configuration."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "ml-latest-small"

MOVIES_CSV = DATA_DIR / "movies.csv"
RATINGS_CSV = DATA_DIR / "ratings.csv"
LINKS_CSV = DATA_DIR / "links.csv"
TAGS_CSV = DATA_DIR / "tags.csv"

POSTER_CACHE_FILE = BASE_DIR / "data" / "poster_cache.json"

# Optional: set TMDB_API_KEY env var for richer poster metadata
TMDB_API_KEY = None  # loaded from os.environ in app startup
