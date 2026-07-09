"""Entry point for the Movie Recommendation app."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.app import app, content_recommender, data_store

if __name__ == "__main__":
    data_store.load()
    content_recommender._ensure_fitted()
    app.run(host="0.0.0.0", port=5000, debug=True)
