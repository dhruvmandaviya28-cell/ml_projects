/**
 * CineMatch — Movie Recommendation System
 * Frontend application logic
 */

const API = "/api";
const RECENT_MOODS_KEY = "cinematch_recentMoods";
const MAX_RECENT = 5;

// ── State ──────────────────────────────────────────────────────────
let moods = [];
let selectedMoods = new Set();
let searchDebounce = null;
let suggestionFocusIdx = -1;
let currentSuggestions = [];

// ── DOM helpers ────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── Init ───────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);

async function init() {
  setupTabs();
  setupScrollTop();
  setupModal();
  setupSimilarSearch();
  await loadMoods();
  setupMoodSection();
  renderRecentMoods();
  loadStats();
  loadTrending();
  setupHeroCta();
}

// ── Tab navigation ─────────────────────────────────────────────────
function setupTabs() {
  $$(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
}

function switchTab(target) {
  $$(".nav-tab").forEach((t) => {
    const active = t.dataset.tab === target;
    t.classList.toggle("active", active);
    t.setAttribute("aria-selected", active ? "true" : "false");
  });
  $$(".panel").forEach((p) => {
    p.classList.toggle("active", p.id === `${target}-section`);
  });
}

// ── Hero CTA ───────────────────────────────────────────────────────
function setupHeroCta() {
  $("#hero-similar-btn")?.addEventListener("click", () => {
    switchTab("similar");
    setTimeout(() => $("#movie-search")?.focus(), 350);
  });
  $("#hero-mood-btn")?.addEventListener("click", () => switchTab("mood"));
}

// ── Stats ──────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const res = await fetch(`${API}/stats`);
    if (!res.ok) return;
    const data = await res.json();
    animateCount("stat-movies",  data.movies);
    animateCount("stat-ratings", data.ratings);
    animateCount("stat-users",   data.users);
  } catch {
    // non-critical, silently ignore
  }
}

function animateCount(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const duration = 1200;
  const start = performance.now();
  function tick(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(eased * target);
    el.textContent = value >= 1000
      ? (value >= 1_000_000 ? `${(value / 1_000_000).toFixed(1)}M` : `${(value / 1000).toFixed(0)}k`)
      : value;
    if (progress < 1) requestAnimationFrame(tick);
    else el.textContent = target >= 1_000_000
      ? `${(target / 1_000_000).toFixed(1)}M`
      : target >= 1000 ? `${(target / 1000).toFixed(0)}k` : target;
  }
  requestAnimationFrame(tick);
}

// ── Trending ───────────────────────────────────────────────────────
async function loadTrending() {
  const loading = $("#trending-loading");
  const error   = $("#trending-error");
  const grid    = $("#trending-grid");

  renderSkeletons(grid, 12);
  grid.classList.remove("hidden");

  try {
    const res = await fetch(`${API}/trending?count=12`);
    if (!res.ok) throw new Error("Failed to load trending.");
    const data = await res.json();

    loading.classList.add("hidden");
    grid.innerHTML = "";
    data.trending.forEach((movie, i) => {
      grid.appendChild(createMovieCard(movie, i, "trending"));
    });
  } catch (err) {
    loading.classList.add("hidden");
    grid.classList.add("hidden");
    error.textContent = err.message;
    error.classList.remove("hidden");
  }
}

