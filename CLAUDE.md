# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Danki Independent is a spaced repetition flashcard application for language learners that delivers Anki-style spaced repetition without the setup burden. Built with Python and PySide6, it focuses on clean three-button reviews, built-in CEFR decks (A1-B2), and a minimal home → review flow.

**Current Status**: Phase 1 Mac MVP in active development. M0 (foundation) ✅ complete, AI card generation ✅ complete, M1 (core engine) ✅ complete, German TTS system ✅ complete. Working on M2 polish features and GUI redesign.

## Development Commands

### Running the Application
```bash
python main.py
```

### Testing Database Operations
```bash
python test_db.py
```

### Testing JSONL Deck Loading
```bash
python cli_test.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Testing German TTS System
```bash
# Verify edge-tts is installed and working
python -c "from danki.utils.tts import german_tts; german_tts.speak('Hallo Welt')"
```

### Testing Scheduling Algorithm
```bash
# Run SM-2 scheduler unit tests
python test_scheduler.py

# Test "Again" button behavior
python test_again_behavior.py

# Debug current card states
python debug_due_cards.py
```

### CLI Engine Testing (Future)
```bash
python -m danki.engine.cli demo-session
```

## Architecture

### Package Structure
```
danki/
├── __init__.py
├── engine/          # Pure Python scheduling engine
│   ├── db.py        # SQLite database layer
│   └── scheduler.py # SM-2 scheduling algorithm
├── ui/              # PySide6 GUI components
│   ├── main.py      # Main application window
│   ├── screens/     # Individual screen components
│   └── dialogs/     # Preferences and settings dialogs
├── utils/           # Utility modules
│   ├── config.py    # Configuration management
│   ├── study_time.py # Study date/time utilities
│   └── tts.py       # German TTS with edge-tts
└── data/            # Built-in decks and resources
    └── decks/       # JSONL deck files
