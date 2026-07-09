"""
Mood-based movie recommender.

Scores movies using genre weights, user tags, title keywords, and ratings.
Supports single/multi-mood selection and a surprise-me mode.
"""
from __future__ import annotations

import random
import re

from backend.services.data_loader import data_store
from backend.services.mood_mapping import (
    MOOD_GENRE_WEIGHTS,
    MOOD_TAG_KEYWORDS,
    MOOD_TITLE_KEYWORDS,
    MOODS,
)
from backend.services.movie_enricher import enrich_movie


class MoodRecommender:
    MIN_RESULTS = 10
    MAX_RESULTS = 15

    def get_moods(self) -> list[dict]:
        return MOODS

    def recommend(
        self,
        mood_ids: list[str],
        surprise: bool = False,
        count: int | None = None,
    ) -> dict:
        data_store.load()
        movies = data_store.movies
        assert movies is not None

        if surprise or not mood_ids:
            mood_ids = [random.choice([m["id"] for m in MOODS])]
            surprise = True

        valid_ids = {m["id"] for m in MOODS}
        mood_ids = [m for m in mood_ids if m in valid_ids]
        if not mood_ids:
            return {"moods": [], "surprise": False, "recommendations": []}

        target_count = count or random.randint(self.MIN_RESULTS, self.MAX_RESULTS)
        scored: list[tuple[float, int]] = []

        for idx, row in movies.iterrows():
            movie_id = int(row["movieId"])
            score = self._score_movie(row, mood_ids)
            if score > 0:
                scored.append((score, idx))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Slight shuffle among top candidates for variety on repeat visits
        top_pool = scored[: max(target_count * 3, 40)]
        if surprise:
            random.shuffle(top_pool)

        selected = top_pool[:target_count]
        mood_labels = [
            next(m["label"] for m in MOODS if m["id"] == mid) for mid in mood_ids
        ]

        recommendations = []
        max_score = selected[0][0] if selected else 1.0

        for score, idx in selected:
            row = movies.iloc[idx]
            movie_id = int(row["movieId"])
            confidence = round(min(99.0, (score / max_score) * 100), 1)
            enriched = enrich_movie(row, mood_ids, mood_labels, confidence)
            recommendations.append(enriched)

        return {
            "moods": mood_ids,
            "mood_labels": mood_labels,
            "surprise": surprise,
            "recommendations": recommendations,
        }

    def _score_movie(self, row, mood_ids: list[str]) -> float:
        genres = [g.strip() for g in str(row["genres"]).split("|") if g.strip()]
        if not genres or genres == ["(no genres listed)"]:
            return 0.0

        movie_id = int(row["movieId"])
        tags = data_store.tags_by_movie.get(movie_id, set())
        title_lower = str(row["title"]).lower()
        title_tokens = set(re.findall(r"[a-z]+", title_lower))

        genre_score = 0.0
        tag_score = 0.0
        title_score = 0.0

        for mood_id in mood_ids:
            weights = MOOD_GENRE_WEIGHTS.get(mood_id, {})
            for genre in genres:
                genre_score += weights.get(genre, 0.0)

            tag_keywords = MOOD_TAG_KEYWORDS.get(mood_id, set())
            tag_hits = sum(1 for t in tags if any(kw in t for kw in tag_keywords))
            tag_score += tag_hits * 0.35

            title_keywords = MOOD_TITLE_KEYWORDS.get(mood_id, set())
            title_hits = len(title_tokens & title_keywords)
            title_score += title_hits * 0.25

        # Normalize multi-mood: average then boost movies matching ALL moods
        n = len(mood_ids)
        base = (genre_score + tag_score + title_score) / n

        if n > 1:
            mood_hits = sum(
                1
                for mood_id in mood_ids
                if self._movie_matches_mood(genres, tags, title_tokens, mood_id)
            )
            if mood_hits == n:
                base *= 1.25  # Boost films fitting every selected mood

        # Quality boost from community ratings
        avg_rating = data_store.avg_ratings.get(movie_id)
        rating_count = data_store.rating_counts.get(movie_id, 0)
        if avg_rating and rating_count >= 5:
            base += (avg_rating / 5.0) * 0.4

        return base

    def _movie_matches_mood(
        self, genres: list[str], tags: set[str], title_tokens: set[str], mood_id: str
    ) -> bool:
        weights = MOOD_GENRE_WEIGHTS.get(mood_id, {})
        if any(weights.get(g, 0) >= 0.5 for g in genres):
            return True
        tag_keywords = MOOD_TAG_KEYWORDS.get(mood_id, set())
        if any(any(kw in t for kw in tag_keywords) for t in tags):
            return True
        title_keywords = MOOD_TITLE_KEYWORDS.get(mood_id, set())
        return bool(title_tokens & title_keywords)


mood_recommender = MoodRecommender()
