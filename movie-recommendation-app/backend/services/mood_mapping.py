"""
Genre, keyword, and tag mappings for mood-based recommendations.

Movies can belong to multiple moods; scoring combines genre weights,
user tags, and title keywords.
"""

MOODS = [
    {"id": "happy", "label": "Happy", "emoji": "😊"},
    {"id": "sad", "label": "Sad", "emoji": "😢"},
    {"id": "thrilling", "label": "Thrilling", "emoji": "😨"},
    {"id": "romantic", "label": "Romantic", "emoji": "❤️"},
    {"id": "funny", "label": "Funny", "emoji": "😂"},
    {"id": "thought-provoking", "label": "Thought-provoking", "emoji": "🤔"},
    {"id": "relaxing", "label": "Relaxing", "emoji": "😌"},
    {"id": "motivational", "label": "Motivational", "emoji": "🚀"},
    {"id": "family", "label": "Family", "emoji": "👨‍👩‍👧"},
    {"id": "horror", "label": "Horror", "emoji": "👻"},
]

# Primary genre weights per mood (0.0–1.0)
MOOD_GENRE_WEIGHTS = {
    "happy": {
        "Comedy": 1.0,
        "Animation": 0.85,
        "Musical": 0.9,
        "Children": 0.7,
        "Fantasy": 0.6,
        "Adventure": 0.5,
    },
    "sad": {
        "Drama": 1.0,
        "Romance": 0.55,
        "War": 0.75,
        "Biography": 0.6,
    },
    "thrilling": {
        "Thriller": 1.0,
        "Action": 0.85,
        "Crime": 0.8,
        "Mystery": 0.85,
        "Adventure": 0.45,
        "Sci-Fi": 0.5,
    },
    "romantic": {
        "Romance": 1.0,
        "Comedy": 0.45,
        "Drama": 0.5,
    },
    "funny": {
        "Comedy": 1.0,
        "Animation": 0.55,
        "Musical": 0.5,
    },
    "thought-provoking": {
        "Sci-Fi": 1.0,
        "Documentary": 0.95,
        "Drama": 0.65,
        "Mystery": 0.7,
        "War": 0.6,
        "Fantasy": 0.45,
    },
    "relaxing": {
        "Animation": 0.85,
        "Fantasy": 0.8,
        "Children": 0.75,
        "Comedy": 0.5,
        "Romance": 0.45,
        "Documentary": 0.55,
    },
    "motivational": {
        "Biography": 1.0,
        "Sport": 0.95,
        "Drama": 0.65,
        "Documentary": 0.7,
        "War": 0.55,
    },
    "family": {
        "Children": 1.0,
        "Animation": 0.9,
        "Adventure": 0.75,
        "Comedy": 0.55,
        "Fantasy": 0.65,
    },
    "horror": {
        "Horror": 1.0,
        "Thriller": 0.55,
        "Mystery": 0.35,
    },
}

# User-applied tags that reinforce each mood
MOOD_TAG_KEYWORDS = {
    "happy": {"feel-good", "uplifting", "happy", "fun", "cheerful", "heartwarming", "classic"},
    "sad": {"sad", "emotional", "tearjerker", "tragedy", "depressing", "melancholy", "cry"},
    "thrilling": {"suspense", "twist ending", "intense", "edge of your seat", "action", "dark"},
    "romantic": {"romantic", "love story", "romance", "relationship", "date night"},
    "funny": {"funny", "hilarious", "comedy", "humor", "quotable", "satire", "parody"},
    "thought-provoking": {
        "philosophical",
        "mind-bending",
        "twist ending",
        "psychological",
        "deep",
        "complex",
        "social commentary",
        "thought-provoking",
    },
    "relaxing": {"calm", "peaceful", "cozy", "slow", "beautiful", "atmospheric", "comfort"},
    "motivational": {
        "inspirational",
        "true story",
        "underdog",
        "perseverance",
        "based on a true story",
        "hero",
        "sports",
    },
    "family": {"family", "kids", "disney", "pixar", "children", "all ages"},
    "horror": {"scary", "horror", "creepy", "gore", "zombie", "supernatural", "ghost"},
}

# Title keywords (lowercase) that hint at mood
MOOD_TITLE_KEYWORDS = {
    "happy": {"joy", "happy", "sunshine", "smile", "magic", "celebration"},
    "sad": {"tear", "goodbye", "loss", "lonely", "death", "memorial"},
    "thrilling": {"kill", "dead", "dark", "hunt", "war", "mission", "escape", "danger"},
    "romantic": {"love", "wedding", "bride", "valentine", "heart", "kiss"},
    "funny": {"funny", "laugh", "dumb", "crazy", "wild", "party"},
    "thought-provoking": {"matrix", "inception", "mind", "future", "time", "existence"},
    "relaxing": {"peace", "garden", "dream", "gentle", "slow", "nature"},
    "motivational": {"champion", "victory", "rise", "dream", "legend", "hero"},
    "family": {"toy", "story", "family", "kid", "princess", "dragon", "adventure"},
    "horror": {"horror", "dead", "evil", "nightmare", "ghost", "demon", "blood", "haunt"},
}

MOOD_EXPLANATION_PHRASES = {
    "happy": "uplifting energy and feel-good moments",
    "sad": "emotional depth that resonates when you need a cathartic watch",
    "thrilling": "pulse-pounding suspense and high-stakes tension",
    "romantic": "heartfelt chemistry and romantic storytelling",
    "funny": "sharp humor and laugh-out-loud comedy",
    "thought-provoking": "ideas that linger long after the credits roll",
    "relaxing": "a gentle, easy-going atmosphere to unwind with",
    "motivational": "inspiring triumph-over-adversity storytelling",
    "family": "wholesome entertainment the whole household can enjoy",
    "horror": "chilling atmosphere and spine-tingling scares",
}


def generate_explanation(
    title: str,
    genres: str,
    year: int | None,
    mood_ids: list[str],
    mood_labels: list[str],
    confidence: float,
) -> str:
    """Build a natural 1–2 sentence explanation for why a movie fits the mood."""
    primary_mood = mood_ids[0]
    mood_phrase = MOOD_EXPLANATION_PHRASES.get(primary_mood, "the vibe you're after")
    genre_list = [g.strip() for g in genres.split("|") if g.strip()][:3]
    genre_text = ", ".join(genre_list) if genre_list else "its genre blend"

    year_bit = f" ({year})" if year else ""
    mood_text = " and ".join(mood_labels) if len(mood_labels) > 1 else mood_labels[0]

    if confidence >= 85:
        fit = "An excellent match"
    elif confidence >= 65:
        fit = "A strong match"
    else:
        fit = "A solid pick"

    return (
        f"{fit} for a {mood_text.lower()} mood — {title}{year_bit} blends {genre_text} "
        f"with {mood_phrase}."
    )
