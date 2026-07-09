"""
Enrich movie records with posters, ratings, and mood explanations.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import quote

import requests

from backend.config import POSTER_CACHE_FILE
from backend.services.data_loader import data_store
from backend.services.mood_mapping import generate_explanation

CINEMETA_URL = "https://v3-cinemeta.strem.io/meta/movie/{imdb_id}.json"
TMDB_POSTER_URL = "https://image.tmdb.org/t/p/w500/{poster_path}"


class PosterCache:
    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if POSTER_CACHE_FILE.exists():
            try:
                self._cache = json.loads(POSTER_CACHE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def save(self) -> None:
        POSTER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        POSTER_CACHE_FILE.write_text(
            json.dumps(self._cache, indent=2), encoding="utf-8"
        )

    def get(self, imdb_id: str) -> str | None:
        return self._cache.get(imdb_id)

    def set(self, imdb_id: str, url: str) -> None:
        self._cache[imdb_id] = url


poster_cache = PosterCache()


def format_imdb_id(raw_id) -> str | None:
    if raw_id is None or (isinstance(raw_id, float) and str(raw_id) == "nan"):
        return None
    digits = str(int(raw_id)).zfill(7)
    return f"tt{digits}"


def get_imdb_rating_proxy(movie_id: int) -> float | None:
    """MovieLens avg rating scaled to a 0–10 IMDb-like scale."""
    avg = data_store.avg_ratings.get(movie_id)
    if avg is None:
        return None
    return round(float(avg) * 2, 1)


def fetch_poster(imdb_id: str, tmdb_id: int | None = None, allow_network: bool = True) -> str:
    cached = poster_cache.get(imdb_id)
    if cached:
        return cached

    if not allow_network:
        return placeholder_poster(imdb_id)

    # Try Cinemeta (free, no API key) with short timeout
    try:
        resp = requests.get(CINEMETA_URL.format(imdb_id=imdb_id), timeout=1.5)
        if resp.ok:
            meta = resp.json().get("meta", {})
            poster = meta.get("poster") or meta.get("background")
            if poster:
                poster_cache.set(imdb_id, poster)
                return poster
    except requests.RequestException:
        pass

    # Optional TMDB fallback
    tmdb_key = os.environ.get("TMDB_API_KEY")
    if tmdb_key and tmdb_id:
        try:
            resp = requests.get(
                f"https://api.themoviedb.org/3/movie/{tmdb_id}",
                params={"api_key": tmdb_key},
                timeout=1.5,
            )
            if resp.ok:
                path = resp.json().get("poster_path")
                if path:
                    url = TMDB_POSTER_URL.format(poster_path=path.lstrip("/"))
                    poster_cache.set(imdb_id, url)
                    return url
        except requests.RequestException:
            pass

    placeholder = placeholder_poster(imdb_id)
    poster_cache.set(imdb_id, placeholder)
    return placeholder


def placeholder_poster(imdb_id: str) -> str:
    """Deterministic gradient placeholder when no poster is available."""
    seed = imdb_id.replace("tt", "")
    hues = ["1a1a2e", "16213e", "0f3460", "533483", "2d4059", "1b262c"]
    bg = hues[int(seed[-2:]) % len(hues)]
    accent = hues[(int(seed[-2:]) + 2) % len(hues)]
    text = quote(imdb_id)
    return (
        f"https://placehold.co/300x450/{bg}/{accent}?text={text}"
        "&font=roboto"
    )


def enrich_movie(
    row,
    mood_ids: list[str],
    mood_labels: list[str],
    confidence: float,
) -> dict:
    movie_id = int(row["movieId"])
    links = data_store.get_links_row(movie_id)
    imdb_id = format_imdb_id(links["imdbId"]) if links else None
    tmdb_id = int(links["tmdbId"]) if links and links.get("tmdbId") else None

    year_val = row.get("year")
    year = int(year_val) if year_val is not None and str(year_val) != "nan" else None

    poster = fetch_poster(imdb_id, tmdb_id) if imdb_id else placeholder_poster("unknown")
    imdb_rating = get_imdb_rating_proxy(movie_id)

    genres = str(row["genres"])
    explanation = generate_explanation(
        title=str(row["title"]),
        genres=genres,
        year=year,
        mood_ids=mood_ids,
        mood_labels=mood_labels,
        confidence=confidence,
    )

    return {
        "movieId": movie_id,
        "title": row["title"],
        "year": year,
        "imdbRating": imdb_rating,
        "genres": genres.replace("|", ", "),
        "poster": poster,
        "explanation": explanation,
        "confidence": confidence,
        "imdbId": imdb_id,
    }


def enrich_similar_movie(row, similarity: float) -> dict:
    """Enrich content-based recommendations with poster and rating."""
    movie_id = int(row["movieId"])
    links = data_store.get_links_row(movie_id)
    imdb_id = format_imdb_id(links["imdbId"]) if links else None
    tmdb_id = int(links["tmdbId"]) if links and links.get("tmdbId") else None

    year_val = row.get("year")
    if "year" not in row or year_val is None:
        match = re.search(r"\((\d{4})\)", str(row["title"]))
        year = int(match.group(1)) if match else None
    else:
        year = int(year_val) if str(year_val) != "nan" else None

    poster = fetch_poster(imdb_id, tmdb_id) if imdb_id else placeholder_poster("unknown")

    return {
        "movieId": movie_id,
        "title": row["title"],
        "year": year,
        "imdbRating": get_imdb_rating_proxy(movie_id),
        "genres": str(row["genres"]).replace("|", ", "),
        "poster": poster,
        "similarity": similarity,
    }
