# 🎬 CineMatch — Movie Recommendation System

> AI-powered movie discovery powered by MovieLens data, Flask, and vanilla JavaScript.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-green?logo=flask)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3+-orange?logo=scikitlearn)

## Features

| Feature | Description |
|---|---|
| 🎥 **Content-Based Recommendations** | Enter any movie title → TF-IDF + KNN finds movies with matching genre profiles |
| 🎭 **Mood-Based Recommendations** | Select one or more moods (Happy, Thrilling, Horror, …) → curated watchlist |
| 🎲 **Surprise Me** | Random mood-based pick for when you can't decide |
| 🔥 **Trending & Top Rated** | Homepage shows top-rated popular films from the dataset |
| 🔍 **Autocomplete Search** | Real-time title suggestions with keyboard navigation |
| 🪟 **Movie Detail Modal** | Click any card to see tags, rating counts, and an IMDb link |
| 🌐 **Poster Fetching** | Posters loaded from Cinemeta (TMDB optional), cached locally |

## Project Structure

```
movie-recommendation-app/
├── backend/
│   ├── app.py                  # Flask API (all endpoints)
│   ├── config.py               # Paths & constants
│   └── services/
│       ├── content_recommender.py   # TF-IDF + KNN engine
│       ├── data_loader.py           # MovieLens data store
│       ├── mood_mapping.py          # Mood→genre weights & explanations
│       ├── mood_recommender.py      # Mood scoring engine
│       └── movie_enricher.py        # Poster fetching & enrichment
├── data/
│   └── ml-latest-small/        # MovieLens dataset (9,000+ movies)
├── frontend/
│   ├── index.html
│   ├── favicon.ico
│   ├── css/styles.css
│   └── js/app.js
├── requirements.txt
└── run.py                      # Entry point
```

## Quick Start

### 1. Prerequisites
- Python 3.10+
- pip

### 2. Clone & install dependencies
```bash
git clone <repo-url>
cd movie-recommendation-app
pip install -r requirements.txt
```

### 3. Run the server
```bash
python run.py
```

The app will be available at **http://localhost:5000**

### 4. (Optional) TMDB poster integration
Set your TMDB API key as an environment variable for richer poster metadata:
```bash
set TMDB_API_KEY=your_key_here   # Windows
export TMDB_API_KEY=your_key_here # Linux/macOS
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Dataset statistics (movies, ratings, users) |
| `GET` | `/api/moods` | List all supported moods |
| `GET` | `/api/trending?count=12` | Top-rated popular movies |
| `GET` | `/api/search?q=<query>` | Autocomplete search |
| `GET` | `/api/recommend?title=<title>` | Content-based recommendations |
| `GET` | `/api/movie/<id>` | Individual movie details + tags |
| `POST` | `/api/recommend/mood` | Mood-based recommendations |

### POST /api/recommend/mood
```json
{
  "moods": ["happy", "funny"],
  "surprise": false,
  "count": 12
}
```

## Dataset

Uses the [MovieLens Small Dataset](https://grouplens.org/datasets/movielens/latest/) (ml-latest-small):
- **9,742** movies
- **100,836** ratings
- **3,683** user tags
- **610** users

## Tech Stack

- **Backend**: Python · Flask · scikit-learn · pandas · requests
- **Recommendation**: TF-IDF vectorization · Nearest Neighbors (cosine similarity)
- **Frontend**: Vanilla HTML/CSS/JavaScript (no framework)
- **Data**: MovieLens ml-latest-small · Cinemeta for posters

## License

MIT