// ── Similar movies ─────────────────────────────────────────────────
function setupSimilarSearch() {
  const form        = $("#similar-form");
  const input       = $("#movie-search");
  const suggestions = $("#search-suggestions");

  input.addEventListener("input", () => {
    clearTimeout(searchDebounce);
    const q = input.value.trim();
    if (q.length < 2) {
      hideSuggestions(suggestions, input);
      return;
    }
    searchDebounce = setTimeout(async () => {
      try {
        const res  = await fetch(`${API}/search?q=${encodeURIComponent(q)}&limit=8`);
        const data = await res.json();
        currentSuggestions = data.results;
        suggestionFocusIdx = -1;
        renderSuggestions(data.results, input, suggestions);
      } catch {
        hideSuggestions(suggestions, input);
      }
    }, 220);
  });

  // Keyboard navigation
  input.addEventListener("keydown", (e) => {
    const items = suggestions.querySelectorAll("li");
    if (!items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      suggestionFocusIdx = Math.min(suggestionFocusIdx + 1, items.length - 1);
      updateFocusedSuggestion(items, input);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      suggestionFocusIdx = Math.max(suggestionFocusIdx - 1, -1);
      updateFocusedSuggestion(items, input);
    } else if (e.key === "Escape") {
      hideSuggestions(suggestions, input);
    } else if (e.key === "Enter" && suggestionFocusIdx >= 0) {
      e.preventDefault();
      const title = currentSuggestions[suggestionFocusIdx];
      if (title) {
        input.value = title;
        hideSuggestions(suggestions, input);
        fetchSimilarRecommendations(title);
      }
    }
  });

  input.addEventListener("blur", () => {
    setTimeout(() => hideSuggestions(suggestions, input), 160);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = input.value.trim();
    if (!title) return;
    hideSuggestions(suggestions, input);
    await fetchSimilarRecommendations(title);
  });
}

function updateFocusedSuggestion(items, input) {
  items.forEach((li, i) => li.classList.toggle("focused", i === suggestionFocusIdx));
  if (suggestionFocusIdx >= 0 && currentSuggestions[suggestionFocusIdx]) {
    input.value = currentSuggestions[suggestionFocusIdx];
  }
}

function hideSuggestions(container, input) {
  container.classList.add("hidden");
  input.setAttribute("aria-expanded", "false");
  suggestionFocusIdx = -1;
}

function renderSuggestions(results, input, container) {
  container.innerHTML = "";
  if (!results.length) { hideSuggestions(container, input); return; }
  results.forEach((title, idx) => {
    const li = document.createElement("li");
    li.textContent = title;
    li.setAttribute("role", "option");
    li.addEventListener("mousedown", (e) => {
      e.preventDefault();
      input.value = title;
      hideSuggestions(container, input);
      fetchSimilarRecommendations(title);
    });
    li.addEventListener("mousemove", () => {
      container.querySelectorAll("li").forEach((el) => el.classList.remove("focused"));
      li.classList.add("focused");
      suggestionFocusIdx = idx;
    });
    container.appendChild(li);
  });
  container.classList.remove("hidden");
  input.setAttribute("aria-expanded", "true");
}

async function fetchSimilarRecommendations(title) {
  const loading = $("#similar-loading");
  const error   = $("#similar-error");
  const results = $("#similar-results");
  const grid    = $("#similar-grid");

  loading.classList.remove("hidden");
  error.classList.add("hidden");
  results.classList.add("hidden");

  renderSkeletons(grid, 10);
  results.classList.remove("hidden");

  try {
    const res  = await fetch(`${API}/recommend?title=${encodeURIComponent(title)}&count=12`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.found === false ? `Movie "${title}" not found in our database.` : "Request failed.");
    }

    $("#similar-query").textContent = `"${data.query}"`;
    const count = data.recommendations.length;
    $("#similar-count").textContent = `${count} result${count !== 1 ? "s" : ""}`;

    grid.innerHTML = "";
    data.recommendations.forEach((movie, i) => {
      grid.appendChild(createMovieCard(movie, i, "similar"));
    });

    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    results.classList.add("hidden");
    error.textContent = err.message || "Something went wrong. Please try again.";
    error.classList.remove("hidden");
  } finally {
    loading.classList.add("hidden");
  }
}

// ── Mood recommendations ───────────────────────────────────────────
async function loadMoods() {
  try {
    const res  = await fetch(`${API}/moods`);
    const data = await res.json();
    moods = data.moods || [];
    renderMoodCards();
  } catch {
    const el = $("#mood-error");
    el.textContent = "Could not load mood options.";
    el.classList.remove("hidden");
  }
}

