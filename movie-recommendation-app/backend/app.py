"""
Flask API for the Movie Recommendation System.

Endpoints:
  GET  /api/health
  GET  /api/stats
  GET  /api/moods
  GET  /api/search?q=
  GET  /api/trending?count=12
  GET  /api/movie/<int:movie_id>
  GET  /api/recommend?title=
  POST /api/recommend/mood  { moods: [], surprise: bool }
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Allow running as `python backend/app.py` or `python run.py`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.content_recommender import content_recommender
from backend.services.data_loader import data_store
from backend.services.mood_recommender import mood_recommender
from backend.services.movie_enricher import enrich_similar_movie, poster_cache

FRONTEND_DIR = ROOT / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(FRONTEND_DIR, "favicon.ico")


@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    return send_from_directory(FRONTEND_DIR, "apple-touch-icon.png")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/stats")
def stats():
    """Dataset statistics."""
    data_store.load()
    movies = data_store.movies
    ratings = data_store.ratings
    assert movies is not None and ratings is not None
    unique_users = int(ratings["userId"].nunique())
    return jsonify(
        {
            "movies": len(movies),
            "ratings": len(ratings),
            "users": unique_users,
        }
    )


@app.route("/api/moods")
def get_moods():
    return jsonify({"moods": mood_recommender.get_moods()})


@app.route("/api/search")
def search():
    query = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 10)), 25)
    titles = data_store.search_titles(query, limit=limit)
    return jsonify({"query": query, "results": titles})


@app.route("/api/trending")
def trending():
    """Return top-rated, popular movies (used for homepage hero)."""
    count = min(int(request.args.get("count", 12)), 24)
    data_store.load()
    movies = data_store.movies
    assert movies is not None

    # Require at least 50 ratings, sort by avg rating
    min_ratings = 50
    qualified = [
        movie_id
        for movie_id, cnt in data_store.rating_counts.items()
        if cnt >= min_ratings
    ]
    # Build (avg_rating, movie_id) list, sort descending
    scored = sorted(
        ((data_store.avg_ratings[mid], mid) for mid in qualified if mid in data_store.avg_ratings),
        reverse=True,
    )
    # Take top 40 then pick `count` with slight variety shuffle (not fully random)
    import random
    pool = scored[:40]
    # Stable top selection but add variety by sampling from top pool
    sample = pool[:count]

    results = []
    for _score, movie_id in sample:
        row = movies[movies["movieId"] == movie_id]
        if row.empty:
            continue
        row = row.iloc[0]
        enriched = enrich_similar_movie(row, round(float(_score / 5.0) * 100, 1))
        enriched["avgRating"] = round(float(_score), 2)
        results.append(enriched)

    poster_cache.save()
    return jsonify({"trending": results})


@app.route("/api/movie/<int:movie_id>")
def movie_detail(movie_id: int):
    """Return details for a single movie."""
    data_store.load()
    movies = data_store.movies
    assert movies is not None
    row = movies[movies["movieId"] == movie_id]
    if row.empty:
        return jsonify({"error": "Movie not found"}), 404
    row = row.iloc[0]
    enriched = enrich_similar_movie(row, 0.0)
    # Add tags
    tags = sorted(data_store.tags_by_movie.get(movie_id, set()))
    enriched["tags"] = tags
    enriched["ratingCount"] = data_store.rating_counts.get(movie_id, 0)
    return jsonify(enriched)


@app.route("/api/recommend")
def recommend():
    """Original content-based recommendations (preserved from notebook)."""
    title = request.args.get("title", "")
    count = min(int(request.args.get("count", 10)), 15)

    result = content_recommender.recommend(title, count=count)
    if not result["found"]:
        return jsonify(result), 404

    data_store.load()
    movies = data_store.movies
    assert movies is not None

    enriched = []
    for rec in result["recommendations"]:
        row = movies[movies["movieId"] == rec["movieId"]].iloc[0]
        enriched.append(enrich_similar_movie(row, rec["similarity"]))

    poster_cache.save()
    return jsonify(
        {
            "found": True,
            "query": result["query"],
            "recommendations": enriched,
        }
    )


@app.route("/api/recommend/mood", methods=["POST"])
def recommend_mood():
    """
    Mood-based recommendations.

    Body: { "moods": ["happy", "romantic"], "surprise": false, "count": 12 }
    """
    body = request.get_json(silent=True) or {}
    mood_ids = body.get("moods", [])
    surprise = bool(body.get("surprise", False))
    count = body.get("count")

    if count is not None:
        count = min(max(int(count), 10), 15)

    result = mood_recommender.recommend(
        mood_ids=mood_ids if isinstance(mood_ids, list) else [],
        surprise=surprise,
        count=count,
    )

    # Persist poster cache after batch enrichment
    poster_cache.save()

    return jsonify(result)


def create_app() -> Flask:
    """Factory for testing."""
    data_store.load()
    content_recommender._ensure_fitted()
    return app


if __name__ == "__main__":
    data_store.load()
    content_recommender._ensure_fitted()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
