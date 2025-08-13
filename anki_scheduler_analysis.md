# Anki Scheduler Analysis: Complete System Architecture

## Overview

This document provides a comprehensive analysis of Anki's spaced repetition scheduler system based on deep investigation of the ankitects/anki repository (2024). The analysis covers both the legacy SM-2 implementation and the modern FSRS (Free Spaced Repetition Scheduler) system.

## Repository Structure

### Core Scheduler Location
- **Primary Directory**: `rslib/src/scheduler/` (Rust implementation)
- **Python Interface**: `pylib/` (Python bindings to Rust core)
- **Protocol Buffers**: `proto/anki/scheduler.proto` (API definitions)

### Key Modules

#### Scheduler Core (`rslib/src/scheduler/`)
```
scheduler/
├── mod.rs              # Main scheduler module and interfaces
├── answering/          # Card answer processing logic
├── fsrs/               # FSRS algorithm implementation
├── queue/              # Review session queue management
├── states/             # Card state management system
├── new.rs              # New card scheduling
├── reviews.rs          # Review card interval calculations
├── timing.rs           # Daily scheduling and timezone handling
├── bury_and_suspend.rs # Card suspension/burying logic
├── congrats.rs         # Session completion handling
├── filtered/           # Filtered deck operations
├── service/            # Scheduling service layer
└── upgrade.rs          # Scheduler version migrations
```

## Core Architecture Components

### 1. Scheduler Information System

```rust
pub struct SchedulerInfo {
    pub version: SchedulerVersion,  // V1, V2, or V3 (FSRS)
    pub timing: SchedTimingToday,   // Current day timing information
}
```

**Key Methods:**
- `scheduler_info()`: Retrieves/generates current scheduler state
- `timing_today()`: Returns current scheduling timing
- `timing_for_timestamp()`: Calculates timing for specific timestamps

### 2. Card State Management

#### State Hierarchy
```rust
pub enum CardState {
    Normal(NormalState),
    Filtered(FilteredState),
}

pub enum NormalState {
    New(NewState),
    Learning(LearnState),
    Review(ReviewState),
    Relearning(RelearnState),
}
```

#### State Transitions
- **New → Learning**: First review with answer ratings
- **Learning → Review**: Graduation after completing all learning steps
- **Review → Relearning**: Failed review (Again answer)
- **Learning/Relearning → Review**: Successful completion of steps

### 3. Queue Management System

```rust
pub struct CardQueues {
    main: VecDeque<QueueEntry>,
    intraday_learning: VecDeque<QueueEntry>,
    current_day: u32,
    current_learning_cutoff: TimestampSecs,
}
```

**Queue Ordering Priority:**
1. Intraday learning cards (immediate)
2. Main queue cards (new/review)
3. Future intraday learning cards

### 4. Answer Rating System

```rust
pub enum Rating {
    Again = 1,  // Complete failure - card resets
    Hard = 2,   // Difficult recall - reduced interval
    Good = 3,   // Successful recall - normal interval
    Easy = 4,   // Effortless recall - bonus interval
}
```

## SM-2 Algorithm Implementation

### Core Parameters

#### Ease Factor Management
- **Initial Ease**: 2.5 (250%)
- **Minimum Ease**: 1.3 (130%)
- **Ease Adjustments**:
  - Again: -0.2 (-20 percentage points)
  - Hard: -0.15 (-15 percentage points)
  - Good: No change
  - Easy: +0.15 (+15 percentage points)

#### Learning Steps
- **Default Steps**: [1 minute, 10 minutes] (configurable)
- **Graduating Interval**: 1 day (when leaving learning)
- **Easy Interval**: 4 days (when pressing Easy from learning)

#### Review Intervals

**Basic Interval Calculation:**
```rust
// Good answer
new_interval = (current_interval + days_late/2) * ease_factor

// Hard answer
new_interval = current_interval * hard_multiplier  // typically 1.2

// Easy answer  
new_interval = (current_interval + days_late) * ease_factor * easy_multiplier  // typically 1.3
```

### Learning State Progression

#### New Cards
1. **Positioning**: Cards assigned position numbers for ordering
2. **Initial State**: CardType::New, CardQueue::New
3. **First Answer**: Transitions to Learning state with first step