function setupMoodSection() {
  $("#mood-submit-btn").addEventListener("click", () => submitMoodRecommendations(false));
  $("#surprise-btn").addEventListener("click",    () => submitMoodRecommendations(true));
}

function renderMoodCards() {
  const grid = $("#mood-grid");
  grid.innerHTML = "";
  moods.forEach((mood) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "mood-card";
    card.dataset.moodId = mood.id;
    card.setAttribute("aria-pressed", "false");
    card.innerHTML = `<span class="emoji">${mood.emoji}</span><span class="label">${mood.label}</span>`;
    card.addEventListener("click", () => toggleMood(mood.id, card));
    grid.appendChild(card);
  });
}

function toggleMood(moodId, card) {
  if (selectedMoods.has(moodId)) {
    selectedMoods.delete(moodId);
    card.classList.remove("selected");
    card.setAttribute("aria-pressed", "false");
  } else {
    selectedMoods.add(moodId);
    card.classList.add("selected");
    card.setAttribute("aria-pressed", "true");
  }
  $("#mood-submit-btn").disabled = selectedMoods.size === 0;
}

function selectMoodsFromRecent(moodIds) {
  selectedMoods = new Set(moodIds);
  $$(".mood-card").forEach((card) => {
    const active = selectedMoods.has(card.dataset.moodId);
    card.classList.toggle("selected", active);
    card.setAttribute("aria-pressed", active ? "true" : "false");
  });
  $("#mood-submit-btn").disabled = selectedMoods.size === 0;
}

async function submitMoodRecommendations(surprise) {
  const loading = $("#mood-loading");
  const error   = $("#mood-error");
  const results = $("#mood-results");
  const grid    = $("#mood-grid-results");

  loading.classList.remove("hidden");
  error.classList.add("hidden");
  results.classList.add("hidden");

  const moodList = surprise ? [] : [...selectedMoods];

  renderSkeletons(grid, 12);
  results.classList.remove("hidden");

  try {
    const res  = await fetch(`${API}/recommend/mood`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ moods: moodList, surprise }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error("Could not generate mood recommendations.");

    if (!surprise && moodList.length) {
      saveRecentMoods(moodList);
      renderRecentMoods();
    }

    const labels  = data.mood_labels || [];
    const titleEl = $("#mood-results-title");
    if (data.surprise) {
      titleEl.innerHTML = `Surprise picks for a <span>${labels[0] || "Random"}</span> mood`;
    } else if (labels.length > 1) {
      titleEl.innerHTML = `Curated for <span>${labels.join(" + ")}</span>`;
    } else {
      titleEl.innerHTML = `Perfect for a <span>${labels[0] || "your"}</span> mood`;
    }

    const count = data.recommendations.length;
    $("#mood-count").textContent = `${count} film${count !== 1 ? "s" : ""}`;

    grid.innerHTML = "";
    data.recommendations.forEach((movie, i) => {
      grid.appendChild(createMovieCard(movie, i, "mood"));
    });

    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    results.classList.add("hidden");
    error.textContent = err.message || "Something went wrong. Please try again.";
    error.classList.remove("hidden");
  } finally {
    loading.classList.add("hidden");
  }
}

