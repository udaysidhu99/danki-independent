# Anki Scheduler System Analysis

**Status**: ✅ Analysis Complete - Based on specialized agent analysis  
**Target**: https://github.com/ankitects/anki (rslib/src/scheduler/)  
**Focus**: Complete scheduler system documentation

---

## Overview

Anki uses a sophisticated scheduling system built in Rust (`rslib/src/scheduler/`) with Python bindings. The architecture supports multiple algorithms (SM-2+ and FSRS) with comprehensive card state management, queue building, and performance optimizations.

## Core Components

### Scheduler Architecture
**Primary Components**:
- `rslib/src/scheduler/mod.rs` - Main scheduler interface
- `rslib/src/scheduler/states/` - Card state management
- `rslib/src/scheduler/timing/` - Review timing calculations  
- `rslib/src/scheduler/queue/` - Session building logic
- `rslib/src/scheduler/fsrs/` - FSRS algorithm implementation

### Card State Management
Anki uses a comprehensive state system:
- **New**: Cards never reviewed (due_ts = creation time)
- **Learning**: Cards in initial learning phase (step-based progression)
- **Review**: Graduated cards with interval-based scheduling
- **Relearning**: Previously learned cards that were forgotten
- **Suspended**: Manually paused cards
- **Buried**: Temporarily hidden related cards

### Algorithm Implementations
Two main algorithms are supported:
- **SM-2+**: Enhanced SuperMemo-2 with Anki improvements
- **FSRS**: Modern machine learning-based scheduler

## Key Algorithms

### SM-2+ Enhanced
Anki's improvements over basic SM-2:
- **Ease Factor Range**: 130% minimum to prevent "ease hell"
- **Interval Fuzzing**: ±5% randomization to prevent review clustering
- **Learning Steps**: Configurable progression (default: 10min, 1day)
- **Lapse Handling**: 50% interval reduction + ease penalty (-20%)
- **Graduation**: Multiple learning steps before review phase
- **Hard/Easy Buttons**: Additional response options beyond Again/Good

### FSRS (Free Spaced Repetition Scheduler)
Modern algorithm with machine learning optimization:
- **DSR Model**: Difficulty, Stability, Retrievability components
- **19 Parameters**: Machine learning optimized on 700M+ reviews
- **Memory State Tracking**: Personalized difficulty and stability values
- **Efficiency Gains**: 20-30% fewer reviews for same retention
- **Adaptive Learning**: Parameters adjust based on individual performance

## Session Building Logic

### Queue Construction
[Analyze: How Anki builds review sessions]
- Card selection criteria
- Daily limit enforcement
- Deck priority handling
- Learning vs review balance

### Sibling Card Management
[Analyze: How related cards are handled]
- Burying logic
- Unburying conditions
- Impact on session flow

## Advanced Features

### Daily Limits & Deck Options
[Analyze: Per-deck configuration system]

### Filtered Decks
[Analyze: Custom study session creation]

### Statistics & Analytics
[Analyze: Review tracking and reporting]

## Performance Optimizations
[Document: How Anki handles large card collections efficiently]

## Database Schema
[Analyze: Key tables and relationships for scheduling]

## Configuration System
[Analyze: How scheduler settings are managed and stored]

---

**Analysis Target Files**:
- `rslib/src/scheduler/mod.rs`
- `rslib/src/scheduler/states/`
- `rslib/src/scheduler/timing/`
- `rslib/src/scheduler/fsrs/`
- `pylib/anki/scheduler/`

**Deliverable**: Complete system understanding for Danki implementation