#### Learning Steps
```rust
pub struct LearnState {
    remaining_steps: Vec<u32>,    // Steps in minutes
    scheduled_secs: u32,          // Time until next review
    elapsed_secs: u32,            // Time spent learning
    memory_state: Option<MemoryState>,  // FSRS integration
}
```

**Progression Rules:**
- **Again**: Reset to first step
- **Hard**: Repeat current step (min 10 minutes)
- **Good**: Advance to next step
- **Easy**: Graduate immediately (if allowed)

#### Graduation Logic
Cards graduate to Review state when:
1. Successfully complete all learning steps with Good/Easy
2. Next interval would exceed learning threshold
3. Using Easy button from final learning step

### Review State Management

#### Interval Fuzzing
```rust
// Add randomness to prevent card clustering
fuzzed_interval = base_interval * (0.95 + 0.1 * random())
```

#### Lapse Handling
When Review cards are answered "Again":
1. **State Change**: Review → Relearning
2. **Ease Penalty**: -20 percentage points
3. **Interval Reset**: Based on lapse multiplier (default 0.5)
4. **Step Assignment**: Enter relearning steps

## FSRS Algorithm Implementation

### Core Concepts

#### DSR Model Components
```rust
pub struct MemoryState {
    stability: f32,      // Days for recall to drop from 100% to 90%
    difficulty: f32,     // Inherent complexity (1.0 - 10.0)
}
```

#### Retrievability Calculation
```rust
// R(t,S) = (1 + DECAY * t / S)^(-1/DECAY)
// Where DECAY ensures R(S,S) = 0.9
fn retrievability(elapsed_days: f32, stability: f32) -> f32 {
    let factor = (DECAY * elapsed_days / stability);
    (1.0 + factor).powf(-1.0 / DECAY)
}
```

### FSRS Parameters

#### Parameter Structure
- **Total Parameters**: 19 floating-point values
- **Default Source**: Trained on 20,000+ users, 700M+ reviews
- **Optimization**: Machine learning on individual review history

#### Key Formulas (FSRS v6)

**Stability After Review:**
```rust
S' = S * e^(w[17] * (G - 3 + w[18])) * S^(-w[19])
```

**Difficulty Evolution:**
```rust
// Mean reversion to prevent "difficulty hell"
D' = D + w[6] * (Grade - 3)
D' = constrain(D', 1.0, 10.0)
```

**Interval Calculation:**
```rust
// Target retrievability = 0.9 (90% retention)
interval = S * ln(target_retention / 0.9) / ln(0.9)
```

### FSRS Integration Points

#### Memory State Tracking
```rust
pub struct FsrsItemForMemoryState {
    card: Card,
    starting_state: Option<MemoryState>,
    filtered_revlogs: Vec<ReviewLog>,
}
```

#### Optimization Process
1. **Data Collection**: Analyze user's complete review history
2. **Parameter Fitting**: Minimize prediction loss using ML
3. **Validation**: Cross-validation on held-out data
4. **Application**: Use optimized parameters for scheduling

## Daily Scheduling System

### Timing Management

#### Day Calculation
```rust
pub struct SchedTimingToday {
    pub days_elapsed: u32,        // Days since collection creation
    pub next_day_at: TimestampSecs, // When next day begins
}
```

#### Rollover Logic
- **Default Rollover**: 4:00 AM local time
- **Configurable**: Per-collection rollover hour setting
- **Timezone Handling**: Accounts for UTC offsets and DST

### Queue Building Process

#### Daily Limits
- **New Cards**: Configurable per deck (default 20)
- **Review Cards**: Configurable per deck (default 200)
- **Learning Cards**: No daily limit (processed as due)

#### Card Selection Algorithm
1. **Learning Cards**: All due learning cards (priority)
2. **New Cards**: Up to daily limit, by position/random order
3. **Review Cards**: All due reviews, sorted by due date
4. **Interleaving**: Mix new/review based on preferences

## Database Schema Integration

### Key Tables