// ── Movie card renderer ────────────────────────────────────────────
function createMovieCard(movie, index, mode) {
  const card = document.createElement("article");
  card.className = "movie-card";
  card.style.animationDelay = `${Math.min(index * 0.05, 0.6)}s`;

  // Rating
  const ratingHtml = movie.imdbRating
    ? `<span class="meta-chip rating">★ ${movie.imdbRating}</span>`
    : "";
  const yearHtml = movie.year
    ? `<span class="meta-chip">${movie.year}</span>`
    : "";

  // Badge
  let badge = "";
  if (mode === "mood" && movie.confidence != null) {
    badge = `<span class="confidence-badge">✓ ${movie.confidence}%</span>`;
  } else if ((mode === "similar" || mode === "trending") && movie.similarity != null) {
    badge = `<span class="similarity-badge">~ ${movie.similarity}%</span>`;
  }

  // Genre pills
  const genreList  = (movie.genres || "").split(", ").filter(Boolean);
  const genrePills = genreList
    .slice(0, 4)
    .map((g) => {
      const cls = genreClass(g);
      return `<span class="genre-pill ${cls}">${g}</span>`;
    })
    .join("");

  // Explanation (mood only)
  const explanationHtml =
    mode === "mood" && movie.explanation
      ? `<p class="explanation">${escapeHtml(movie.explanation)}</p>`
      : "";

  // IMDb link
  const imdbHref = movie.imdbId
    ? `https://www.imdb.com/title/${movie.imdbId}/`
    : null;

  // Overlay actions
  const overlayActions = `
    <div class="overlay-actions">
      <button class="overlay-btn overlay-btn-primary" data-movie-id="${movie.movieId}" aria-label="More info about ${escapeHtml(movie.title)}">
        ℹ Details
      </button>
      ${imdbHref
        ? `<a class="overlay-btn overlay-btn-secondary" href="${imdbHref}" target="_blank" rel="noopener noreferrer" aria-label="View on IMDb">
            ↗ IMDb
           </a>`
        : ""}
    </div>
  `;

  card.innerHTML = `
    <div class="poster-wrap">
      <img
        src="${escapeHtml(movie.poster)}"
        alt="Poster for ${escapeHtml(movie.title)}"
        loading="lazy"
        onerror="this.src='https://placehold.co/300x450/10101a/8b5cf6?text=No+Poster&font=inter'"
      />
      ${badge}
      <div class="poster-overlay">${overlayActions}</div>
    </div>
    <div class="card-body">
      <h4>${escapeHtml(movie.title)}</h4>
      <div class="movie-meta">${yearHtml}${ratingHtml}</div>
      <div class="genres-row">${genrePills}</div>
      ${explanationHtml}
    </div>
  `;

  // Details button handler
  card.querySelector("[data-movie-id]")?.addEventListener("click", (e) => {
    e.stopPropagation();
    openMovieModal(movie);
  });

  return card;
}

// Genre → CSS class
function genreClass(genre) {
  const safe = genre.replace(/[\s-]+/g, "-").replace(/[^a-zA-Z0-9-]/g, "");
  const knownGenres = [
    "Action","Adventure","Animation","Children","Comedy","Crime",
    "Documentary","Drama","Fantasy","Film-Noir","Horror","Musical",
    "Mystery","Romance","Sci-Fi","Sport","Thriller","War","Western",
  ];
  return knownGenres.includes(genre) ? `genre-${safe}` : "genre-default";
}

// Skeleton loaders
function renderSkeletons(container, count) {
  container.innerHTML = Array.from({ length: count }, () => `
    <div class="skeleton-card">
      <div class="skeleton-poster"></div>
      <div class="skeleton-body">
        <div class="skeleton-line medium"></div>
        <div class="skeleton-line short"></div>
        <div class="skeleton-line short" style="width:40%"></div>
      </div>
    </div>
  `).join("");
}

// ── Movie detail modal ─────────────────────────────────────────────
function setupModal() {
  const overlay = $("#modal-overlay");
  const closeBtn = $("#modal-close");

  closeBtn?.addEventListener("click", closeModal);
  overlay?.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay?.classList.contains("hidden")) closeModal();
  });
}

