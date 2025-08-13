# Anki Scheduler System Analysis

**Status**: 📋 Template - To be completed by specialized analysis agent  
**Target**: https://github.com/ankitects/anki  
**Focus**: Complete scheduler system documentation

---

## Overview
[To be filled: High-level architecture overview of Anki's scheduling system]

## Core Components

### Scheduler Architecture
[Analyze: rslib/src/scheduler/ structure and main components]

### Card State Management  
[Analyze: How Anki manages card states (new, learning, review, suspended)]

### Algorithm Implementations
[Analyze: Both SM-2+ and FSRS implementations]

## Key Algorithms

### SM-2+ Enhanced
[Document: Anki's improvements over basic SM-2]
- Ease factor adjustments
- Learning step sequences
- Graduation logic
- Lapse handling

### FSRS (Free Spaced Repetition Scheduler)
[Document: Modern algorithm implementation]
- Memory stability calculations
- Difficulty assessments  
- Retention prediction
- Parameter optimization

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