# Danki – Phase 1 PRD & Tech Spec (Hand‑off Draft)
Version: v1.0 (Hand‑off)
Prepared for: Implementation in Claude Code (and other AI coding assistants)
Authoring date: 10 Aug 2025

## 1) Product vision (one paragraph)
Danki is a simple, friendly flashcard app for language learners that delivers Anki‑style spaced repetition without the setup burden. The Mac MVP focuses on clean, three‑button reviews, built‑in CEFR decks (A1–B2), and a minimal home → review flow. Later releases will add sync and mobile apps reusing the same scheduling engine and schema.
## 2) Scope for Phase 1 (Mac MVP)
Platforms: macOS desktop only (prototype in PyQt/PySide6).
Built‑in CEFR decks (A1–B2) bundled as JSONL and installable into the user’s library.
User‑created decks and cards (single add flow; optional context).
Simple review with Missed / Almost / Got it.
Basic stats popover: counts + pie of New/Learning/Review for today.
Local SQLite storage; manual backup/restore.
No cloud sync, no accounts, no Anki interoperability.
### Non‑goals (Phase 1)
FSRS calibration, advanced analytics, per‑deck custom steps, Easy button, cloud sync, mobile clients.
## 3) Personas & UX principles
Beginner learner: wants to add a word and start reviewing in under a minute.
Returning learner: expects daily goals, quick sessions, clear progress.
Principles: one action per screen, no jargon, sensible defaults, keyboard‑first ergonomics.
## 4) Feature list & acceptance criteria (AC)
### 4.1 Library & built‑in decks
F1: Show built‑in CEFR decks (A1, A2, B1, B2) with an Add to My Library button.
AC: After clicking, cards appear as New in user’s default deck; duplicates are avoided.
F2: Create/rename/delete user decks.
AC: Deck list updates immediately; counts recalc.
### 4.2 Add cards
F3: Add note (front, back, optional context). Reverse card off by default.
AC: Empty fields blocked; duplicate prompt warning; success clears input.
### 4.3 Review session
F4: Start Review → shows due queue (mix of New/Learning/Review) with 3 buttons.
AC: Ratings update state; timer recorded; next card loads instantaneously (<100 ms target from local DB).
F5: TTS on reveal with local cache.
AC: First play may download/produce audio; subsequent plays read from cache.
F6: Keyboard shortcuts: 1=Missed, 2=Almost, 3=Got it, Space=flip.
### 4.4 Stats (popover)
F7: Today’s counts + pie chart (New/Learning/Review); streak counter.
AC: Values reflect DB queries; updates after session.
### 4.5 Utilities
F8: Backup & restore.
AC: Export creates a portable file; restore on a fresh install reproduces identical counts and cards.
## 5) Interaction flows (Simple Mode)
### 5.1 First‑run
Launch → Welcome screen with two actions: Add A1 Deck and Start Empty.
If Add A1 chosen → “Added!” → Home screen shows Today’s Goal and Start Review.
### 5.2 Add single card
Type front/back (+ optional context) → Add to deck.
Snackbar “Added” → counter increments.
### 5.3 Review
Card front → Space to reveal → TTS plays.
Choose Missed / Almost / Got it (or 1/2/3).
Queue continues until Today’s Goal completed → completion screen.
## 6) Data model (SQLite)
PRAGMA journal_mode=WAL;

CREATE TABLE decks (
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  is_builtin INTEGER NOT NULL DEFAULT 0,
  prefs JSON NOT NULL -- {"new_per_day":10,"rev_per_day":100,"steps_min":[10,1440]}
);

CREATE TABLE notes (
  id TEXT PRIMARY KEY,
  deck_id TEXT NOT NULL,
  front TEXT NOT NULL,
  back  TEXT NOT NULL,
  meta  JSON,                -- {"context":"…","article":"der","case":"[DAT]","tags":[…]}
  created_at INTEGER NOT NULL,
  FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
);