async function openMovieModal(movie) {
  const overlay = $("#modal-overlay");
  const body    = $("#modal-body");
  overlay.classList.remove("hidden");
  document.body.style.overflow = "hidden";

  // Show loading
  body.innerHTML = `<div class="loading-state" style="padding:3rem 1rem;"><div class="spinner"></div><p>Loading details…</p></div>`;

  // Fetch tags / extra info
  let tags = [];
  let ratingCount = 0;
  try {
    const res  = await fetch(`${API}/movie/${movie.movieId}`);
    if (res.ok) {
      const detail = await res.json();
      tags = detail.tags || [];
      ratingCount = detail.ratingCount || 0;
    }
  } catch { /* non-critical */ }

  const imdbHref = movie.imdbId ? `https://www.imdb.com/title/${movie.imdbId}/` : null;
  const genreList = (movie.genres || "").split(", ").filter(Boolean);
  const genrePills = genreList
    .map((g) => `<span class="genre-pill ${genreClass(g)}">${g}</span>`)
    .join("");

  const tagsHtml = tags.length
    ? `<div class="modal-tags">
         <p class="modal-tags-label">User Tags</p>
         <div class="modal-tags-list">${tags.slice(0, 20).map((t) => `<span class="tag-chip">${escapeHtml(t)}</span>`).join("")}</div>
       </div>`
    : "";

  body.innerHTML = `
    <div class="modal-poster-row">
      <div class="modal-poster">
        <img src="${escapeHtml(movie.poster)}"
             alt="${escapeHtml(movie.title)}"
             onerror="this.src='https://placehold.co/300x450/10101a/8b5cf6?text=No+Poster&font=inter'" />
      </div>
      <div class="modal-info">
        <h2 class="modal-title" id="modal-title">${escapeHtml(movie.title)}</h2>
        <div class="modal-meta">
          ${movie.year ? `<span class="meta-chip">${movie.year}</span>` : ""}
          ${movie.imdbRating ? `<span class="meta-chip rating">★ ${movie.imdbRating}</span>` : ""}
          ${ratingCount ? `<span class="meta-chip">${ratingCount.toLocaleString()} ratings</span>` : ""}
        </div>
        <div class="modal-genres">${genrePills}</div>
        ${tagsHtml}
      </div>
    </div>
    <div class="modal-actions">
      ${imdbHref
        ? `<a class="btn btn-primary" href="${imdbHref}" target="_blank" rel="noopener noreferrer">↗ View on IMDb</a>`
        : ""}
      <button class="btn btn-secondary" id="modal-similar-btn">🔍 Find Similar</button>
    </div>
  `;

  body.querySelector("#modal-similar-btn")?.addEventListener("click", () => {
    closeModal();
    switchTab("similar");
    const input = $("#movie-search");
    if (input) {
      input.value = movie.title;
      setTimeout(() => fetchSimilarRecommendations(movie.title), 350);
    }
  });
}

function closeModal() {
  const overlay = $("#modal-overlay");
  overlay.classList.add("hidden");
  document.body.style.overflow = "";
}

// ── Scroll-to-top ──────────────────────────────────────────────────
function setupScrollTop() {
  const btn = $("#scroll-top-btn");
  if (!btn) return;

  window.addEventListener("scroll", () => {
    btn.classList.toggle("hidden", window.scrollY < 400);
    btn.classList.toggle("visible", window.scrollY >= 400);
  }, { passive: true });

  btn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

// ── Recent moods ───────────────────────────────────────────────────
function saveRecentMoods(moodIds) {
  let recent = getRecentMoods();
  const key = moodIds.slice().sort().join("+");
  recent = recent.filter((r) => r.key !== key);
  recent.unshift({ key, ids: moodIds, ts: Date.now() });
  recent = recent.slice(0, MAX_RECENT);
  localStorage.setItem(RECENT_MOODS_KEY, JSON.stringify(recent));
}

function getRecentMoods() {
  try { return JSON.parse(localStorage.getItem(RECENT_MOODS_KEY) || "[]"); }
  catch { return []; }
}

function renderRecentMoods() {
  const container = $("#recent-moods");
  const list      = $("#recent-moods-list");
  const recent    = getRecentMoods();

  if (!recent.length) { container.classList.add("hidden"); return; }

  list.innerHTML = "";
  recent.forEach(({ ids }) => {
    const labels = ids
      .map((id) => { const m = moods.find((x) => x.id === id); return m ? `${m.emoji} ${m.label}` : id; })
      .join(" + ");
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "recent-chip";
    chip.textContent = labels;
    chip.addEventListener("click", () => {
      selectMoodsFromRecent(ids);
      submitMoodRecommendations(false);
    });
    list.appendChild(chip);
  });
  container.classList.remove("hidden");
}

// ── Utilities ──────────────────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
