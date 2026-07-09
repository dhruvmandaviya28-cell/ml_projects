"""
Content-based movie recommender (original notebook logic).

Uses TF-IDF on genres + KNN, matching the Jupyter notebook approach.
"""
from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

from backend.services.data_loader import data_store


class ContentRecommender:
    def __init__(self) -> None:
        self._model: NearestNeighbors | None = None
        self._tfidf_matrix = None
        self._fitted = False

    def _ensure_fitted(self) -> None:
        if self._fitted:
            return

        data_store.load()
        movies = data_store.movies
        assert movies is not None

        tfidf = TfidfVectorizer(token_pattern=r"[^|]+")
        self._tfidf_matrix = tfidf.fit_transform(movies["genres"])
        self._model = NearestNeighbors(
            metric="cosine", algorithm="brute", n_neighbors=12
        )
        self._model.fit(self._tfidf_matrix)
        self._fitted = True

    def recommend(self, movie_title: str, count: int = 10) -> dict:
        """Return similar movies for a given title."""
        self._ensure_fitted()
        data_store.load()
        movies = data_store.movies
        assert movies is not None and self._model is not None

        movie_row = data_store.get_movie_by_title(movie_title)
        if movie_row is None:
            return {"found": False, "query": movie_title, "recommendations": []}

        idx = int(movie_row.name)
        distances, indices = self._model.kneighbors(
            self._tfidf_matrix[idx], n_neighbors=min(count + 1, 12)
        )

        results = []
        for dist, movie_idx in zip(distances[0][1:], indices[0][1:], strict=False):
            row = movies.iloc[movie_idx]
            similarity = round(float(1 - dist) * 100, 1)
            results.append(
                {
                    "movieId": int(row["movieId"]),
                    "title": row["title"],
                    "genres": row["genres"],
                    "year": _safe_year(row),
                    "similarity": similarity,
                }
            )

        return {
            "found": True,
            "query": movie_row["title"],
            "recommendations": results[:count],
        }


def _safe_year(row) -> int | None:
    year = row.get("year")
    if year is None or (isinstance(year, float) and pd.isna(year)):
        return None
    return int(year)


content_recommender = ContentRecommender()
