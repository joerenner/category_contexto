# Product Layer Design — Category Contexto

## Overview

Mobile app (iOS + Android) for Category Contexto, a Contexto-style word guessing game with proper noun categories. React Native (Expo) frontend + FastAPI backend.

## Architecture

```
┌─────────────────────────────────────┐
│  React Native (Expo) Mobile App     │
│  - Game screen (guess + rank)       │
│  - Autocomplete dropdown            │
│  - Category picker                  │
│  - Results/share screen             │
│  - Streak tracking (local storage)  │
└──────────────┬──────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────┐
│  FastAPI Backend                    │
│  - GET /categories                  │
│  - GET /daily/{category}            │
│  - POST /guess                      │
│  - GET /entities/{category}/search  │
│  - POST /daily/{category}/hint      │
│  - GET /stats/{category}            │
├─────────────────────────────────────┤
│  SQLite (rankings, read-only)       │
│  Postgres (daily puzzles, streaks)  │
└─────────────────────────────────────┘
```

## API Design

### GET /categories
```json
[{"id": "politics", "name": "US Politics", "entity_count": 500, "icon": "🏛️"}]
```

### GET /daily/{category}
Today's puzzle info (not the answer). Falls back to deterministic random if no curated puzzle.
```json
{"category": "politics", "date": "2026-03-08", "entity_count": 499}
```

### POST /guess
```json
// Request
{"category": "politics", "date": "2026-03-08", "guess": "Barack Obama", "device_id": "uuid"}

// Normal response
{"rank": 2, "total": 499, "color": "green", "guess_number": 3, "solved": false}

// Winning response
{
  "rank": 0, "total": 499, "color": "gold", "guess_number": 8, "solved": true,
  "answer": "Joe Biden",
  "share_text": "Category Contexto: Politics 🏛️\n2026-03-08\n🟢🟡🔴🔴🟡🟢🟢🏆\nSolved in 8 guesses!"
}
```

Color thresholds: green ≤ 50, yellow ≤ 200, red > 200.

### GET /entities/{category}/search?q=bar
Autocomplete. Top 10 by prefix + fuzzy match.
```json
[{"name": "Barack Obama"}, {"name": "Barbara Lee"}, {"name": "Barbara Mikulski"}]
```

### POST /daily/{category}/hint
Returns one entity closer than all current guesses.
```json
{"hint": "Al Gore", "rank": 7}
```

### GET /stats/{category}?device_id=uuid
```json
{"current_streak": 5, "max_streak": 12, "games_played": 30, "avg_guesses": 14.2}
```

## Mobile App Screens

### 1. Home / Category Picker
- List of categories with name, icon, solved status
- Tap to enter game

### 2. Game Screen
- Text input with autocomplete dropdown (debounced 200ms, queries search endpoint)
- Tap suggestion to submit guess
- Scrollable guess list sorted by rank (best at top), color-coded
- Hint button (top right)
- On solve: confetti, answer revealed, transition to results

### 3. Results Screen
- Answer, guess count, rank history
- Share button (copies share text / native share sheet)
- "View Stats" / "Play Another Category" buttons

### 4. Stats Screen (modal from Home)
- Current streak, max streak, games played, average guesses
- Calendar grid of recent days

## Data & Storage

### Server-side

**SQLite (read-only):** Existing `rankings` and `entities` tables. One file per refresh.

**Postgres (mutable):**
- `daily_puzzles (category, date, secret_entity_id)` — curated or auto-generated. Cron pre-fills 30 days, admin can override.
- `game_sessions (device_id, category, date, guesses_json, solved, guess_count, created_at)` — per-device guess tracking.

### Client-side (AsyncStorage)
- `device_id`: UUID on first launch
- `streaks`: per-category current/max streak
- `history`: per-category daily results

## Tech Stack

- **Mobile:** React Native + Expo + TypeScript
- **Backend:** FastAPI (Python)
- **Rankings DB:** SQLite (existing)
- **Mutable DB:** Postgres
- **Hosting:** Railway or Fly.io (~$5/mo)
- **Builds:** Expo EAS
- **Ads:** AdMob via expo-ads-admob
- **App Stores:** iOS ($99/yr) + Google Play ($25 one-time)

## Deployment

- FastAPI on Railway/Fly.io, SQLite baked into container image
- Postgres managed by hosting provider
- Expo EAS for mobile builds and app store submissions
- Monthly cron runs ranking pipeline, rebuilds server image
- Daily cron pre-fills 30 days of puzzles

## Monetization

- AdMob: banner ad on game screen (bottom), interstitial between solve and results
- No paywall for MVP
- Optional "remove ads" IAP later