```

### Core Components

- **`danki/ui/main.py`**: Main application window with screen navigation
- **`danki/ui/screens/home.py`**: Home screen with deck management and stats
- **`danki/ui/screens/review.py`**: Review screen with 3-button interface and TTS
- **`danki/ui/screens/add_cards.py`**: AI-powered card creation with Gemini
- **`danki/ui/dialogs/preferences.py`**: Settings dialog for API keys and preferences
- **`danki/engine/db.py`**: SQLite database layer with full CRUD operations
- **`danki/engine/scheduler.py`**: SM-2 spaced repetition algorithm
- **`danki/utils/tts.py`**: German TTS system with edge-tts and audio caching
- **`danki/utils/config.py`**: Persistent configuration management
- **`danki/data/decks/`**: Built-in JSONL decks (A1-B2 CEFR levels)

### Database Schema

SQLite with WAL mode for performance and safety:

**decks**: id, name, is_builtin, prefs (JSON with new_per_day, rev_per_day, steps_min, bidirectional_cards)  
**notes**: id, deck_id, front, back, meta (JSON with conjugation, word_type, etc.), created_at  
**cards**: id, note_id, template, state, due_ts, interval_days, ease, lapses, step_index, last_review_ts  
**review_log**: id, card_id, ts, rating, answer_ms, prev_state, prev_interval, next_interval  
**daily_stats**: id, deck_id, study_date, new_studied, rev_studied, created_at

### Scheduling Algorithm (SM-2 Simplified)

**Rating System**: Missed=0 (Again), Almost=1 (Hard), Got It=2 (Good)  
**Learning Steps**: [1 minute, 10 minutes] (Anki default for immediate re-learning)  
**Graduation**: Good at last learning step → review state, 1 day interval  
**SM-2 Updates**: Ease floor 1.3, Hard=-0.15, Good=+0.0, Missed=-0.8  
**Daily Limits**: Per-deck new/review card limits with progress tracking  
**Bidirectional Cards**: Optional front→back and back→front cards per note

### Key Features (Phase 1 Scope)

✅ **M0 Foundation**: Package structure, SQLite schema, skeleton UI  
✅ **AI Card Generation**: Gemini API integration, persistent config, deck management  
✅ **M1 Core Engine**: SM-2 scheduler, review session with 3-button interface  
✅ **German TTS System**: Edge-TTS integration, audio caching, speaker toggle  
🔄 **M2 Polish**: Stats dashboard, backup/restore, GUI redesign preparation  
⏳ **M3 Content**: Full CEFR decks A1-B2, leech detection, bury siblings

### Recently Completed (Sessions 1-2)
- ✅ Real Gemini API integration with German language focus
- ✅ Bulk word processing with rich metadata (conjugations, articles, examples)
- ✅ Persistent API key storage in `~/.danki/config.json`
- ✅ Complete deck management (create, delete, list with card counts)
- ✅ Cross-screen synchronization between Home/Add Cards tabs
- ✅ **Complete Review Session**: 3-button interface, German card display, keyboard shortcuts
- ✅ **Full SM-2 Scheduling**: Card state transitions, ease adjustments, lapse handling
- ✅ **Engine Fixes**: Home stats display, card availability, proper scheduling logic
- ✅ **UI Polish**: API key persistence, compact layouts, better contrast

### Session 3 Completed (TTS & Polish)
- ✅ **German TTS System**: edge-tts integration with neural voice (de-DE-KatjaNeural)
- ✅ **Audio Caching**: Smart MD5-based caching to avoid regeneration
- ✅ **Speaker Toggle**: 🔊/🔇 button with auto-play on card show/flip
- ✅ **Daily Limits**: Per-deck new/review limits with progress tracking
- ✅ **Bidirectional Cards**: Optional front→back and back→front per note
- ✅ **Learning Steps Fix**: [1, 10] minutes for immediate re-learning
- ✅ **Article Bug Fix**: Prevent duplicate articles (der der Hund → der Hund)
- ✅ **Preferences Dialog**: Clean API key and settings management
- ✅ **Test Suite**: Comprehensive scheduler tests and debug utilities

### Next Priority (M2 Continued)
- 🎯 **GUI Redesign**: Modern framework (Electron) with designer collaboration
- 🎯 **Stats Dashboard**: Learning analytics, completion streaks, deck insights
- 🎯 **Built-in CEFR Decks**: A1-B2 German vocabulary with import functionality

### Data Formats

**JSONL Deck Format**:
```json
{"front":"der Tisch","back":"the table","meta":{"article":"der","tags":["A1"]}}
```

**Built-in Decks**: A1, A2, B1, B2 German vocabulary with "Add to My Library" functionality

### UI Principles

- One action per screen
- No jargon, sensible defaults  
- Keyboard-first ergonomics (Space=flip, 1/2/3=rating)
- Clean navigation: Home ↔ Review screens

### Testing Strategy

**Unit Tests**: Graduation logic, lapse behavior, daily caps, bury siblings  
**Smoke Tests**: Add card → due count increases, review ratings work correctly  
**Database Tests**: CRUD operations, JSONL loading, backup/restore integrity

### AI-Enhanced Card Generation

**Integration with Gemini API** (inspired by existing `danki_app.py`):
- **Auto-Card Creation**: Input German words/phrases → AI generates comprehensive flashcards
- **Rich Metadata**: Articles (der/die/das), plural forms, verb conjugations, example sentences  
- **Multilingual Support**: Translation target languages (English, Spanish, Hindi, French)
- **Context-Aware**: Optional context input for better translations
- **Audio Generation**: Text-to-speech integration using edge-tts (German voice)

**German Language Learning Focus**:
```json
{
  "base_d": "laufen",           // Original German word (infinitive for verbs)
  "base_e": "to run",           // Translation
  "artikel_d": "",              // Article (der/die/das) - empty for verbs
  "plural_d": "",               // Plural form - empty for verbs
  "word_type": "verb",          // Word type: "noun", "verb", "adjective", etc.
  "conjugation": {              // Full conjugation (if verb)
    "ich": "laufe",
    "du": "läufst", 
    "er_sie_es": "läuft",
    "wir": "laufen",
    "ihr": "lauft",
    "sie_Sie": "laufen"
  },
  "praesens": "läuft",          // 3rd person singular (for backward compatibility)
  "praeteritum": "lief",        // Past tense (3rd person singular)
  "perfekt": "ist gelaufen",    // Perfect tense
  "full_d": "läuft, lief, ist gelaufen",  // Combined key conjugations
  "s1": "Ich laufe jeden Morgen...",      // Example sentence 1
  "s1e": "I run every morning...",        // Translation
  "s2": "Er läuft zur Arbeit...",         // Example sentence 2 (optional)
  "s3": "Der Hund läuft...",              // Example sentence 3 (optional)
  "meta": {"tags": ["A1"], "context": "..."}  // Additional metadata
}
```

**Card Display Requirements** (German Learning Cards):
- **Front Side**: Show German word with article (if noun) or infinitive (if verb)
- **Back Side**: 
  - Translation in target language
  - **For Verbs**: Full conjugation table (ich/du/er/wir/ihr/sie) + key tenses
  - **For Nouns**: Article (color-coded), plural form
  - Example sentences with translations
  - Audio playback capability
- **Audio Integration**: TTS for German pronunciation
- **Smart Metadata Display**: 
  - Articles color-coded (der=blue, die=red, das=green)
  - Conjugation table formatted clearly
  - Word type indicators (verb/noun/adjective)

### Non-Goals (Phase 1)

FSRS calibration, advanced analytics, per-deck custom steps, Easy button, cloud sync, mobile clients, Anki interoperability

### Future AI Integration Plan

**M2+ Features** (post-core implementation):
- Gemini API integration for card auto-generation  
- Text-to-speech with edge-tts
- Context-aware translation requests
- Multi-language support beyond German
- Phrase/sentence processing capabilities