#### Cards Table
```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY,
    nid INTEGER NOT NULL,     -- Note ID
    did INTEGER NOT NULL,     -- Deck ID
    ord INTEGER NOT NULL,     -- Card template ordinal
    mod INTEGER NOT NULL,     -- Last modified timestamp
    usn INTEGER NOT NULL,     -- Update sequence number
    type INTEGER NOT NULL,    -- Card type (0=new, 1=learning, 2=review, 3=relearning)
    queue INTEGER NOT NULL,   -- Current queue (-3=user buried, -2=sched buried, -1=suspended, 0=new, 1=learning, 2=review, 3=in learning)
    due INTEGER NOT NULL,     -- Due date/position
    ivl INTEGER NOT NULL,     -- Current interval in days
    factor INTEGER NOT NULL,  -- Ease factor * 1000
    reps INTEGER NOT NULL,    -- Number of reviews
    lapses INTEGER NOT NULL,  -- Number of times card went from review to relearning
    left INTEGER NOT NULL,    -- Learning: steps left | Review: unused
    odue INTEGER NOT NULL,    -- Original due date (for filtered decks)
    odid INTEGER NOT NULL,    -- Original deck ID (for filtered decks)
    flags INTEGER NOT NULL,   -- Unused
    data TEXT NOT NULL        -- Extra data (JSON)
);
```

#### Review Log Table
```sql
CREATE TABLE revlog (
    id INTEGER PRIMARY KEY,
    cid INTEGER NOT NULL,     -- Card ID
    usn INTEGER NOT NULL,     -- Update sequence number
    ease INTEGER NOT NULL,    -- Answer button pressed (1-4)
    ivl INTEGER NOT NULL,     -- Interval after review
    lastIvl INTEGER NOT NULL, -- Interval before review
    factor INTEGER NOT NULL,  -- Ease factor after review
    time INTEGER NOT NULL,    -- Time taken to answer (milliseconds)
    type INTEGER NOT NULL     -- Review type (0=learn, 1=review, 2=relearn, 3=early review)
);
```

## Performance Optimizations

### Indexing Strategy
- **Primary Indexes**: Card due dates, deck IDs, card types
- **Queue Optimization**: Separate indexes for different queue states
- **Review Log**: Indexes on card ID and timestamp for analytics

### Memory Management
- **Queue Caching**: In-memory queue for active session
- **Lazy Loading**: Cards loaded on-demand during review
- **Batch Operations**: Bulk updates for state changes

## Advanced Features

### Filtered Decks
- **Custom Study**: Temporary decks with modified scheduling
- **Preview Mode**: Review without affecting normal scheduling
- **Cramming**: Short-term intensive review sessions

### Sibling Management
- **Card Burial**: Hide related cards until next day
- **Automatic Burial**: Based on note relationships
- **Manual Control**: User-controlled burial options

### Statistics Integration
- **Performance Tracking**: Retention rates, review time
- **Forecast Calculations**: Predicted review load
- **Historical Analysis**: Long-term learning trends

## Migration and Compatibility

### Scheduler Upgrades
- **V1 → V2**: Legacy compatibility mode
- **V2 → FSRS**: Optional migration with history preservation
- **Data Preservation**: All review history maintained

### Backward Compatibility
- **Algorithm Selection**: Per-deck scheduler choice
- **Parameter Migration**: Automatic conversion of intervals/ease
- **Rollback Support**: Ability to revert scheduler changes

## Key Implementation Insights

### Design Principles
1. **Modularity**: Clear separation between algorithms and infrastructure
2. **Configurability**: Extensive per-deck and per-collection options
3. **Performance**: Optimized for large collections (100k+ cards)
4. **Reliability**: Robust error handling and data consistency

### Algorithm Trade-offs
- **SM-2**: Simple, predictable, widely understood
- **FSRS**: More accurate, personalized, but complex
- **Hybrid Approach**: Users can choose per-deck

### Extensibility Points
- **Custom Schedulers**: Plugin architecture for new algorithms
- **Parameter Tuning**: Machine learning optimization
- **Research Integration**: Easy algorithm comparison and validation

This analysis provides the foundation for implementing a compatible scheduler system in Danki, with the flexibility to support both traditional SM-2 and modern FSRS approaches based on user preferences and requirements.