CREATE TABLE cards (
  id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL,
  template TEXT NOT NULL,    -- "front->back" (default)
  state TEXT NOT NULL,       -- "new"|"learning"|"review"|"suspended"
  due_ts INTEGER NOT NULL,
  interval_days REAL NOT NULL DEFAULT 0,
  ease REAL NOT NULL DEFAULT 2.5,
  lapses INTEGER NOT NULL DEFAULT 0,
  step_index INTEGER NOT NULL DEFAULT 0,
  last_review_ts INTEGER,
  UNIQUE(note_id, template),
  FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE TABLE review_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id TEXT NOT NULL,
  ts INTEGER NOT NULL,
  rating INTEGER NOT NULL,   -- 0 Again, 1 Hard, 2 Good
  answer_ms INTEGER NOT NULL,
  prev_state TEXT,
  prev_interval REAL,
  next_interval REAL,
  FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE
);

CREATE INDEX idx_cards_due ON cards(state, due_ts);
## 7) Scheduling logic (Phase 1)
Buttons: Missed=0 (Again), Almost=1 (Hard), Got it=2 (Good). No Easy in Simple Mode.
Learning steps: [10 min, 1 day] (stored in deck prefs).
Graduation: Good at last step → state=review, interval=1 day; first review special‑case to 6 days.
SM‑2 update (simplified):
Ease floor 1.3.
Hard: ease −0.15; Good: ease +0.0; Missed: ease −0.8 and move to step 0 due in 10 min.
Next interval = interval * ease (with 1→6 day special‑case).
Bury siblings: skip other cards of the same note for the day.
Leech (Phase 2): lapses ≥ 6 → suspended with prompt.
## 8) Engine API (Python for MVP)
class Rating(IntEnum):
    MISSED=0; ALMOST=1; GOT_IT=2

class Scheduler:
    def add_note(self, deck_id: str, front: str, back: str, meta: dict|None=None) -> str: ...
    def build_session(self, deck_ids: list[str], now_ts: int|None=None,
                      max_new: int|None=None, max_rev: int|None=None) -> list[dict]: ...
    def review(self, card_id: str, rating: Rating, answer_ms: int, now_ts: int|None=None) -> None: ...
    def suspend(self, card_id: str) -> None: ...
## 9) Bundled deck format (JSONL)
Each line is a note:
{"front":"der Tisch","back":"the table","meta":{"article":"der","tags":["A1"]}}
App provides Add to My Library which clones these into user decks.
## 10) macOS UI (PyQt/PySide6) – components
Home: input fields, Add button, Today’s Goal ring, Start Review.
Review: card view (front/back), 3 buttons + hotkeys, timer, TTS speaker, overflow menu (Suspend, Edit).
Stats popover: pie chart + counts; accessible via ⓘ icon.
Theme: theme.qss with light/dark, 1 accent colour; 8‑pt spacing grid.
## 11) TTS & caching
Use platform TTS or edge-tts (local cache by hash of text+voice). Cache path configurable.
## 12) Backup & restore
Export: JSONL (notes) + JSON (decks) + CSV/JSONL (review_log) or a zipped SQLite snapshot.
Restore: merges by stable IDs; avoids duplicates.
## 13) Testing & QA
Unit tests for: graduation, lapse behaviour, daily caps, bury siblings.
Smoke tests:
Add word → due count increases.
Missed → reappears in ≤10 min.
Got it twice on learning → due tomorrow.
Backup → wipe → restore → identical counts.
## 14) Milestones & deliverables
M0: Repo + migrations + skeleton UI (clickable, no logic).
M1: Engine SM‑2 + add/review flows; seeded A1 sample deck.
M2: TTS cache + stats popover + backup/restore.
M3: Content pass (A1–B2 min 100 cards each) + leech + bury siblings.
## 15) Risks & mitigations
DB corruption → WAL, safe shutdown, periodic auto‑backup.
Performance → indexes on (state, due_ts), keep queries small, prefetch next card.
Licensing of deck content → use original or permissive sources; keep attribution.
## 16) Future (post‑Phase 1) – for awareness
FSRS scheduler (toggle per deck) with answer time.
Supabase auth + delta sync.
Flutter clients (iOS/Android) sharing engine (Rust) + SQLite schema.
## 17) Handoff notes for Claude Code
Follow the API signatures in §8; implement engine in danki/engine/.
Keep Qt types out of engine; UI calls pure Python methods.
Provide docstrings and small docstring examples for each method.
Add CLI harness for headless tests: python -m danki.engine.cli demo-session.

Ready for implementation.

