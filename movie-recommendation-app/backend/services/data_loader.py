"""Load and prepare MovieLens datasets."""
from __future__ import annotations

import re

import pandas as pd

from backend.config import LINKS_CSV, MOVIES_CSV, RATINGS_CSV, TAGS_CSV


YEAR_PATTERN = re.compile(r"\((\d{4})\)")


class MovieDataStore:
    """Central data store shared by all recommendation engines."""

    def __init__(self) -> None:
        self.movies: pd.DataFrame | None = None
        self.ratings: pd.DataFrame | None = None
        self.links: pd.DataFrame | None = None
        self.tags_by_movie: dict[int, set[str]] = {}
        self.avg_ratings: dict[int, float] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        self.movies = pd.read_csv(MOVIES_CSV)
        self.ratings = pd.read_csv(RATINGS_CSV)
        self.links = pd.read_csv(LINKS_CSV)

        self.movies["genres"] = self.movies["genres"].fillna("")
        self.movies["year"] = self.movies["title"].str.extract(YEAR_PATTERN)[0]
        self.movies["year"] = pd.to_numeric(self.movies["year"], errors="coerce")
        self.movies["title_clean"] = self.movies["title"].str.lower().str.strip()

        rating_stats = (
            self.ratings.groupby("movieId")["rating"]
            .agg(["mean", "count"])
            .reset_index()
        )
        self.avg_ratings = dict(
            zip(rating_stats["movieId"], rating_stats["mean"], strict=False)
        )
        self.rating_counts = dict(
            zip(rating_stats["movieId"], rating_stats["count"], strict=False)
        )

        tags_df = pd.read_csv(TAGS_CSV)
        for movie_id, group in tags_df.groupby("movieId"):
            self.tags_by_movie[int(movie_id)] = {
                str(tag).lower().strip() for tag in group["tag"]
            }

        self._loaded = True

    def get_movie_by_title(self, title: str) -> pd.Series | None:
        self.load()
        assert self.movies is not None
        normalized = title.lower().strip()
        matches = self.movies[self.movies["title_clean"] == normalized]
        if matches.empty:
            # Partial match fallback
            matches = self.movies[
                self.movies["title_clean"].str.contains(
                    re.escape(normalized), regex=True, na=False
                )
            ]
        if matches.empty:
            return None
        return matches.iloc[0]

    def search_titles(self, query: str, limit: int = 10) -> list[str]:
        self.load()
        assert self.movies is not None
        if not query.strip():
            return []
        normalized = query.lower().strip()
        mask = self.movies["title_clean"].str.contains(
            re.escape(normalized), regex=True, na=False
        )
        return self.movies.loc[mask, "title"].head(limit).tolist()

    def get_links_row(self, movie_id: int) -> dict | None:
        self.load()
        assert self.links is not None
        row = self.links[self.links["movieId"] == movie_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()


# Singleton used by the Flask app
data_store = MovieDataStore()
